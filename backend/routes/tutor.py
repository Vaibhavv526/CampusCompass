from fastapi import APIRouter
from pydantic import BaseModel

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


@router.post("", response_model=TutorResponse)
def ask_tutor(request: TutorRequest):
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

    result = orchestrator.ask_tutor(
        question=request.question
    )

    return result