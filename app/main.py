from fastapi import FastAPI, Request, Response, Depends
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.database import engine, Base, SessionLocal, run_migrations, get_db
from app.models import Job
from app.routers import jobs, intelligence
from app.session import get_or_create_session_id
from dotenv import load_dotenv
import json
import os

load_dotenv()

Base.metadata.create_all(bind=engine)
run_migrations()

UPLOAD_DIR = "/tmp/uploads" if os.getenv("RENDER") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(
    title="JobScribe",
    description="Track job applications with AI-powered resume analysis",
    version="2.0.0"
)
GA_TRACKING_ID = os.getenv("GA_TRACKING_ID", "")

templates = Jinja2Templates(directory="templates")
templates.env.globals["GA_TRACKING_ID"] = os.getenv("GA_TRACKING_ID", "")
templates.env.filters["fromjson"] = json.loads
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(jobs.router)
app.include_router(intelligence.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, response: Response):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        all_jobs = db.query(Job).filter(
            Job.session_id == session_id
        ).order_by(Job.applied_at.desc()).all()
    finally:
        db.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"jobs": all_jobs}
    )


@app.get("/jobs/{job_id}/detail", response_class=HTMLResponse)
def job_detail(request: Request, response: Response, job_id: int):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.session_id == session_id
        ).first()
    finally:
        db.close()

    if not job:
        return HTMLResponse("<h2>Job not found</h2>", status_code=404)

    analysis = None
    if job.analysis:
        analysis = json.loads(job.analysis)

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={"job": job, "analysis": analysis}
    )


@app.get("/add-job", response_class=HTMLResponse)
def add_job_page(request: Request, response: Response):
    get_or_create_session_id(request, response)
    return templates.TemplateResponse(
        request=request,
        name="add_job.html",
        context={}
    )


@app.get("/jobs/{job_id}/research-result", response_class=HTMLResponse)
def research_result(request: Request, response: Response, job_id: int):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.session_id == session_id
        ).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import CompanyResearch
        research = db.query(CompanyResearch).filter(
            CompanyResearch.company_name == job.company
        ).first()
    finally:
        db.close()

    if not research:
        return HTMLResponse("<h2>No research found.</h2>")

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
def assessment_result(request: Request, response: Response, job_id: int):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.session_id == session_id
        ).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import ReadinessAssessment
        assessment = db.query(ReadinessAssessment).filter(
            ReadinessAssessment.job_id == job_id
        ).order_by(ReadinessAssessment.assessed_at.desc()).first()
    finally:
        db.close()

    if not assessment:
        return HTMLResponse("<h2>No assessment found.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="assessment.html",
        context={
            "job": job,
            "assessment": json.loads(assessment.full_assessment)
        }
    )


@app.get("/jobs/{job_id}/roadmap-result", response_class=HTMLResponse)
def roadmap_result(request: Request, response: Response, job_id: int):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.session_id == session_id
        ).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import PrepRoadmap
        roadmap = db.query(PrepRoadmap).filter(
            PrepRoadmap.job_id == job_id
        ).first()
    finally:
        db.close()

    if not roadmap:
        return HTMLResponse("<h2>No roadmap found.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="roadmap.html",
        context={
            "job": job,
            "roadmap": json.loads(roadmap.roadmap_json)
        }
    )


@app.get("/jobs/{job_id}/simulator", response_class=HTMLResponse)
def simulator_page(request: Request, response: Response, job_id: int):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.session_id == session_id
        ).first()
        if not job:
            return HTMLResponse("<h2>Job not found</h2>", status_code=404)
        from app.models import InterviewQuestion
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.job_id == job_id
        ).all()
    finally:
        db.close()

    if not questions:
        return HTMLResponse("<h2>No questions found.</h2>")

    return templates.TemplateResponse(
        request=request,
        name="simulator.html",
        context={"job": job, "questions": questions}
    )


@app.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, response: Response):
    session_id = get_or_create_session_id(request, response)
    db = SessionLocal()
    try:
        all_jobs = db.query(Job).filter(
            Job.session_id == session_id
        ).all()
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

@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    """
    Quick stats endpoint — visit this URL to see
    what's happening on your platform right now.
    Bookmark it after your LinkedIn post goes live.
    """
    from app.models import UsageLog
    from sqlalchemy import func

    total_jobs     = db.query(Job).count()
    total_sessions = db.query(Job.session_id).distinct().count()

    # Events in last 24 hours
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(hours=24)

    recent_events = db.query(
        UsageLog.event,
        func.count(UsageLog.id).label("count")
    ).filter(
        UsageLog.created_at >= since
    ).group_by(UsageLog.event).all()

    # Most researched companies
    top_companies = db.query(
        UsageLog.company,
        func.count(UsageLog.id).label("count")
    ).filter(
        UsageLog.event == "research_run",
        UsageLog.company != None
    ).group_by(
        UsageLog.company
    ).order_by(
        func.count(UsageLog.id).desc()
    ).limit(5).all()

    # Unique sessions today
    today = datetime.utcnow().replace(hour=0, minute=0,
                                      second=0, microsecond=0)
    sessions_today = db.query(
        UsageLog.session_id
    ).filter(
        UsageLog.created_at >= today,
        UsageLog.session_id != None
    ).distinct().count()

    return {
        "total_jobs_in_db":     total_jobs,
        "total_unique_users":   total_sessions,
        "unique_users_today":   sessions_today,
        "last_24h": {
            event: count
            for event, count in recent_events
        },
        "top_companies_researched": [
            {"company": c, "count": n}
            for c, n in top_companies
        ]
    }