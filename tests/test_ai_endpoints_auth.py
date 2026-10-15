import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from models.tutor_schema import TutorResponse
from models.quiz_schema import QuizResponse, QuizQuestion
from models.recommendation_schema import RecommendationResponse, RecommendationResource
from models.assessment_schema import (
    LearningAssessmentResponse,
    StudentAssessmentSummary,
    SkillGapResponse,
    LearningRecommendation,
)


class TestAIEndpointsSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.test_email = "ai_sec_test@campuscompass.org"
        cls.test_password = "SecurePassword123!"

        cls._cleanup_user()

        # Register dedicated test user
        reg_res = cls.client.post(
            "/auth/register",
            json={
                "full_name": "AI Security Test User",
                "email": cls.test_email,
                "password": cls.test_password,
            },
        )
        assert reg_res.status_code == 201, f"Test user registration failed: {reg_res.text}"

        # Login to obtain valid JWT token
        login_res = cls.client.post(
            "/auth/login",
            data={
                "username": cls.test_email,
                "password": cls.test_password,
            },
        )
        assert login_res.status_code == 200, f"Test user login failed: {login_res.text}"
        cls.token = login_res.json()["access_token"]
        cls.valid_headers = {"Authorization": f"Bearer {cls.token}"}
        cls.invalid_headers = {"Authorization": "Bearer invalid_or_expired_jwt_token_12345"}

        # Base student payload for tests
        cls.student_payload = {
            "name": "AI Security Test User",
            "email": cls.test_email,
            "degree": "B.Tech",
            "branch": "Computer Science",
            "current_year": 3,
            "semester": 5,
            "career_goal": "Machine Learning Engineer",
            "interests": ["Python", "Deep Learning"],
            "weekly_hours": 15.0,
            "skills": [
                {
                    "name": "Python",
                    "category": "Technical",
                    "current_level": 75.0,
                    "target_level": 95.0,
                }
            ],
        }

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_user()
        cls.db.close()

    @classmethod
    def _cleanup_user(cls):
        try:
            user = (
                cls.db.query(User)
                .filter(User.email == cls.test_email)
                .first()
            )
            if user:
                cls.db.delete(user)
                cls.db.commit()
        except Exception:
            cls.db.rollback()

    def test_01_assessment_endpoint_auth(self):
        """POST /api/assessment requires valid authentication."""
        endpoint = "/api/assessment"

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=self.student_payload)
        self.assertEqual(res_no_auth.status_code, 401)
        self.assertEqual(res_no_auth.headers.get("WWW-Authenticate"), "Bearer")

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=self.student_payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked orchestrator)
        mock_response = {
            "summary": {
                "student_name": "AI Security Test User",
                "degree": "B.Tech",
                "branch": "Computer Science",
                "current_year": 3,
                "semester": 5,
                "career_goal": "Machine Learning Engineer",
                "weekly_study_hours": 15.0,
            },
            "skill_gaps": [],
            "recommendations": [],
        }

        with patch("backend.routes.assessment.StudentMentorOrchestrator.assess_student", return_value=mock_response) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=self.student_payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["summary"]["student_name"], "AI Security Test User")

    def test_02_roadmap_endpoint_auth(self):
        """POST /api/roadmap requires valid authentication."""
        endpoint = "/api/roadmap"
        payload = {
            "student": self.student_payload,
            "assessment": {
                "summary": {
                    "student_name": "AI Security Test User",
                    "degree": "B.Tech",
                    "branch": "Computer Science",
                    "current_year": 3,
                    "semester": 5,
                    "career_goal": "Machine Learning Engineer",
                    "weekly_study_hours": 15.0,
                },
                "skill_gaps": [],
                "recommendations": [],
            },
        }

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked orchestrator)
        mock_response = {
            "title": "Machine Learning Roadmap",
            "milestones": ["Python Basics", "Linear Algebra", "PyTorch"],
        }

        with patch("backend.routes.roadmap.StudentMentorOrchestrator.generate_roadmap", return_value=mock_response) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["title"], "Machine Learning Roadmap")

    def test_03_tutor_endpoint_auth(self):
        """POST /api/tutor requires valid authentication."""
        endpoint = "/api/tutor"
        payload = {
            "student": self.student_payload,
            "topic": "Neural Networks",
            "question": "What is backpropagation?",
        }

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked orchestrator returning TutorResponse)
        mock_tutor_resp = TutorResponse(
            topic="Neural Networks",
            explanation="Backpropagation calculates gradients of the loss function.",
            key_points=["Chain rule", "Gradient descent"],
            example="loss.backward()",
            practice_task="Implement single layer backprop in NumPy",
        )

        with patch("backend.routes.tutor.StudentMentorOrchestrator.ask_tutor", return_value=mock_tutor_resp) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["topic"], "Neural Networks")
            self.assertIn("Chain rule", res_valid.json()["key_points"])

    def test_04_quiz_generate_endpoint_auth(self):
        """POST /api/quiz requires valid authentication."""
        endpoint = "/api/quiz"
        payload = {
            "student": self.student_payload,
            "topic": "Python OOP",
            "num_questions": 3,
        }

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked orchestrator returning QuizResponse)
        mock_quiz_resp = QuizResponse(
            topic="Python OOP",
            difficulty="Medium",
            questions=[
                QuizQuestion(
                    question="What keyword is used for inheritance in Python?",
                    options=["extends", "class Child(Parent):", "implements", "inherits"],
                    correct_answer="class Child(Parent):",
                    explanation="Parent class is passed inside parentheses.",
                )
            ],
        )

        with patch("backend.routes.quiz.StudentMentorOrchestrator.generate_quiz", return_value=mock_quiz_resp) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["topic"], "Python OOP")
            self.assertEqual(len(res_valid.json()["questions"]), 1)

    def test_05_quiz_evaluate_endpoint_auth(self):
        """POST /api/quiz/evaluate requires valid authentication."""
        endpoint = "/api/quiz/evaluate"
        payload = {
            "quiz": {
                "topic": "Python OOP",
                "difficulty": "Medium",
                "questions": [
                    {
                        "question": "What keyword is used for inheritance?",
                        "options": ["extends", "class Child(Parent):"],
                        "correct_answer": "class Child(Parent):",
                        "explanation": "Parent class in parens.",
                    }
                ],
            },
            "student_answers": ["class Child(Parent):"],
        }

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked evaluation agent)
        mock_eval_resp = {
            "topic": "Python OOP",
            "total_questions": 1,
            "correct_answers": 1,
            "score_percentage": 100.0,
            "question_results": [
                {
                    "question": "What keyword is used for inheritance?",
                    "student_answer": "class Child(Parent):",
                    "correct_answer": "class Child(Parent):",
                    "is_correct": True,
                    "explanation": "Parent class in parens.",
                }
            ],
            "weak_topics": [],
            "recommendation": "Excellent grasp of Python inheritance.",
        }

        with patch("backend.routes.quiz.QuizEvaluationAgent.evaluate", return_value=mock_eval_resp) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["score_percentage"], 100.0)

    def test_06_recommendations_endpoint_auth(self):
        """POST /api/recommendations requires valid authentication."""
        endpoint = "/api/recommendations"

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=self.student_payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=self.student_payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked recommendation agent)
        mock_rec_resp = RecommendationResponse(
            summary="Recommended learning trajectory for ML Engineer.",
            recommended_skills=["NumPy", "Pandas", "Scikit-Learn"],
            recommended_projects=["House Price Prediction", "Sentiment Analyzer"],
            recommended_resources=[
                RecommendationResource(
                    title="Official Python Docs",
                    link="https://docs.python.org",
                    type="Documentation",
                )
            ],
            next_steps=["Complete PyTorch tutorial", "Build portfolio project"],
        )

        with patch("backend.routes.recommendation.RecommendationAgent.recommend", return_value=mock_rec_resp) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=self.student_payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(len(res_valid.json()["recommended_skills"]), 3)

    def test_07_skill_analysis_endpoint_auth(self):
        """POST /api/skill-analysis requires valid authentication."""
        endpoint = "/api/skill-analysis"
        payload = {
            "skills": [
                {
                    "name": "Python",
                    "proficiency": 80,
                    "strengths": "Object oriented design",
                    "weak_areas": "Asynchronous programming",
                    "experience": "2 years academic projects",
                }
            ]
        }

        # 1. Without credentials -> 401
        res_no_auth = self.client.post(endpoint, json=payload)
        self.assertEqual(res_no_auth.status_code, 401)

        # 2. With invalid credentials -> 401
        res_invalid = self.client.post(endpoint, headers=self.invalid_headers, json=payload)
        self.assertEqual(res_invalid.status_code, 401)

        # 3. With valid credentials -> 200 (mocked skill analysis agent)
        mock_analysis_resp = {
            "summary": "Overall good foundational competency.",
            "skills": [
                {
                    "name": "Python",
                    "proficiency": 80,
                    "strengths": ["Object oriented design"],
                    "weak_areas": ["Asynchronous programming"],
                    "gap": "Needs hands-on asyncio practice",
                    "next_steps": ["Build async API with FastAPI"],
                }
            ],
        }

        with patch("backend.routes.skill_analysis.SkillAnalysisAgent.analyze", return_value=mock_analysis_resp) as mock_method:
            res_valid = self.client.post(endpoint, headers=self.valid_headers, json=payload)
            self.assertEqual(res_valid.status_code, 200)
            mock_method.assert_called_once()
            self.assertEqual(res_valid.json()["summary"], "Overall good foundational competency.")

    def test_08_public_endpoints_remain_accessible(self):
        """Verify public endpoints (/api/health, /auth/login, /auth/register) remain accessible without auth."""
        # Health check should be 200 without credentials
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        # Register endpoint does not require auth header (bad payload triggers 422, not 401)
        res_reg_bad = self.client.post("/auth/register", json={})
        self.assertEqual(res_reg_bad.status_code, 422)

        # Login endpoint does not require auth header (bad payload triggers 422, not 401)
        res_login_bad = self.client.post("/auth/login", data={})
        self.assertEqual(res_login_bad.status_code, 422)


if __name__ == "__main__":
    unittest.main()
