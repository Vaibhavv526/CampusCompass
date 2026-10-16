from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.core.rate_limit import rate_limit_user
from backend.database.session import get_db
from backend.models.user import User
from backend.services.context_service import get_quiz_context
from models.skill import Skill
from models.quiz_schema import QuizResponse
from orchestrator import StudentMentorOrchestrator

from backend.schemas.student import StudentInput
from agents.quiz_evaluation_agent import QuizEvaluationAgent
from models.student import StudentProfile

router = APIRouter(
    prefix="/api/quiz",
    tags=["Quiz"],
)


class QuizRequest(BaseModel):
    student: StudentInput
    topic: str
    num_questions: int = 5
    weak_areas: list[str] | None = None
    roadmap_milestone: str | None = None


@router.post("", response_model=QuizResponse)
def generate_quiz(
    request: QuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_user(max_requests=15, window_seconds=60, group="quiz_generate")),
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

    quiz_ctx = get_quiz_context(db, current_user.id)
    weak_areas = request.weak_areas if request.weak_areas is not None else quiz_ctx.get("weak_areas")
    roadmap_milestone = request.roadmap_milestone or quiz_ctx.get("roadmap_milestone")

    kwargs = {"num_questions": request.num_questions}
    if weak_areas:
        kwargs["weak_areas"] = weak_areas
    if roadmap_milestone:
        kwargs["roadmap_milestone"] = roadmap_milestone

    result = orchestrator.generate_quiz(**kwargs)

    return result


class QuizEvaluationRequest(BaseModel):
    quiz: QuizResponse
    student_answers: list[str]


@router.post("/evaluate")
def evaluate_quiz(
    request: QuizEvaluationRequest,
    current_user: User = Depends(get_current_user),
    _rate_limit: None = Depends(rate_limit_user(max_requests=15, window_seconds=60, group="quiz_evaluate")),
):
    evaluator = QuizEvaluationAgent()

    return evaluator.evaluate(
        quiz=request.quiz,
        student_answers=request.student_answers,
    )
