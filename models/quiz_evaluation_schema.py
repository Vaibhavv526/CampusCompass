from pydantic import BaseModel, Field
from typing import List


class QuestionEvaluation(BaseModel):
    """Evaluation result for one quiz question."""

    question: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizEvaluationResponse(BaseModel):
    """Overall evaluation of a completed quiz."""

    topic: str
    total_questions: int
    correct_answers: int
    score_percentage: float = Field(ge=0, le=100)
    question_results: List[QuestionEvaluation] = Field(
        default_factory=list
    )
    weak_topics: List[str] = Field(default_factory=list)
    recommendation: str