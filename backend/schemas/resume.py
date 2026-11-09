from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResumeAnalyzeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, max_length=50000)
    target_role: str = Field(..., min_length=2, max_length=120)
    file_name: Optional[str] = Field("pasted_resume.txt", max_length=255)
    job_description: Optional[str] = Field(None, max_length=10000)


class ResumeAnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    target_role: str
    overall_score: int
    ats_compatibility: int
    skills_score: int
    created_at: datetime


class ResumeAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    file_name: str
    target_role: str
    overall_score: int
    ats_compatibility: int
    skills_score: int
    impact_score: int
    structure_score: int
    strengths: List[str]
    weaknesses: List[str]
    found_keywords: List[str]
    missing_keywords: List[str]
    recommendations: List[str]
    section_feedback: Dict[str, Any]
    created_at: datetime
