from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id           = Column(Integer, primary_key=True, index=True)
    company      = Column(String(100), nullable=False)
    role         = Column(String(100), nullable=False)
    status       = Column(String(20), default="applied")
    job_url      = Column(String(500), nullable=True)
    jd_text      = Column(Text, nullable=True)
    resume_path  = Column(String(500), nullable=True)
    analysis     = Column(Text, nullable=True)
    notes        = Column(String(500), nullable=True)
    applied_at   = Column(DateTime, default=datetime.utcnow)