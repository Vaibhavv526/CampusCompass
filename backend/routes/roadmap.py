from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.core.rate_limit import rate_limit_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.context_service import get_latest_assessment_activity
from models.skill import Skill
from models.student import StudentProfile
from models.assessment_schema import LearningAssessmentResponse
from orchestrator import StudentMentorOrchestrator

from backend.schemas.student import StudentInput


router = APIRouter(
    prefix="/api/roadmap",
    tags=["Roadmap"],
)


class RoadmapRequest(BaseModel):
    student: StudentInput
    assessment: LearningAssessmentResponse | None = None


@router.post("")
def create_roadmap(
    request: RoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_user(max_requests=5, window_seconds=60, group="roadmap")),
):
    student = StudentProfile(
        name=current_user.full_name,
        email=current_user.email,
        degree=request.student.degree,
        branch=request.student.branch,
        current_year=request.student.current_year,
        semester=request.student.semester,
        career_goal=request.student.career_goal,
        interests=request.student.interests,
        weekly_hours=request.student.weekly_hours,
        skills=[
            Skill(
                skill.name,
                skill.category,
                skill.current_level,
                skill.target_level,
            )
            for skill in request.student.skills
        ],
    )

    orchestrator = StudentMentorOrchestrator(
        student=student,
        topic="General",
    )

    assessment = request.assessment
    if assessment is None:
        assessment = get_latest_assessment_activity(db, current_user.id)

    result = orchestrator.generate_roadmap(
        assessment=assessment
    )

    return result
