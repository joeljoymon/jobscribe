from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal
from app.routers import jobs, intelligence   
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
app.include_router(intelligence.router) 


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

@app.get("/jobs/{job_id}/research-result", response_class=HTMLResponse)
def research_result(request: Request, job_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import CompanyResearch
        research = db.query(CompanyResearch).filter(
            CompanyResearch.company_name == job.company
        ).first()
    finally:
        db.close()

    if not research:
        return HTMLResponse("<h2>No research found. Run research first.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="research.html",
        context={
            "job": job,
            "research": json.loads(research.raw_research),
            "cached": False
        }
    )


@app.get("/jobs/{job_id}/assessment-result", response_class=HTMLResponse)
def assessment_result(request: Request, job_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import ReadinessAssessment
        assessment = db.query(ReadinessAssessment).filter(
            ReadinessAssessment.job_id == job_id
        ).order_by(ReadinessAssessment.assessed_at.desc()).first()
    finally:
        db.close()

    if not assessment:
        return HTMLResponse("<h2>No assessment found. Run assess first.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="assessment.html",
        context={
            "job": job,
            "assessment": json.loads(assessment.full_assessment)
        }
    )


@app.get("/jobs/{job_id}/roadmap-result", response_class=HTMLResponse)
def roadmap_result(request: Request, job_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import PrepRoadmap
        roadmap = db.query(PrepRoadmap).filter(
            PrepRoadmap.job_id == job_id
        ).first()
    finally:
        db.close()

    if not roadmap:
        return HTMLResponse("<h2>No roadmap found. Generate roadmap first.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="roadmap.html",
        context={
            "job": job,
            "roadmap": json.loads(roadmap.roadmap_json)
        }
    )


@app.get("/jobs/{job_id}/simulator", response_class=HTMLResponse)
def simulator_page(request: Request, job_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import InterviewQuestion
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.job_id == job_id
        ).all()
    finally:
        db.close()

    if not questions:
        return HTMLResponse("<h2>No questions found. Run simulator first.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="simulator.html",
        context={
            "job": job,
            "questions": questions
        }
    )


@app.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request):
    db = SessionLocal()
    try:
        all_jobs = db.query(Job).all()
    finally:
        db.close()

    if len(all_jobs) < 3:
        analytics = {
            "message": "Add at least 3 job applications to see patterns.",
            "total_jobs": len(all_jobs)
        }
    else:
        from app.models import ReadinessAssessment
        from app.analyzer import analyze_outcomes
        jobs_summary = []
        db2 = SessionLocal()
        try:
            for job in all_jobs:
                latest = db2.query(ReadinessAssessment).filter(
                    ReadinessAssessment.job_id == job.id
                ).order_by(ReadinessAssessment.assessed_at.desc()).first()
                jobs_summary.append({
                    "company":         job.company,
                    "role":            job.role,
                    "status":          job.status,
                    "readiness_score": job.readiness_score,
                    "match_score":     json.loads(job.analysis).get("match_score")
                                       if job.analysis else None,
                })
        finally:
            db2.close()
        analytics = {"analytics": analyze_outcomes(jobs_summary)}

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={"analytics": analytics}
    )