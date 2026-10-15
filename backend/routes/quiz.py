from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.models.user import User
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


@router.post("", response_model=QuizResponse)
def generate_quiz(
    request: QuizRequest,
    current_user: User = Depends(get_current_user),
):
    student = StudentProfile(
        name=request.student.name,
        email=request.student.email,
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

    result = orchestrator.generate_quiz(
        num_questions=request.num_questions
    )


    return result
class QuizEvaluationRequest(BaseModel):
    quiz: QuizResponse
    student_answers: list[str]


@router.post("/evaluate")
def evaluate_quiz(
    request: QuizEvaluationRequest,
    current_user: User = Depends(get_current_user),
):
    evaluator = QuizEvaluationAgent()

    return evaluator.evaluate(
        quiz=request.quiz,
        student_answers=request.student_answers,
    )
