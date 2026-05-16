import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models import Job
from app.schemas import JobCreate, JobUpdate, JobResponse
from app.session import get_or_create_session_id
from app.analyzer import extract_text_from_pdf, analyze_resume_against_jd

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_STATUSES = [
    "interested", "researched", "assessed", "preparing",
    "ready", "applied", "interview", "offer",
    "rejected", "ghosted", "withdrawn"
]

UPLOAD_DIR = "/tmp/uploads" if os.getenv("RENDER") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=JobResponse)
async def create_job(
    request: Request,
    response: Response,
    company:  str           = Form(...),
    role:     str           = Form(...),
    job_url:  Optional[str] = Form(None),
    notes:    Optional[str] = Form(None),
    jd_text:  Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)

    new_job = Job(
        session_id=session_id,   # ← attach session to every job
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


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    return db.query(Job).filter(
        Job.session_id == session_id   # ← only this session's jobs
    ).order_by(Job.applied_at.desc()).all()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.session_id == session_id   # ← must belong to this session
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id:  int,
    request: Request,
    response: Response,
    status:  Optional[str] = Form(None),
    notes:   Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.session_id == session_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {VALID_STATUSES}"
        )

    if status  is not None: job.status  = status
    if notes   is not None: job.notes   = notes
    if jd_text is not None: job.jd_text = jd_text

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.session_id == session_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.resume_path and os.path.exists(job.resume_path):
        other_jobs = db.query(Job).filter(
            Job.resume_path == job.resume_path,
            Job.id != job_id
        ).count()
        if other_jobs == 0:
            os.remove(job.resume_path)

    db.delete(job)
    db.commit()
    return {"message": f"Job #{job_id} deleted successfully"}


@router.post("/{job_id}/upload-resume", response_model=JobResponse)
async def upload_resume(
    job_id: int,
    request: Request,
    response: Response,
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.session_id == session_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    file_path = f"{UPLOAD_DIR}/job_{job_id}_resume.pdf"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    job.resume_path = file_path
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/analyze")
def analyze_job(
    job_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    session_id = get_or_create_session_id(request, response)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.session_id == session_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.jd_text:
        raise HTTPException(status_code=400, detail="No job description found.")
    if not job.resume_path or not os.path.exists(job.resume_path):
        raise HTTPException(status_code=400, detail="No resume found.")

    resume_text = extract_text_from_pdf(job.resume_path)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        analysis_result = analyze_resume_against_jd(resume_text, job.jd_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    job.analysis = json.dumps(analysis_result)
    db.commit()
    db.refresh(job)

    return {
        "job_id":   job_id,
        "company":  job.company,
        "role":     job.role,
        "analysis": analysis_result
    }