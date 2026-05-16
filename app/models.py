from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(String(36), nullable=True, index=True)  
    company         = Column(String(100), nullable=False)
    role            = Column(String(100), nullable=False)
    status          = Column(String(20), default="interested")  # V2: starts as interested
    job_url         = Column(String(500), nullable=True)
    jd_text         = Column(Text, nullable=True)
    resume_path     = Column(String(500), nullable=True)
    analysis        = Column(Text, nullable=True)               # V1 skill gap analysis
    notes           = Column(String(500), nullable=True)
    readiness_score = Column(Integer, nullable=True)            # V2: latest readiness %
    applied_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships — SQLAlchemy loads related rows automatically
    assessments      = relationship("ReadinessAssessment", back_populates="job",
                                    cascade="all, delete-orphan")
    roadmap          = relationship("PrepRoadmap", back_populates="job",
                                    uselist=False, cascade="all, delete-orphan")
    questions        = relationship("InterviewQuestion", back_populates="job",
                                    cascade="all, delete-orphan")


class CompanyResearch(Base):
    """
    Stores research results per company name.
    One row per unique company — reused across multiple jobs.
    If user applies to Google twice, research is fetched once.
    """
    __tablename__ = "company_research"

    id               = Column(Integer, primary_key=True, index=True)
    company_name     = Column(String(100), nullable=False, unique=True, index=True)
    company_type     = Column(String(50), nullable=True)
    what_they_do     = Column(Text, nullable=True)
    role_summary     = Column(Text, nullable=True)
    interview_style  = Column(Text, nullable=True)
    cs_topics_json   = Column(Text, nullable=True)  # JSON: {topic: depth_level}
    raw_research     = Column(Text, nullable=True)  # full JSON from AI
    researched_at    = Column(DateTime, default=datetime.utcnow)


class ReadinessAssessment(Base):
    """
    Stores every readiness check run for a job.
    Multiple rows per job — tracks improvement over time.
    When user re-assesses after studying, new row is created.
    Score history shows their progress.
    """
    __tablename__ = "readiness_assessments"

    id                    = Column(Integer, primary_key=True, index=True)
    job_id                = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    overall_score         = Column(Integer, nullable=False)   # 0-100
    technical_score       = Column(Integer, nullable=True)    # 0-100
    fundamentals_score    = Column(Integer, nullable=True)    # 0-100
    projects_score        = Column(Integer, nullable=True)    # 0-100
    confidence_level      = Column(String(20), nullable=True) # not ready/building/ready/strong
    gaps_json             = Column(Text, nullable=True)       # JSON list of gaps
    cs_gaps_json          = Column(Text, nullable=True)       # JSON list of CS gaps
    verdict               = Column(String(50), nullable=True) # apply now / prepare first
    estimated_days        = Column(Integer, nullable=True)    # days to be ready
    full_assessment       = Column(Text, nullable=True)       # complete JSON from AI
    assessed_at           = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="assessments")


class PrepRoadmap(Base):
    """
    Stores the preparation roadmap generated for a job.
    One roadmap per job (uselist=False in Job relationship).
    Regenerated when user re-assesses and score changes.
    """
    __tablename__ = "prep_roadmaps"

    id             = Column(Integer, primary_key=True, index=True)
    job_id         = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True)
    total_days     = Column(Integer, nullable=False)
    roadmap_json   = Column(Text, nullable=False)  # full day by day plan as JSON
    generated_at   = Column(DateTime, default=datetime.utcnow)
    completed_at   = Column(DateTime, nullable=True)  # set when user marks complete

    job = relationship("Job", back_populates="roadmap")


class InterviewQuestion(Base):
    """
    Stores each interview question as its own row.
    Multiple rows per job.
    user can mark individual questions as practiced.
    Allows querying: "show me only unpracticed questions"
    """
    __tablename__ = "interview_questions"

    id             = Column(Integer, primary_key=True, index=True)
    job_id         = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    question_text  = Column(Text, nullable=False)
    question_type  = Column(String(50), nullable=True)  # technical/fundamentals/project/situation
    why_asked      = Column(Text, nullable=True)
    answer_guide   = Column(Text, nullable=True)
    keywords       = Column(Text, nullable=True)        # comma separated
    common_mistake = Column(Text, nullable=True)
    practiced      = Column(Boolean, default=False)     # user marks this
    created_at     = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="questions")