from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.core.rate_limit import rate_limit_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.context_service import get_tutor_context
from models.skill import Skill
from models.student import StudentProfile
from models.tutor_schema import TutorResponse
from orchestrator import StudentMentorOrchestrator

from backend.schemas.student import StudentInput


router = APIRouter(
    prefix="/api/tutor",
    tags=["Tutor"],
)


class TutorRequest(BaseModel):
    student: StudentInput
    topic: str
    question: str
    roadmap_goal: str | None = None
    skill_gaps: list[str] | None = None
    recent_history: list[str] | None = None


@router.post("", response_model=TutorResponse)
def ask_tutor(
    request: TutorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_user(max_requests=15, window_seconds=60, group="tutor")),
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
        topic=request.topic,
    )

    # Contextual learning resolution
    tutor_ctx = get_tutor_context(db, current_user.id)
    roadmap_goal = request.roadmap_goal or tutor_ctx.get("roadmap_goal")
    skill_gaps = request.skill_gaps if request.skill_gaps is not None else tutor_ctx.get("skill_gaps")
    recent_history = request.recent_history if request.recent_history is not None else tutor_ctx.get("recent_history")

    kwargs = {"question": request.question}
    if roadmap_goal:
        kwargs["roadmap_goal"] = roadmap_goal
    if skill_gaps:
        kwargs["skill_gaps"] = skill_gaps
    if recent_history:
        kwargs["recent_history"] = recent_history

    result = orchestrator.ask_tutor(**kwargs)

    return result
