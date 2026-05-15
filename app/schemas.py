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


class CompanyResearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    company_name:    str
    company_type:    Optional[str]
    what_they_do:    Optional[str]
    role_summary:    Optional[str]
    interview_style: Optional[str]
    cs_topics_json:  Optional[str]
    researched_at:   datetime


class ReadinessAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 int
    job_id:             int
    overall_score:      int
    technical_score:    Optional[int]
    fundamentals_score: Optional[int]
    projects_score:     Optional[int]
    confidence_level:   Optional[str]
    verdict:            Optional[str]
    estimated_days:     Optional[int]
    full_assessment:    Optional[str]
    assessed_at:        datetime


class PrepRoadmapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    job_id:       int
    total_days:   int
    roadmap_json: str
    generated_at: datetime
    completed_at: Optional[datetime]


class InterviewQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             int
    job_id:         int
    question_text:  str
    question_type:  Optional[str]
    why_asked:      Optional[str]
    answer_guide:   Optional[str]
    keywords:       Optional[str]
    common_mistake: Optional[str]
    practiced:      bool
    created_at:     datetime