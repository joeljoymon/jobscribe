from fastapi import APIRouter, Depends, HTTPException,  Request, Response
from app.session import get_or_create_session_id
from app.analyzer import (
    extract_text_from_pdf,
    research_company,
    assess_readiness,
    generate_roadmap,
    generate_interview_questions,
    analyze_outcomes 
)
import os
import json
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, CompanyResearch, ReadinessAssessment, PrepRoadmap, InterviewQuestion
from datetime import datetime, timedelta
last_calls = {}

def check_rate_limit(session_id: str):
    """
    Prevents one user from rapidly firing multiple AI calls.
    10 second cooldown between any two AI requests per session.
    """
    now = datetime.utcnow()
    last = last_calls.get(session_id)
    if last and (now - last) < timedelta(seconds=10):
        raise HTTPException(
            status_code=429,
            detail="Please wait a few seconds before running another analysis."
        )
    last_calls[session_id] = now
router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── COMPANY RESEARCH ─────────────────────────────────────────
@router.post("/jobs/{job_id}/research")
def research_job_company(job_id: int,request: Request,
    response: Response, db: Session = Depends(get_db)):
    """
    Researches the company and role for a specific job.

    First checks if this company has been researched before.
    If yes — returns cached result instantly without calling AI.
    If no  — calls Groq AI, saves result, returns it.

    Also updates job status to 'researched'.
    """
    session_id = get_or_create_session_id(request, response)

    # Guard 1 — job must exist
    job = db.query(Job).filter(Job.id == job_id, Job.session_id == session_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard 2 — company name must exist
    if not job.company:
        raise HTTPException(status_code=400, detail="Job has no company name")
    check_rate_limit(session_id)
    # Step 1 — check cache first
    cached = db.query(CompanyResearch).filter(
        CompanyResearch.company_name == job.company
    ).first()

    if cached:
        # Update job status and return cached result
        job.status = "researched"
        db.commit()
        return {
            "job_id":   job_id,
            "company":  job.company,
            "role":     job.role,
            "cached":   True,
            "research": json.loads(cached.raw_research)
        }

    # Step 2 — not cached, call AI
    research_result = research_company(job.company, job.role)

    # Step 3 — save to database
    new_research = CompanyResearch(
        company_name    = job.company,
        company_type    = research_result.get("company_type"),
        what_they_do    = research_result.get("what_they_do"),
        role_summary    = research_result.get("role_summary"),
        interview_style = research_result.get("interview_style"),
        cs_topics_json  = json.dumps(research_result.get("cs_topics", {})),
        raw_research    = json.dumps(research_result)
    )
    db.add(new_research)

    # Step 4 — update job status
    job.status = "researched"
    db.commit()

    return {
        "job_id":   job_id,
        "company":  job.company,
        "role":     job.role,
        "cached":   False,
        "research": research_result
    }


# ── READINESS ASSESSMENT ─────────────────────────────────────
@router.post("/jobs/{job_id}/assess")
def assess_job_readiness(job_id: int, request: Request,
    response: Response,db: Session = Depends(get_db)):
    """
    Assesses how ready the user is for this specific role.

    Requires:
    - Resume uploaded (resume_path exists)
    - JD text saved on the job

    Creates a new ReadinessAssessment row every time it runs.
    This builds a history of scores so user can track improvement.
    Also updates job.readiness_score with the latest score.
    """
    session_id = get_or_create_session_id(request, response)

    # Guard 1 — job must exist
    job = db.query(Job).filter(Job.id == job_id, Job.session_id == session_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard 2 — JD must exist
    if not job.jd_text:
        raise HTTPException(
            status_code=400,
            detail="No job description found. Update this job with jd_text first."
        )

    # Guard 3 — resume must be uploaded
    if not job.resume_path or not os.path.exists(job.resume_path):
        raise HTTPException(
            status_code=400,
            detail="No resume found. Upload your resume first."
        )
    check_rate_limit(session_id)

    # Get company research if available (improves assessment quality)
    company_context = None
    cached_research = db.query(CompanyResearch).filter(
        CompanyResearch.company_name == job.company
    ).first()
    if cached_research:
        company_context = cached_research.raw_research

    # Extract resume text
    resume_text = extract_text_from_pdf(job.resume_path)
    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF."
        )

    # Call AI for assessment
    assessment_result = assess_readiness(
        resume_text=resume_text,
        jd_text=job.jd_text,
        company_context=company_context
    )

    # Save assessment as new row (preserves history)
    new_assessment = ReadinessAssessment(
        job_id             = job_id,
        overall_score      = assessment_result.get("overall_readiness_score", 0),
        technical_score    = assessment_result.get("technical_skills_score"),
        fundamentals_score = assessment_result.get("cs_fundamentals_score"),
        projects_score     = assessment_result.get("projects_relevance_score"),
        confidence_level   = assessment_result.get("confidence_level"),
        gaps_json          = json.dumps(assessment_result.get("gaps", [])),
        cs_gaps_json       = json.dumps(assessment_result.get("cs_gaps", [])),
        verdict            = assessment_result.get("verdict"),
        estimated_days     = assessment_result.get("estimated_days_to_ready"),
        full_assessment    = json.dumps(assessment_result)
    )
    db.add(new_assessment)

    # Update job with latest score and status
    job.readiness_score = assessment_result.get("overall_readiness_score", 0)
    job.status = "assessed"
    db.commit()

    return {
        "job_id":     job_id,
        "company":    job.company,
        "role":       job.role,
        "assessment": assessment_result
    }


# ── PREPARATION ROADMAP ──────────────────────────────────────
@router.post("/jobs/{job_id}/roadmap")
def generate_job_roadmap(job_id: int, request: Request,
    response: Response, db: Session = Depends(get_db)):
    """
    Generates a day by day preparation plan based on
    the latest readiness assessment gaps.

    Requires a readiness assessment to exist first.
    If a roadmap already exists for this job, replaces it.
    Updates job status to 'preparing'.
    """
    session_id = get_or_create_session_id(request, response)

    # Guard 1 — job must exist
    job = db.query(Job).filter(Job.id == job_id, Job.session_id == session_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard 2 — assessment must exist
    latest_assessment = db.query(ReadinessAssessment).filter(
        ReadinessAssessment.job_id == job_id
    ).order_by(ReadinessAssessment.assessed_at.desc()).first()

    check_rate_limit(session_id)

    if not latest_assessment:
        raise HTTPException(
            status_code=400,
            detail="No readiness assessment found. Run /assess first."
        )

    # Generate roadmap from gaps
    gaps = json.loads(latest_assessment.gaps_json or "[]")
    cs_gaps = json.loads(latest_assessment.cs_gaps_json or "[]")
    estimated_days = latest_assessment.estimated_days or 7

    roadmap_result = generate_roadmap(
        gaps=gaps,
        cs_gaps=cs_gaps,
        estimated_days=estimated_days,
        company=job.company,
        role=job.role
    )

    # Delete existing roadmap if present, create new one
    existing = db.query(PrepRoadmap).filter(
        PrepRoadmap.job_id == job_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_roadmap = PrepRoadmap(
        job_id       = job_id,
        total_days   = roadmap_result.get("total_days", estimated_days),
        roadmap_json = json.dumps(roadmap_result)
    )
    db.add(new_roadmap)

    # Update job status
    job.status = "preparing"
    db.commit()

    return {
        "job_id":  job_id,
        "company": job.company,
        "role":    job.role,
        "roadmap": roadmap_result
    }


# ── INTERVIEW SIMULATOR ──────────────────────────────────────
@router.post("/jobs/{job_id}/simulate")
def simulate_interview(job_id: int, request: Request,
    response: Response, db: Session = Depends(get_db)):
    """
    Generates 10 personalized interview questions.

    Questions are tailored to:
    - The specific JD and company
    - The user's resume and projects
    - Their readiness level (not too hard, not too easy)

    Each question is saved as its own row so user
    can mark individual questions as practiced.
    """
    session_id = get_or_create_session_id(request, response)

    # Guard 1 — job must exist
    job = db.query(Job).filter(Job.id == job_id, Job.session_id == session_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard 2 — resume and JD must exist
    if not job.jd_text:
        raise HTTPException(status_code=400, detail="No JD found.")
    if not job.resume_path or not os.path.exists(job.resume_path):
        raise HTTPException(status_code=400, detail="No resume found.")

    check_rate_limit(session_id)

    # Get latest assessment for readiness context
    latest_assessment = db.query(ReadinessAssessment).filter(
        ReadinessAssessment.job_id == job_id
    ).order_by(ReadinessAssessment.assessed_at.desc()).first()

    readiness_context = None
    if latest_assessment:
        readiness_context = latest_assessment.full_assessment

    # Extract resume text
    resume_text = extract_text_from_pdf(job.resume_path)

    # Generate questions
    questions_result = generate_interview_questions(
        resume_text=resume_text,
        jd_text=job.jd_text,
        company=job.company,
        role=job.role,
        readiness_context=readiness_context
    )

    # Delete existing questions and save fresh ones
    db.query(InterviewQuestion).filter(
        InterviewQuestion.job_id == job_id
    ).delete()

    questions_list = questions_result.get("questions", [])
    for q in questions_list:
        new_question = InterviewQuestion(
            job_id         = job_id,
            question_text  = q.get("question"),
            question_type  = q.get("type"),
            why_asked      = q.get("why_asked"),
            answer_guide   = q.get("answer_guide"),
            keywords       = ", ".join(q.get("keywords", [])),
            common_mistake = q.get("common_mistake"),
            practiced      = False
        )
        db.add(new_question)

    db.commit()

    return {
        "job_id":    job_id,
        "company":   job.company,
        "role":      job.role,
        "questions": questions_list
    }


# ── MARK QUESTION AS PRACTICED ───────────────────────────────
@router.patch("/questions/{question_id}/practiced")
def mark_question_practiced(question_id: int, request: Request,
    response: Response, db: Session = Depends(get_db)):
    """
    User marks a single interview question as practiced.
    Simple toggle — practiced becomes True.
    """
    session_id = get_or_create_session_id(request, response)
    question = db.query(InterviewQuestion).join(Job).filter(
        InterviewQuestion.id == question_id, Job.session_id == session_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    check_rate_limit(session_id)
    question.practiced = True
    db.commit()
    return {"message": f"Question #{question_id} marked as practiced"}


# ── OUTCOME ANALYTICS ────────────────────────────────────────
@router.get("/analytics")
def get_analytics(request: Request,
    response: Response, db: Session = Depends(get_db)):
    """
    Analyses all job outcomes to find patterns.
    Only meaningful once user has 3+ applications with outcomes.
    """
    session_id = get_or_create_session_id(request, response)

    all_jobs = db.query(Job).filter(Job.session_id == session_id).all()

    if len(all_jobs) < 3:
        return {
            "message": "Add at least 3 job applications to see patterns.",
            "total_jobs": len(all_jobs)
        }
    check_rate_limit(session_id)
    # Build summary for AI analysis
    jobs_summary = []
    for job in all_jobs:
        latest = db.query(ReadinessAssessment).filter(
            ReadinessAssessment.job_id == job.id
        ).order_by(ReadinessAssessment.assessed_at.desc()).first()

        jobs_summary.append({
            "company":        job.company,
            "role":           job.role,
            "status":         job.status,
            "readiness_score": job.readiness_score,
            "match_score":    json.loads(job.analysis).get("match_score")
                              if job.analysis else None,
        })

    analytics_result = analyze_outcomes(jobs_summary)

    return {
        "total_applications": len(all_jobs),
        "analytics":          analytics_result
    }