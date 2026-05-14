from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class JobCreate(BaseModel):
    """
    What the user sends when adding a new job.
    Only company and role are required.
    JD text is optional here — they can add it later.
    """
    company:  str
    role:     str
    job_url:  Optional[str] = None
    jd_text:  Optional[str] = None
    notes:    Optional[str] = None

class JobUpdate(BaseModel):
    """
    What the user sends when updating a job.
    Everything is optional — they might only
    want to change the status, or only the notes.
    """
    status:  Optional[str] = None
    notes:   Optional[str] = None
    jd_text: Optional[str] = None

class JobResponse(BaseModel):
    """
    What the API sends back to the user.
    Includes everything — including the analysis
    result from Gemini if it exists.
    """
    model_config = ConfigDict(from_attributes=True)
     
    id:          int
    company:     str
    role:        str
    status:      str
    job_url:     Optional[str]
    jd_text:     Optional[str]
    resume_path: Optional[str]
    analysis:    Optional[str]
    notes:       Optional[str]
    applied_at:  datetime


class AnalysisResponse(BaseModel):
    """
    The structured output from Gemini analysis.
    This is what gets saved in the analysis column
    and shown to the user on the dashboard.
    """
    match_score:      int
    matched_skills:   list[str]
    missing_skills:   list[str]
    experience_match: str
    verdict:          str
    preparation_tips: list[str]