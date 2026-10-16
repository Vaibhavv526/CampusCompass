import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.learning_activity import LearningActivity
from backend.schemas.learning_activity import LearningActivityCreate
import orchestrator
from orchestrator import StudentMentorOrchestrator


class TestStudentJourneyHistoryAndOrchestrator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.email = "journey_student@campuscompass.org"
        cls.password = "ValidPassword123!"

        cls._cleanup()

        # Register User
        res = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Journey Student",
                "email": cls.email,
                "password": cls.password,
            },
        )
        assert res.status_code == 201, f"Registration failed: {res.text}"

        # Login User
        login_res = cls.client.post(
            "/auth/login",
            data={
                "username": cls.email,
                "password": cls.password,
            },
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        cls.token = login_res.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.db.close()

    @classmethod
    def _cleanup(cls):
        user = cls.db.query(User).filter(User.email == cls.email).first()
        if user:
            cls.db.query(LearningActivity).filter(LearningActivity.user_id == user.id).delete()
            cls.db.delete(user)
            cls.db.commit()

    # --- 1. Schema Validation Tests ---

    def test_schema_valid_activity_types(self):
        """Verify all valid journey activity types are accepted by LearningActivityCreate."""
        for act_type in ["tutor", "practice", "assessment", "quiz", "roadmap"]:
            payload = LearningActivityCreate(
                activity_type=act_type,
                title=f"Sample {act_type} Title",
                summary=f"Sample {act_type} summary content",
                score=85.0 if act_type == "quiz" else None,
                data={"key": "value"},
            )
            self.assertEqual(payload.activity_type, act_type)

    def test_schema_rejects_invalid_activity_type(self):
        """Verify invalid activity types are rejected."""
        with self.assertRaises(ValidationError):
            LearningActivityCreate(
                activity_type="invalid_journey_type",
                title="Invalid",
                summary="Invalid type test",
            )

    def test_schema_length_constraints(self):
        """Verify title (255) and summary (1000) field constraints."""
        with self.assertRaises(ValidationError):
            LearningActivityCreate(
                activity_type="tutor",
                title="A" * 256,
                summary="Valid summary",
            )

        with self.assertRaises(ValidationError):
            LearningActivityCreate(
                activity_type="tutor",
                title="Valid Title",
                summary="B" * 1001,
            )

    # --- 2. API Endpoint Persistence Tests ---

    def test_persist_tutor_interaction(self):
        """Test persisting tutor Q&A interaction to learning history."""
        payload = {
            "activity_type": "tutor",
            "title": "AI Tutor: Binary Search Trees",
            "summary": "Q: How do BSTs work? - A: A binary search tree is a rooted binary tree...",
            "score": None,
            "data": {
                "question": "How do BSTs work?",
                "response": "A binary search tree is a rooted binary tree data structure.",
            },
        }
        res = self.client.post("/api/learning-history", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["activity_type"], "tutor")
        self.assertEqual(data["title"], payload["title"])
        self.assertIn("BSTs", data["summary"])

    def test_persist_recommendation_interaction(self):
        """Test persisting recommendation interaction to learning history."""
        payload = {
            "activity_type": "practice",
            "title": "Career Recommendations (Cloud Engineer)",
            "summary": "AI generated personalized career milestones and project suggestions.",
            "score": None,
            "data": {
                "recommendations": ["Learn Terraform", "Build Kubernetes cluster"],
            },
        }
        res = self.client.post("/api/learning-history", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["activity_type"], "practice")
        self.assertEqual(data["title"], payload["title"])

    def test_persist_skill_analysis_interaction(self):
        """Test persisting skill gap analysis to learning history."""
        payload = {
            "activity_type": "assessment",
            "title": "Skill Gap Analysis: Python, Docker, AWS",
            "summary": "Identified proficiency gaps in container orchestration and AWS IAM.",
            "score": None,
            "data": {
                "gaps": ["Docker security", "Kubernetes networking"],
            },
        }
        res = self.client.post("/api/learning-history", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["activity_type"], "assessment")
        self.assertEqual(data["title"], payload["title"])

    def test_retrieve_learning_history_contains_journey_activities(self):
        """Verify that GET /api/learning-history returns persisted journey activities."""
        res = self.client.get("/api/learning-history", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        types = [item["activity_type"] for item in items]
        self.assertIn("tutor", types)
        self.assertIn("practice", types)
        self.assertIn("assessment", types)

    # --- 3. Orchestrator evaluate_quiz Cleanup Tests ---

    def test_orchestrator_evaluate_quiz_single_definition(self):
        """Verify orchestrator source code contains evaluate_quiz exactly once."""
        with open(orchestrator.__file__, "r", encoding="utf-8") as f:
            src = f.read()

        method_defs = [line for line in src.splitlines() if line.strip().startswith("def evaluate_quiz")]
        self.assertEqual(len(method_defs), 1, f"Expected exactly 1 evaluate_quiz def, found: {method_defs}")

    @patch("orchestrator.TutorAgent")
    @patch("orchestrator.RoadmapAgent")
    @patch("orchestrator.QuizEvaluationAgent")
    def test_orchestrator_evaluate_quiz_execution(self, mock_quiz_eval_cls, mock_roadmap_cls, mock_tutor_cls):
        """Verify StudentMentorOrchestrator.evaluate_quiz delegates correctly to QuizEvaluationAgent.evaluate."""
        mock_instance = MagicMock()
        mock_instance.evaluate.return_value = {"score": 90, "total": 100, "feedback": "Excellent"}
        mock_quiz_eval_cls.return_value = mock_instance

        mock_student = MagicMock()
        orch = StudentMentorOrchestrator(student=mock_student, topic="Python")
        answers = ["B", "A", "C"]
        mock_quiz = MagicMock()

        result = orch.evaluate_quiz(quiz=mock_quiz, student_answers=answers)
        mock_instance.evaluate.assert_called_once_with(quiz=mock_quiz, student_answers=answers)
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
