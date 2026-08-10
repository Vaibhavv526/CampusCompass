from agents.roadmap_agent import RoadmapAgent
from agents.assessment_agent import AssessmentAgent
from agents.tutor_agent import TutorAgent
from agents.quiz_agent import QuizAgent
from agents.quiz_evaluation_agent import QuizEvaluationAgent
from agents.recommendation_agent import RecommendationAgent

from models.student import StudentProfile


class StudentMentorOrchestrator:
    """Coordinates the specialized AI agents for a student."""

    def __init__(self, student: StudentProfile, topic: str):
        self.student = student
        self.topic = topic

        self.roadmap_agent = RoadmapAgent()
        self.assessment_agent = AssessmentAgent()
        self.tutor_agent = TutorAgent()
        self.quiz_agent = QuizAgent()
        self.quiz_evaluation_agent = QuizEvaluationAgent()
        self.recommendation_agent = RecommendationAgent()

    def generate_quiz(self, num_questions: int = 5):
        """Generate a personalized quiz for the current study topic."""

        return self.quiz_agent.generate(
            topic=self.topic,
            knowledge_level=self._get_knowledge_level(),
            learning_goal=self.student.career_goal,
            num_questions=num_questions,
        )
    def evaluate_quiz(
        self,
        quiz,
        student_answers: list[str],
    ):
        """Evaluate a completed quiz."""

        return self.quiz_evaluation_agent.evaluate(
            quiz=quiz,
            student_answers=student_answers,
        )

    def _get_knowledge_level(self) -> str:
        """Infer a basic knowledge level from the student's skills."""

        if not self.student.skills:
            return "beginner"

        average_level = sum(
            skill.current_level
            for skill in self.student.skills
        ) / len(self.student.skills)

        if average_level < 40:
            return "beginner"
        elif average_level < 70:
            return "intermediate"
        else:
            return "advanced"