import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Job
from app.schemas import JobCreate, JobUpdate, JobResponse
from app.analyzer import extract_text_from_pdf, analyze_resume_against_jd


router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_STATUSES = ["applied", "interview", "offer", "rejected", "ghosted"]
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── ADD A JOB ────────────────────────────────────────────────
@router.post("/", response_model=JobResponse)
async def create_job(
    company:  str              = Form(...),
    role:     str              = Form(...),
    job_url:  Optional[str]    = Form(None),
    notes:    Optional[str]    = Form(None),
    jd_text:  Optional[str]    = Form(None),
    db: Session = Depends(get_db)
):
    """
    Accepts form data instead of JSON.
    This means the JD text can be pasted freely
    without worrying about JSON escaping.
    """
    new_job = Job(
        company=company,
        role=role,
        job_url=job_url,
        notes=notes,
        jd_text=jd_text
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


# ── LIST ALL JOBS ────────────────────────────────────────────
@router.get("/", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """
    Returns every job application in the database.
    The dashboard calls this to show the full list.
    """
    return db.query(Job).order_by(Job.applied_at.desc()).all()


# ── GET ONE JOB ──────────────────────────────────────────────
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Returns a single job with full details including
    the Gemini analysis if it has been run.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── UPDATE A JOB ─────────────────────────────────────────────
@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id:  int,
    company:  str              = Form(...),
    role:     str              = Form(...),
    status:  Optional[str] = Form(None),
    notes:   Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    User manually updates status, notes, or JD text.
    Status must be one of the valid values.
    Only fields that are sent get updated — the rest stay unchanged.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {VALID_STATUSES}"
        )

    if company  is not None: job.company  = company
    if role     is not None: job.role = role
    if status   is not None: job.status   = status
    if notes    is not None: job.notes    = notes
    if jd_text  is not None: job.jd_text  = jd_text


    db.commit()
    db.refresh(job)
    return job


# ── DELETE A JOB ─────────────────────────────────────────────
@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):

    # Guard 1 — does the job exist?
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    # Guard 2 — safe to delete file?
    if job.resume_path and os.path.exists(job.resume_path):
        other_jobs = db.query(Job).filter(
            Job.resume_path == job.resume_path,
            Job.id != job_id
        ).count()
        if other_jobs == 0:
            os.remove(job.resume_path)

    # Main logic — only reaches here if all guards passed
    db.delete(job)
    db.commit()
    return {"message": f"Job #{job_id} deleted successfully"}


# ── UPLOAD RESUME ────────────────────────────────────────────
@router.post("/{job_id}/upload-resume", response_model=JobResponse)
async def upload_resume(
    job_id: int,
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    User uploads their resume PDF for a specific job.
    The file is saved to the uploads/ folder.
    The path is saved in the database against this job.
    Gemini analysis is NOT triggered here — that's a separate step.
    This separation means the user can upload once and
    analyze against multiple jobs without re-uploading.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_path = f"{UPLOAD_DIR}/job_{job_id}_resume.pdf"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    job.resume_path = file_path
    db.commit()
    db.refresh(job)
    return job

# ── ANALYZE RESUME AGAINST JD ────────────────────────────────
@router.post("/{job_id}/analyze")
def analyze_job(job_id: int, db: Session = Depends(get_db)):
    """
    The core feature of JobScribe.

    This endpoint:
    1. Finds the job in the database
    2. Checks resume and JD both exist
    3. Extracts text from the PDF resume
    4. Sends both texts to Gemini
    5. Saves the analysis result back to the job
    6. Returns the structured gap report

    User must have:
    - Added jd_text when creating the job (or updated it later)
    - Uploaded their resume PDF via /upload-resume
    Only then can they run analysis.
    """

    # Guard 1 — job must exist
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard 2 — JD text must exist
    if not job.jd_text:
        raise HTTPException(
            status_code=400,
            detail="No job description found. Update this job with jd_text first."
        )

    # Guard 3 — resume must be uploaded
    if not job.resume_path:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Upload your resume first via /upload-resume."
        )

    # Guard 4 — resume file must exist on disk
    if not os.path.exists(job.resume_path):
        raise HTTPException(
            status_code=400,
            detail="Resume file missing from server. Please upload again."
        )

    # Extract text from PDF
    resume_text = extract_text_from_pdf(job.resume_path)

    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF. Make sure it is not a scanned image."
        )

    # Send to Gemini and get analysis
    try:
        analysis_result = analyze_resume_against_jd(resume_text, job.jd_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini analysis failed: {str(e)}"
        )

    # Save the analysis back to the job as a JSON string
    job.analysis = json.dumps(analysis_result)
    db.commit()
    db.refresh(job)

    # Return the structured analysis directly
    return {
        "job_id":   job_id,
        "company":  job.company,
        "role":     job.role,
        "analysis": analysis_result
    }