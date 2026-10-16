import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.learning_activity import LearningActivity
from backend.services.progress_service import calculate_student_progress


class TestStudentProgressIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.email_a = "progress_alice@campuscompass.org"
        cls.email_b = "progress_bob@campuscompass.org"
        cls.password = "ValidPassword123!"

        cls._cleanup_users()

        # Register Alice
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Alice Progress",
                "email": cls.email_a,
                "password": cls.password,
            },
        )
        assert res_a.status_code == 201, f"Alice reg failed: {res_a.text}"

        # Register Bob
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Bob Isolation",
                "email": cls.email_b,
                "password": cls.password,
            },
        )
        assert res_b.status_code == 201, f"Bob reg failed: {res_b.text}"

        # Login Alice
        login_a = cls.client.post(
            "/auth/login",
            data={"username": cls.email_a, "password": cls.password},
        )
        assert login_a.status_code == 200, f"Alice login failed: {login_a.text}"
        cls.token_a = login_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Login Bob
        login_b = cls.client.post(
            "/auth/login",
            data={"username": cls.email_b, "password": cls.password},
        )
        assert login_b.status_code == 200, f"Bob login failed: {login_b.text}"
        cls.token_b = login_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        # Fetch user IDs
        db = SessionLocal()
        try:
            cls.user_a_id = db.query(User).filter(User.email == cls.email_a).first().id
            cls.user_b_id = db.query(User).filter(User.email == cls.email_b).first().id
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_users()

    @classmethod
    def _cleanup_users(cls):
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.email.in_([cls.email_a, cls.email_b])).all()
            for u in users:
                db.query(LearningActivity).filter(LearningActivity.user_id == u.id).delete()
                db.delete(u)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def setUp(self):
        # Clear activities between individual tests
        db = SessionLocal()
        try:
            db.query(LearningActivity).filter(
                LearningActivity.user_id.in_([self.user_a_id, self.user_b_id])
            ).delete()
            db.commit()
        finally:
            db.close()

    # ---------------------------------------------------------
    # 1. Pure Unit Tests on calculate_student_progress
    # ---------------------------------------------------------
    def test_empty_activities_returns_safe_baseline(self):
        result = calculate_student_progress([])
        self.assertFalse(result.has_history)
        self.assertEqual(result.total_activities, 0)
        self.assertEqual(result.quiz_analytics.total_attempts, 0)
        self.assertIsNone(result.quiz_analytics.average_score)
        self.assertIsNone(result.quiz_analytics.score_delta)
        self.assertEqual(result.quiz_analytics.trend, "insufficient_data")
        self.assertIsNone(result.roadmap_progress)
        self.assertEqual(result.weak_topics, [])
        self.assertEqual(result.improving_topics, [])
        # Recommendations should guide student to start
        rec_types = [r.action_type for r in result.recommended_actions]
        self.assertIn("diagnostic_quiz", rec_types)
        self.assertIn("initial_assessment", rec_types)

    def test_single_quiz_attempt_does_not_fabricate_improvement(self):
        # When only 1 quiz exists, trend MUST be 'insufficient_data' and score_delta MUST be None
        db = SessionLocal()
        try:
            act = LearningActivity(
                user_id=self.user_a_id,
                activity_type="quiz",
                title="Python Basics",
                score=85.0,
                data={"topic": "Python", "evaluation": {"score": 85.0}},
            )
            db.add(act)
            db.commit()
            db.refresh(act)
            activities = [act]
            result = calculate_student_progress(activities)

            self.assertTrue(result.has_history)
            self.assertEqual(result.quiz_analytics.total_attempts, 1)
            self.assertEqual(result.quiz_analytics.average_score, 85.0)
            self.assertIsNone(result.quiz_analytics.score_delta)
            self.assertEqual(result.quiz_analytics.trend, "insufficient_data")
        finally:
            db.close()

    def test_quiz_score_trend_improving(self):
        # 3 quizzes: 40 -> 60 -> 80
        activities = [
            LearningActivity(
                activity_type="quiz",
                title="Q1",
                score=40.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Recursion"},
            ),
            LearningActivity(
                activity_type="quiz",
                title="Q2",
                score=60.0,
                created_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Recursion"},
            ),
            LearningActivity(
                activity_type="quiz",
                title="Q3",
                score=80.0,
                created_at=datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Recursion"},
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertEqual(result.quiz_analytics.total_attempts, 3)
        self.assertEqual(result.quiz_analytics.average_score, 60.0)
        self.assertEqual(result.quiz_analytics.recent_score, 80.0)
        self.assertEqual(result.quiz_analytics.score_delta, 40.0)
        self.assertEqual(result.quiz_analytics.trend, "improving")
        self.assertIn("Recursion", result.improving_topics)

    def test_quiz_score_trend_declining(self):
        # 2 quizzes: 90 -> 50
        activities = [
            LearningActivity(
                activity_type="quiz",
                title="Q1",
                score=90.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Dynamic Programming"},
            ),
            LearningActivity(
                activity_type="quiz",
                title="Q2",
                score=50.0,
                created_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Dynamic Programming"},
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertEqual(result.quiz_analytics.total_attempts, 2)
        self.assertEqual(result.quiz_analytics.score_delta, -40.0)
        self.assertEqual(result.quiz_analytics.trend, "declining")
        self.assertIn("Dynamic Programming", result.weak_topics)

    def test_quiz_score_trend_steady(self):
        # 2 quizzes: 75 -> 77 (delta within [-2, +2])
        activities = [
            LearningActivity(
                activity_type="quiz",
                title="Q1",
                score=75.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Trees"},
            ),
            LearningActivity(
                activity_type="quiz",
                title="Q2",
                score=77.0,
                created_at=datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc),
                data={"topic": "Trees"},
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertEqual(result.quiz_analytics.score_delta, 2.0)
        self.assertEqual(result.quiz_analytics.trend, "steady")

    def test_weak_topics_from_evaluation_payload(self):
        # Quiz evaluation payload has explicit weak_topics
        activities = [
            LearningActivity(
                activity_type="quiz",
                title="Quiz on Algorithms",
                score=55.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={
                    "topic": "Algorithms",
                    "evaluation": {
                        "score": 55.0,
                        "weak_topics": ["Graph Traversal", "Backtracking"],
                    },
                },
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertIn("Graph Traversal", result.weak_topics)
        self.assertIn("Backtracking", result.weak_topics)
        # Recommendation should be revision for weak topic
        rec_types = [r.action_type for r in result.recommended_actions]
        self.assertIn("targeted_revision", rec_types)

    def test_roadmap_milestones_completion_tracking(self):
        activities = [
            LearningActivity(
                activity_type="roadmap",
                title="Full Stack Career Roadmap",
                score=33.3,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={
                    "title": "Full Stack Career Roadmap",
                    "steps": [
                        {"milestone": "HTML/CSS Foundations", "completed": True},
                        {"milestone": "JavaScript Deep Dive", "completed": False},
                        {"milestone": "Backend APIs with FastAPI", "completed": False},
                    ],
                },
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertIsNotNone(result.roadmap_progress)
        self.assertTrue(result.roadmap_progress.has_roadmap)
        self.assertEqual(result.roadmap_progress.total_milestones, 3)
        self.assertEqual(result.roadmap_progress.completed_milestones, 1)
        self.assertAlmostEqual(result.roadmap_progress.completion_percentage, 33.3, places=1)
        self.assertEqual(result.roadmap_progress.next_milestone, "JavaScript Deep Dive")

    def test_roadmap_all_milestones_completed(self):
        activities = [
            LearningActivity(
                activity_type="roadmap",
                title="Completed Roadmap",
                score=100.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={
                    "steps": [
                        {"milestone": "Step 1", "completed": True},
                        {"milestone": "Step 2", "completed": True},
                    ],
                },
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertEqual(result.roadmap_progress.completed_milestones, 2)
        self.assertIsNone(result.roadmap_progress.next_milestone)
        self.assertEqual(result.roadmap_progress.completion_percentage, 100.0)

    def test_malformed_and_incomplete_records_handled_gracefully(self):
        # Corrupted entries: score is None, data is not a dict, data missing steps/topics
        activities = [
            LearningActivity(
                activity_type="quiz",
                title="Corrupt Quiz 1",
                score=None,
                data=None,
            ),
            LearningActivity(
                activity_type="roadmap",
                title="Corrupt Roadmap 1",
                score="invalid_score",
                data={"steps": "not_a_list"},
            ),
            LearningActivity(
                activity_type="assessment",
                title="Corrupt Assessment",
                score=None,
                data={"skill_gaps": [{"skill": None}]},
            ),
        ]
        # Should execute completely without throwing exception
        result = calculate_student_progress(activities)
        self.assertTrue(result.has_history)
        self.assertEqual(result.quiz_analytics.total_attempts, 1)
        self.assertIsNone(result.quiz_analytics.average_score)
        self.assertIsNotNone(result.roadmap_progress)
        self.assertEqual(result.roadmap_progress.total_milestones, 0)

    # ---------------------------------------------------------
    # 2. Endpoint Tests & Cross-User Security Isolation
    # ---------------------------------------------------------
    def test_unauthenticated_request_rejected(self):
        res = self.client.get("/api/progress")
        self.assertEqual(res.status_code, 401)

    def test_cross_user_isolation(self):
        # Alice creates 2 activities: a quiz and a roadmap
        db = SessionLocal()
        try:
            act1 = LearningActivity(
                user_id=self.user_a_id,
                activity_type="quiz",
                title="Alice Quiz on Trees",
                score=95.0,
                data={"topic": "Binary Trees", "evaluation": {"score": 95.0}},
            )
            act2 = LearningActivity(
                user_id=self.user_a_id,
                activity_type="roadmap",
                title="Alice Secret Roadmap",
                score=50.0,
                data={"steps": [{"milestone": "Alice Step 1", "completed": True}]},
            )
            db.add_all([act1, act2])
            db.commit()
        finally:
            db.close()

        # Alice fetches her progress
        res_a = self.client.get("/api/progress", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertTrue(data_a["has_history"])
        self.assertEqual(data_a["total_activities"], 2)
        self.assertEqual(data_a["quiz_analytics"]["total_attempts"], 1)
        self.assertEqual(data_a["quiz_analytics"]["average_score"], 95.0)
        self.assertIsNotNone(data_a["roadmap_progress"])
        self.assertEqual(data_a["roadmap_progress"]["title"], "Alice Secret Roadmap")

        # Bob fetches his progress -> MUST have ZERO activities and ZERO leakage from Alice
        res_b = self.client.get("/api/progress", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        self.assertFalse(data_b["has_history"])
        self.assertEqual(data_b["total_activities"], 0)
        self.assertEqual(data_b["quiz_analytics"]["total_attempts"], 0)
        self.assertIsNone(data_b["quiz_analytics"]["average_score"])
        self.assertIsNone(data_b["roadmap_progress"])
        self.assertEqual(data_b["recent_activities"], [])
        self.assertEqual(data_b["weak_topics"], [])
        self.assertEqual(data_b["improving_topics"], [])

    def test_api_schema_and_deterministic_recommendations(self):
        # Alice takes a quiz with low score and weak topic
        db = SessionLocal()
        try:
            act = LearningActivity(
                user_id=self.user_a_id,
                activity_type="quiz",
                title="Distributed Systems Quiz",
                score=50.0,
                data={
                    "topic": "Distributed Systems",
                    "evaluation": {
                        "score": 50.0,
                        "weak_topics": ["Raft Consensus"],
                    },
                },
            )
            db.add(act)
            db.commit()
        finally:
            db.close()

        res = self.client.get("/api/progress", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Check required schema fields
        self.assertIn("has_history", data)
        self.assertIn("total_activities", data)
        self.assertIn("quiz_analytics", data)
        self.assertIn("weak_topics", data)
        self.assertIn("improving_topics", data)
        self.assertIn("skill_gaps", data)
        self.assertIn("recommended_actions", data)
        self.assertIn("recent_activities", data)

        # Check that weak topic was identified
        self.assertIn("Raft Consensus", data["weak_topics"])

        # Check recommendations
        recs = data["recommended_actions"]
        self.assertGreater(len(recs), 0)
        self.assertLessEqual(len(recs), 3)
        rec_types = [r["action_type"] for r in recs]
        self.assertIn("targeted_revision", rec_types)
        revision_rec = next(r for r in recs if r["action_type"] == "targeted_revision")
        self.assertEqual(revision_rec["target_route"], "/tutor")
        self.assertIn(revision_rec["context"]["topic"], ["Distributed Systems", "Raft Consensus"])


if __name__ == "__main__":
    unittest.main()
