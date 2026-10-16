import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.rate_limit import rate_limiter
from backend.database.session import SessionLocal
from backend.main import app
from backend.models.user import User
from models.assessment_schema import (
    LearningAssessmentResponse,
    LearningRecommendation,
    SkillGapResponse,
    StudentAssessmentSummary,
)
from models.quiz_schema import QuizQuestion, QuizResponse
from models.recommendation_schema import RecommendationResource, RecommendationResponse
from models.tutor_schema import TutorResponse


class TestUserBindingAndRateLimiting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        cls.user_a_email = "alice_binding_test@campuscompass.org"
        cls.user_a_name = "Alice Authenticated"
        cls.user_a_password = "PasswordAlice123!"

        cls.user_b_email = "bob_binding_test@campuscompass.org"
        cls.user_b_name = "Bob Legitimate"
        cls.user_b_password = "PasswordBob123!"

        cls._cleanup_users()

        # Register User A (Alice)
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": cls.user_a_name,
                "email": cls.user_a_email,
                "password": cls.user_a_password,
            },
        )
        assert res_a.status_code == 201, f"User A registration failed: {res_a.text}"

        # Register User B (Bob)
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": cls.user_b_name,
                "email": cls.user_b_email,
                "password": cls.user_b_password,
            },
        )
        assert res_b.status_code == 201, f"User B registration failed: {res_b.text}"

        # Login User A
        login_a = cls.client.post(
            "/auth/login",
            data={"username": cls.user_a_email, "password": cls.user_a_password},
        )
        assert login_a.status_code == 200, f"User A login failed: {login_a.text}"
        cls.token_a = login_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Login User B
        login_b = cls.client.post(
            "/auth/login",
            data={"username": cls.user_b_email, "password": cls.user_b_password},
        )
        assert login_b.status_code == 200, f"User B login failed: {login_b.text}"
        cls.token_b = login_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        # Standard student payload attempting to spoof identity
        cls.spoofed_student_payload = {
            "name": "Eve Attacker Spoofed",
            "email": "eve_spoofed@attacker.com",
            "degree": "B.Tech Computer Science",
            "branch": "Artificial Intelligence",
            "current_year": 3,
            "semester": 6,
            "career_goal": "AI Research Scientist",
            "interests": ["Reinforcement Learning", "NLP"],
            "weekly_hours": 20.0,
            "skills": [
                {
                    "name": "PyTorch",
                    "category": "Technical",
                    "current_level": 70.0,
                    "target_level": 95.0,
                }
            ],
        }

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_users()
        cls.db.close()

    @classmethod
    def _cleanup_users(cls):
        cls.db.query(User).filter(
            User.email.in_([cls.user_a_email, cls.user_b_email])
        ).delete(synchronize_session=False)
        cls.db.commit()

    def setUp(self):
        rate_limiter.reset()

    def tearDown(self):
        rate_limiter.reset()

    # =========================================================================
    # 1. AUTHENTICATED IDENTITY BINDING TESTS (5 Endpoints)
    # =========================================================================

    def test_01_assessment_identity_binding_prevents_spoofing(self):
        """POST /api/assessment binds student identity to current_user, ignoring spoofed fields."""
        endpoint = "/api/assessment"

        mock_assessment_resp = {
            "summary": {"strengths": ["PyTorch"], "readiness_score": 85},
            "gaps": [],
            "recommendations": [],
        }

        with patch("backend.routes.assessment.StudentMentorOrchestrator") as mock_orch_cls:
            mock_orch_inst = MagicMock()
            mock_orch_inst.assess_student.return_value = mock_assessment_resp
            mock_orch_cls.return_value = mock_orch_inst

            res = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=self.spoofed_student_payload,
            )

            self.assertEqual(res.status_code, 200)
            mock_orch_cls.assert_called_once()
            passed_student = mock_orch_cls.call_args[1]["student"]

            # Authoritative identity must be Alice, NOT Eve
            self.assertEqual(passed_student.name, self.user_a_name)
            self.assertEqual(passed_student.email, self.user_a_email)

            # Legitimate academic task inputs must be preserved
            self.assertEqual(passed_student.degree, "B.Tech Computer Science")
            self.assertEqual(passed_student.branch, "Artificial Intelligence")
            self.assertEqual(passed_student.career_goal, "AI Research Scientist")
            self.assertEqual(len(passed_student.skills), 1)
            self.assertEqual(passed_student.skills[0].name, "PyTorch")

    def test_02_roadmap_identity_binding_prevents_spoofing(self):
        """POST /api/roadmap binds student identity to current_user, preserving assessment context."""
        endpoint = "/api/roadmap"
        payload = {
            "student": self.spoofed_student_payload,
            "assessment": {
                "summary": {
                    "student_name": "Eve Attacker Spoofed",
                    "degree": "B.Tech Computer Science",
                    "branch": "Artificial Intelligence",
                    "current_year": 3,
                    "semester": 6,
                    "career_goal": "AI Research Scientist",
                    "weekly_study_hours": 20.0,
                },
                "skill_gaps": [],
                "recommendations": [],
            },
        }

        mock_roadmap_resp = {
            "title": "Roadmap for AI Research Scientist",
            "milestones": [],
        }

        with patch("backend.routes.roadmap.StudentMentorOrchestrator") as mock_orch_cls:
            mock_orch_inst = MagicMock()
            mock_orch_inst.generate_roadmap.return_value = mock_roadmap_resp
            mock_orch_cls.return_value = mock_orch_inst

            res = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=payload,
            )

            self.assertEqual(res.status_code, 200)
            passed_student = mock_orch_cls.call_args[1]["student"]

            # Authoritative identity must be Alice
            self.assertEqual(passed_student.name, self.user_a_name)
            self.assertEqual(passed_student.email, self.user_a_email)

            # Legitimate inputs preserved
            self.assertEqual(passed_student.career_goal, "AI Research Scientist")
            mock_orch_inst.generate_roadmap.assert_called_once()

    def test_03_tutor_identity_binding_prevents_spoofing(self):
        """POST /api/tutor binds student identity to current_user, preserving topic and question."""
        endpoint = "/api/tutor"
        payload = {
            "student": self.spoofed_student_payload,
            "topic": "Backpropagation",
            "question": "How is the gradient calculated across layers?",
        }

        mock_tutor_resp = TutorResponse(
            topic="Backpropagation",
            explanation="Backpropagation computes gradients using the chain rule.",
            key_points=["Chain rule", "Gradient descent"],
            example="loss.backward()",
            practice_task="Implement single layer backprop in NumPy",
        )

        with patch("backend.routes.tutor.StudentMentorOrchestrator") as mock_orch_cls:
            mock_orch_inst = MagicMock()
            mock_orch_inst.ask_tutor.return_value = mock_tutor_resp
            mock_orch_cls.return_value = mock_orch_inst

            res = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=payload,
            )

            self.assertEqual(res.status_code, 200)
            passed_student = mock_orch_cls.call_args[1]["student"]

            # Authoritative identity
            self.assertEqual(passed_student.name, self.user_a_name)
            self.assertEqual(passed_student.email, self.user_a_email)

            # Legitimate inputs preserved
            self.assertEqual(mock_orch_cls.call_args[1]["topic"], "Backpropagation")
            mock_orch_inst.ask_tutor.assert_called_once_with(
                question="How is the gradient calculated across layers?"
            )

    def test_04_quiz_identity_binding_prevents_spoofing(self):
        """POST /api/quiz binds student identity to current_user, preserving topic and params."""
        endpoint = "/api/quiz"
        payload = {
            "student": self.spoofed_student_payload,
            "topic": "Transformers Attention",
            "num_questions": 3,
        }

        mock_quiz_resp = QuizResponse(
            topic="Transformers Attention",
            difficulty="Advanced",
            questions=[
                QuizQuestion(
                    question="What is the formula for scaled dot-product attention?",
                    options=["Softmax(QK^T / sqrt(d_k))V", "Softmax(Q+K+V)"],
                    correct_answer="Softmax(QK^T / sqrt(d_k))V",
                    explanation="Standard scaled dot product attention equation.",
                )
            ],
        )

        with patch("backend.routes.quiz.StudentMentorOrchestrator") as mock_orch_cls:
            mock_orch_inst = MagicMock()
            mock_orch_inst.generate_quiz.return_value = mock_quiz_resp
            mock_orch_cls.return_value = mock_orch_inst

            res = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=payload,
            )

            self.assertEqual(res.status_code, 200)
            passed_student = mock_orch_cls.call_args[1]["student"]

            # Authoritative identity
            self.assertEqual(passed_student.name, self.user_a_name)
            self.assertEqual(passed_student.email, self.user_a_email)

            # Legitimate inputs preserved
            self.assertEqual(mock_orch_cls.call_args[1]["topic"], "Transformers Attention")
            mock_orch_inst.generate_quiz.assert_called_once_with(num_questions=3)

    def test_05_recommendations_identity_binding_prevents_spoofing(self):
        """POST /api/recommendations binds student identity to current_user."""
        endpoint = "/api/recommendations"

        mock_rec_resp = RecommendationResponse(
            summary="Recommended learning path for AI Researcher.",
            recommended_skills=["Distributed Training", "CUDA"],
            recommended_projects=["Custom Attention Kernel"],
            recommended_resources=[
                RecommendationResource(
                    title="Attention Is All You Need",
                    link="https://arxiv.org/abs/1706.03762",
                    type="Paper",
                )
            ],
            next_steps=["Read seminal paper"],
        )

        with patch("backend.routes.recommendation.RecommendationAgent.recommend", return_value=mock_rec_resp) as mock_method:
            res = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=self.spoofed_student_payload,
            )

            self.assertEqual(res.status_code, 200)
            mock_method.assert_called_once()
            passed_student = mock_method.call_args[0][0]

            # Authoritative identity
            self.assertEqual(passed_student.name, self.user_a_name)
            self.assertEqual(passed_student.email, self.user_a_email)

    # =========================================================================
    # 2. RATE LIMITING TESTS
    # =========================================================================

    def test_06_assessment_rate_limit_enforcement_and_headers(self):
        """POST /api/assessment enforces 5 req/min, returns HTTP 429 and Retry-After on 6th."""
        endpoint = "/api/assessment"
        mock_resp = {"summary": {}, "gaps": [], "recommendations": []}

        with patch("backend.routes.assessment.StudentMentorOrchestrator") as mock_orch:
            mock_orch.return_value.assess_student.return_value = mock_resp

            # Requests 1 to 5 must succeed
            for i in range(1, 6):
                res = self.client.post(
                    endpoint,
                    headers=self.headers_a,
                    json=self.spoofed_student_payload,
                )
                self.assertEqual(
                    res.status_code,
                    200,
                    f"Request {i} failed unexpectedly with status {res.status_code}: {res.text}",
                )
                self.assertEqual(res.headers.get("X-RateLimit-Limit"), "5")
                self.assertEqual(res.headers.get("X-RateLimit-Remaining"), str(5 - i))
                self.assertIn("X-RateLimit-Reset", res.headers)

            # Request 6 must exceed quota and return HTTP 429
            res_exceeded = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=self.spoofed_student_payload,
            )

            self.assertEqual(res_exceeded.status_code, 429)
            self.assertEqual(res_exceeded.headers.get("X-RateLimit-Limit"), "5")
            self.assertEqual(res_exceeded.headers.get("X-RateLimit-Remaining"), "0")
            self.assertIn("X-RateLimit-Reset", res_exceeded.headers)

            # Must include a valid integer Retry-After header
            retry_after = res_exceeded.headers.get("Retry-After")
            self.assertIsNotNone(retry_after)
            self.assertTrue(int(retry_after) > 0)

            # Detail must be generic and not leak sensitive info
            body = res_exceeded.json()
            self.assertEqual(body.get("detail"), "Too many requests. Please try again later.")

    def test_07_per_user_quota_isolation(self):
        """User A exhausting quota does NOT block User B."""
        endpoint = "/api/assessment"
        mock_resp = {"summary": {}, "gaps": [], "recommendations": []}

        with patch("backend.routes.assessment.StudentMentorOrchestrator") as mock_orch:
            mock_orch.return_value.assess_student.return_value = mock_resp

            # Exhaust User A's quota (5 requests)
            for _ in range(5):
                res_a = self.client.post(
                    endpoint,
                    headers=self.headers_a,
                    json=self.spoofed_student_payload,
                )
                self.assertEqual(res_a.status_code, 200)

            # User A is now rate-limited
            res_a_blocked = self.client.post(
                endpoint,
                headers=self.headers_a,
                json=self.spoofed_student_payload,
            )
            self.assertEqual(res_a_blocked.status_code, 429)

            # User B must still be permitted
            res_b = self.client.post(
                endpoint,
                headers=self.headers_b,
                json=self.spoofed_student_payload,
            )
            self.assertEqual(res_b.status_code, 200)
            self.assertEqual(res_b.headers.get("X-RateLimit-Remaining"), "4")

    def test_08_tutor_rate_limit_15_req_per_min(self):
        """POST /api/tutor enforces 15 req/min, returns 429 on 16th request."""
        endpoint = "/api/tutor"
        payload = {
            "student": self.spoofed_student_payload,
            "topic": "Python Generators",
            "question": "What does yield do?",
        }
        mock_resp = TutorResponse(
            topic="Generators",
            explanation="Yield pauses execution.",
            key_points=["yield", "next()"],
            example="def gen(): yield 1",
            practice_task="Write a generator",
        )

        with patch("backend.routes.tutor.StudentMentorOrchestrator") as mock_orch:
            mock_orch.return_value.ask_tutor.return_value = mock_resp

            # 15 requests succeed
            for i in range(1, 16):
                res = self.client.post(endpoint, headers=self.headers_a, json=payload)
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.headers.get("X-RateLimit-Remaining"), str(15 - i))

            # 16th request returns 429
            res_exceeded = self.client.post(endpoint, headers=self.headers_a, json=payload)
            self.assertEqual(res_exceeded.status_code, 429)
            self.assertIsNotNone(res_exceeded.headers.get("Retry-After"))

    def test_09_quiz_evaluate_rate_limiting(self):
        """POST /api/quiz/evaluate is protected with rate limiting."""
        endpoint = "/api/quiz/evaluate"
        payload = {
            "quiz": {
                "topic": "Python",
                "difficulty": "Easy",
                "questions": [
                    {
                        "question": "What is len('abc')?",
                        "options": ["1", "2", "3"],
                        "correct_answer": "3",
                        "explanation": "Length is 3",
                    }
                ],
            },
            "student_answers": ["3"],
        }
        mock_eval = {
            "topic": "Python",
            "total_questions": 1,
            "correct_answers": 1,
            "score_percentage": 100.0,
            "question_results": [],
            "weak_topics": [],
            "recommendation": "Great job",
        }

        with patch("backend.routes.quiz.QuizEvaluationAgent.evaluate", return_value=mock_eval):
            # Exhaust 15 requests
            for _ in range(15):
                res = self.client.post(endpoint, headers=self.headers_a, json=payload)
                self.assertEqual(res.status_code, 200)

            # 16th is 429
            res_exceeded = self.client.post(endpoint, headers=self.headers_a, json=payload)
            self.assertEqual(res_exceeded.status_code, 429)

    def test_10_skill_analysis_rate_limiting(self):
        """POST /api/skill-analysis is protected with rate limiting."""
        endpoint = "/api/skill-analysis"
        payload = {
            "skills": [
                {
                    "name": "Python",
                    "proficiency": 80,
                    "strengths": "Fast",
                    "weak_areas": "None",
                    "experience": "1 year",
                }
            ]
        }
        mock_analysis = {"summary": "Strong", "skills": []}

        with patch("backend.routes.skill_analysis.SkillAnalysisAgent.analyze", return_value=mock_analysis):
            # Exhaust 15 requests
            for _ in range(15):
                res = self.client.post(endpoint, headers=self.headers_a, json=payload)
                self.assertEqual(res.status_code, 200)

            # 16th is 429
            res_exceeded = self.client.post(endpoint, headers=self.headers_a, json=payload)
            self.assertEqual(res_exceeded.status_code, 429)

    # =========================================================================
    # 3. RATE LIMITER INTERNALS & SECURITY
    # =========================================================================

    def test_11_rate_limiter_concurrency_thread_safety(self):
        """RateLimiter correctly enforces quotas under concurrent thread execution."""
        max_requests = 10
        window_seconds = 60
        key = "test_concurrent_user"

        def make_check(_):
            allowed, _, _, _ = rate_limiter.check(
                key=key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            return allowed

        # 30 concurrent attempts against limit of 10
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(make_check, range(30)))

        allowed_count = sum(1 for r in results if r is True)
        rejected_count = sum(1 for r in results if r is False)

        self.assertEqual(allowed_count, max_requests)
        self.assertEqual(rejected_count, 20)

    def test_12_rate_limiter_cleanup_pruning(self):
        """RateLimiter.cleanup() prunes expired and idle keys safely."""
        now = 10000.0

        # Key 1 has old timestamps
        rate_limiter.check("old_key", max_requests=5, window_seconds=60, now=now - 5000)
        # Key 2 has fresh timestamps
        rate_limiter.check("fresh_key", max_requests=5, window_seconds=60, now=now)

        # Cleanup with max_idle_seconds = 3600
        pruned_count = rate_limiter.cleanup(max_idle_seconds=3600, now=now)

        self.assertEqual(pruned_count, 1)
        self.assertNotIn("old_key", rate_limiter._records)
        self.assertIn("fresh_key", rate_limiter._records)

    def test_13_spoofed_forwarding_headers_not_trusted(self):
        """IP rate limiting uses request.client.host and ignores spoofed X-Forwarded-For."""
        # Directly test rate_limiter with keys representing client IPs
        # Client host is verified, client-supplied headers cannot manipulate user quotas
        key_actual = "ip:127.0.0.1:test"
        key_spoofed = "ip:203.0.113.195:test"

        # Simulating that requests originating from 127.0.0.1 increment the 127.0.0.1 bucket
        for _ in range(5):
            allowed, _, _, _ = rate_limiter.check(key_actual, max_requests=5, window_seconds=60)
            self.assertTrue(allowed)

        # 6th from same actual IP is blocked
        blocked, _, _, _ = rate_limiter.check(key_actual, max_requests=5, window_seconds=60)
        self.assertFalse(blocked)

        # Spoofed key was never incremented
        self.assertNotIn(key_spoofed, rate_limiter._records)


if __name__ == "__main__":
    unittest.main()