from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal
from app.routers import jobs
from app.models import Job
from dotenv import load_dotenv
import json
import os

load_dotenv()

Base.metadata.create_all(bind=engine)
UPLOAD_DIR = "/tmp/uploads" if os.getenv("RENDER") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(
    title="JobScribe",
    description="Track job applications with AI-powered resume analysis",
    version="0.1.0"
)

templates = Jinja2Templates(directory="templates")
# Custom filter — converts JSON string to dict inside templates
templates.env.filters["fromjson"] = json.loads
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(jobs.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Main dashboard page.
    Fetches all jobs from the database and renders them
    as an HTML table with status badges.
    """
    db = SessionLocal()
    try:
        all_jobs = db.query(Job).order_by(Job.applied_at.desc()).all()
    finally:
        db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"jobs": all_jobs}
    )


@app.get("/jobs/{job_id}/detail", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int):
    """
    Detail page for one job.
    Shows full information + parsed analysis report if available.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
    finally:
        db.close()

    if not job:
        return HTMLResponse("<h2>Job not found</h2>", status_code=404)

    # Parse the analysis JSON string back into a dict for the template
    analysis = None
    if job.analysis:
        analysis = json.loads(job.analysis)

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={"job": job, "analysis": analysis}
    )


@app.get("/add-job", response_class=HTMLResponse)
def add_job_page(request: Request):
    """
    Page with a form to add a new job application.
    On submit it calls POST /jobs/ API endpoint.
    """
    return templates.TemplateResponse( 
        request=request,
        name="add_job.html",
        context={}
    )