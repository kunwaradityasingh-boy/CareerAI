from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ResumeAnalysis, User
from backend.routers.auth import get_current_user
from backend.schemas.resume import (
    ResumeAnalyzeTextRequest,
    ResumeAnalysisResponse,
    ResumeAnalysisSummary,
)
from backend.services.resume_analyzer_service import (
    analyze_resume_content,
    extract_text_from_pdf,
)

router = APIRouter(
    prefix="/api/v1/resume",
    tags=["Resume Analyzer"],
)


@router.post(
    "/analyze-text",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_resume_text(
    payload: ResumeAnalyzeTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        results = analyze_resume_content(
            resume_text=payload.resume_text,
            target_role=payload.target_role,
            job_description=payload.job_description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    analysis = ResumeAnalysis(
        user_id=current_user.id,
        file_name=payload.file_name or "Pasted Resume Text",
        target_role=payload.target_role,
        overall_score=results["overall_score"],
        ats_compatibility=results["ats_compatibility"],
        skills_score=results["skills_score"],
        impact_score=results["impact_score"],
        structure_score=results["structure_score"],
        strengths=results["strengths"],
        weaknesses=results["weaknesses"],
        found_keywords=results["found_keywords"],
        missing_keywords=results["missing_keywords"],
        recommendations=results["recommendations"],
        section_feedback=results["section_feedback"],
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post(
    "/upload",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_analyze_resume(
    file: UploadFile = File(...),
    target_role: str = Form(...),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate file extension
    file_name = file.filename or "resume.pdf"
    lower_name = file_name.lower()

    if not (lower_name.endswith(".pdf") or lower_name.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF (.pdf) and text (.txt) files are supported.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 5MB limit.",
        )

    if lower_name.endswith(".pdf"):
        try:
            resume_text = extract_text_from_pdf(file_bytes)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
    else:
        try:
            resume_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            resume_text = file_bytes.decode("latin-1", errors="ignore")

    try:
        results = analyze_resume_content(
            resume_text=resume_text,
            target_role=target_role,
            job_description=job_description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    analysis = ResumeAnalysis(
        user_id=current_user.id,
        file_name=file_name,
        target_role=target_role,
        overall_score=results["overall_score"],
        ats_compatibility=results["ats_compatibility"],
        skills_score=results["skills_score"],
        impact_score=results["impact_score"],
        structure_score=results["structure_score"],
        strengths=results["strengths"],
        weaknesses=results["weaknesses"],
        found_keywords=results["found_keywords"],
        missing_keywords=results["missing_keywords"],
        recommendations=results["recommendations"],
        section_feedback=results["section_feedback"],
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get(
    "/history",
    response_model=List[ResumeAnalysisSummary],
)
def get_user_resume_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all past resume analyses for the logged-in user."""
    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == current_user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .limit(20)
        .all()
    )
    return analyses


@router.get(
    "/{analysis_id}",
    response_model=ResumeAnalysisResponse,
)
def get_resume_analysis_detail(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a specific resume analysis."""
    analysis = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == analysis_id,
            ResumeAnalysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis report not found.",
        )

    return analysis


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_resume_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an analysis report belonging to the current user."""
    analysis = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == analysis_id,
            ResumeAnalysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis report not found.",
        )

    db.delete(analysis)
    db.commit()
    return None
