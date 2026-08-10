from pydantic import BaseModel, Field
from typing import List


class QuizQuestion(BaseModel):
    """Represents one quiz question."""

    question: str
    options: List[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """Structured quiz generated for a student."""

    topic: str
    difficulty: str
    questions: List[QuizQuestion] = Field(default_factory=list)