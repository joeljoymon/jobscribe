import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Job
from app.schemas import JobCreate, JobUpdate, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_STATUSES = ["applied", "interview", "offer", "rejected", "ghosted"]
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── ADD A JOB ────────────────────────────────────────────────
@router.post("/", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """
    User adds a new job application.
    Status is automatically set to 'applied'.
    JD text can be added now or updated later.
    """
    new_job = Job(**job.model_dump())
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
def update_job(job_id: int, updates: JobUpdate, db: Session = Depends(get_db)):
    """
    User manually updates status, notes, or JD text.
    Status must be one of the valid values.
    Only fields that are sent get updated — the rest stay unchanged.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if updates.status and updates.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {VALID_STATUSES}"
        )

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

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