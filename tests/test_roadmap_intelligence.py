"""Tests for Phase 3.4 Roadmap Intelligence & Milestone Mastery."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.session import SessionLocal, get_db
from backend.models.user import User
from backend.models.learning_activity import LearningActivity
from backend.auth.security import hash_password
from backend.auth.jwt_handler import create_access_token
from backend.services.progress_service import (
    calculate_roadmap_progress,
    calculate_milestone_mastery,
    calculate_student_progress,
)
from models.roadmap import LearningRoadmap, RoadmapStep


class TestRoadmapMasteryCorrelation(unittest.TestCase):
    """Unit tests for deterministic milestone-to-quiz correlation and mastery thresholds."""

    def setUp(self):
        self.raw_steps = [
            {
                "milestone": "Python Fundamentals",
                "completed": False,
                "skills": ["Variables", "Loops", "Functions"],
                "estimated_hours": 10.0,
            },
            {
                "milestone": "Data Structures in Python",
                "completed": True,
                "skills": ["Lists", "Dictionaries", "Trees"],
                "estimated_hours": 15.0,
            },
            {
                "milestone": "Deep Learning with PyTorch",
                "completed": True,
                "skills": ["PyTorch", "Backpropagation", "Tensors"],
                "estimated_hours": 20.0,
            },
            {
                "milestone": "Full Stack Deployment",
                "completed": False,
                "skills": ["Docker", "FastAPI", "Variables"],  # Note: 'Variables' shared with Step 1 (ambiguous)
                "estimated_hours": 12.0,
            },
        ]

    def test_01_mastery_threshold_mastered_gte_70(self):
        """Milestone with quiz score >= 70% is MASTERED."""
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Fundamentals",
            score=85.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals", "evaluation": {"score": 85.0}},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.title, "Python Fundamentals")
        self.assertEqual(m0.mastery_status, "MASTERED")
        self.assertEqual(m0.latest_score, 85.0)
        self.assertEqual(m0.highest_score, 85.0)
        self.assertEqual(m0.attempt_count, 1)
        self.assertEqual(m0.evidence_source, "quiz")
        self.assertIsNone(m0.review_warning)

    def test_02_mastery_threshold_in_progress_60_to_69(self):
        """Milestone with latest quiz score 60-69% is IN_PROGRESS."""
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz on Python Fundamentals",
            score=65.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.mastery_status, "IN_PROGRESS")
        self.assertEqual(m0.latest_score, 65.0)

    def test_03_mastery_threshold_needs_review_lt_60(self):
        """Milestone with latest quiz score < 60% is NEEDS_REVIEW."""
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Fundamentals",
            score=52.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.mastery_status, "NEEDS_REVIEW")
        self.assertEqual(m0.latest_score, 52.0)
        # Not completed yet, so no completed review warning
        self.assertIsNone(m0.review_warning)

    def test_04_weak_topic_signal_triggers_needs_review_even_with_high_score(self):
        """Verified weak-topic signal forces NEEDS_REVIEW status."""
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Fundamentals",
            score=75.0,  # Score looks fine, but evaluation explicitly flagged weak area
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={
                "topic": "Python Fundamentals",
                "evaluation": {
                    "score": 75.0,
                    "weak_topics": ["Python Fundamentals"],
                },
            },
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=["Python Fundamentals"],
        )
        m0 = milestones[0]
        self.assertEqual(m0.mastery_status, "NEEDS_REVIEW")

    def test_05_multiple_quiz_attempts_tracks_latest_and_highest(self):
        """Multiple quiz attempts accurately report latest score, highest score, and attempt count."""
        q1 = LearningActivity(
            activity_type="quiz",
            title="Quiz 1",
            score=50.0,
            created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        q2 = LearningActivity(
            activity_type="quiz",
            title="Quiz 2",
            score=90.0,
            created_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        q3 = LearningActivity(
            activity_type="quiz",
            title="Quiz 3",
            score=80.0,
            created_at=datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[q1, q2, q3],
            tutor_activities=[],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.attempt_count, 3)
        self.assertEqual(m0.latest_score, 80.0)
        self.assertEqual(m0.highest_score, 90.0)
        self.assertEqual(m0.mastery_status, "MASTERED")

    def test_06_no_quiz_data_defaults_to_not_started(self):
        """Milestone with no activity defaults to NOT_STARTED with zero attempts."""
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[],
            tutor_activities=[],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.mastery_status, "NOT_STARTED")
        self.assertEqual(m0.attempt_count, 0)
        self.assertIsNone(m0.latest_score)
        self.assertIsNone(m0.highest_score)
        self.assertEqual(m0.evidence_source, "none")

    def test_07_tutor_activity_supports_in_progress_when_no_quiz(self):
        """Tutor engagement marks milestone as IN_PROGRESS with tutor evidence source."""
        tutor_act = LearningActivity(
            activity_type="tutor",
            title="AI Tutor: Python Fundamentals",
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Python Fundamentals"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[],
            tutor_activities=[tutor_act],
            weak_topics=[],
        )
        m0 = milestones[0]
        self.assertEqual(m0.mastery_status, "IN_PROGRESS")
        self.assertEqual(m0.evidence_source, "tutor")
        self.assertEqual(m0.attempt_count, 0)

    def test_08_unique_skill_match_correlates_to_milestone(self):
        """Quiz topic matching a unique skill correlates reliably to that milestone."""
        # 'Lists' is only in Milestone 1 (Data Structures in Python)
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Lists",
            score=78.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Lists"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        m1 = milestones[1]
        self.assertEqual(m1.title, "Data Structures in Python")
        self.assertEqual(m1.mastery_status, "MASTERED")
        self.assertEqual(m1.latest_score, 78.0)

    def test_09_ambiguous_skill_is_not_matched_without_title(self):
        """Skill present in multiple milestones ('Variables') is not matched to prevent false attribution."""
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Variables",
            score=95.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Variables"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        # Neither Milestone 0 nor Milestone 3 should invent a score from ambiguous 'Variables'
        self.assertEqual(milestones[0].attempt_count, 0)
        self.assertEqual(milestones[0].mastery_status, "NOT_STARTED")
        self.assertEqual(milestones[3].attempt_count, 0)
        self.assertEqual(milestones[3].mastery_status, "NOT_STARTED")

    def test_10_advisory_completion_warning_when_weak_performance(self):
        """Completed milestone with score < 60% displays advisory review warning."""
        # Milestone 2 (Deep Learning with PyTorch) is completed=True
        quiz_act = LearningActivity(
            activity_type="quiz",
            title="Quiz: Deep Learning with PyTorch",
            score=45.0,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            data={"topic": "Deep Learning with PyTorch"},
        )
        milestones = calculate_milestone_mastery(
            raw_steps=self.raw_steps,
            quiz_activities=[quiz_act],
            tutor_activities=[],
            weak_topics=[],
        )
        m2 = milestones[2]
        self.assertTrue(m2.completed)
        self.assertEqual(m2.mastery_status, "NEEDS_REVIEW")
        self.assertIsNotNone(m2.review_warning)
        self.assertIn("review is recommended", m2.review_warning)
        self.assertIn("45%", m2.review_warning)


class TestAdaptiveRoadmapProgressIntegration(unittest.TestCase):
    """Integration tests for progress service adaptive recommendations and focus milestone."""

    def test_11_adaptive_recommendation_prioritizes_completed_milestone_needing_review(self):
        """Completed milestone with NEEDS_REVIEW generates Priority 1 milestone_review recommendation."""
        activities = [
            LearningActivity(
                activity_type="roadmap",
                title="AI Career Roadmap",
                score=50.0,
                created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
                data={
                    "steps": [
                        {
                            "milestone": "Neural Network Basics",
                            "completed": True,
                            "skills": ["Perceptron", "Backpropagation"],
                        },
                        {
                            "milestone": "Computer Vision",
                            "completed": False,
                            "skills": ["CNN", "ResNet"],
                        },
                    ]
                },
            ),
            LearningActivity(
                activity_type="quiz",
                title="Quiz: Neural Network Basics",
                score=42.0,
                created_at=datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc),
                data={"topic": "Neural Network Basics"},
            ),
        ]
        result = calculate_student_progress(activities)
        self.assertIsNotNone(result.roadmap_progress)
        self.assertEqual(result.roadmap_progress.recommended_focus_milestone, "Neural Network Basics")

        # Verify priority 1 action
        rec_types = [a.action_type for a in result.recommended_actions]
        self.assertIn("milestone_review", rec_types)
        review_rec = next(a for a in result.recommended_actions if a.action_type == "milestone_review")
        self.assertEqual(review_rec.priority, 1)
        self.assertEqual(review_rec.context["milestone"], "Neural Network Basics")


class TestRoadmapApiAndCrossUserIsolation(unittest.TestCase):
    """API endpoint tests for roadmap fallback and cross-user isolation."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Create two test users
        cls.user_a = User(
            email="roadmap_alice@example.com",
            hashed_password=hash_password("ValidPass123!"),
            full_name="Alice Roadmap",
        )
        cls.user_b = User(
            email="roadmap_bob@example.com",
            hashed_password=hash_password("ValidPass123!"),
            full_name="Bob Roadmap",
        )
        cls.db.add_all([cls.user_a, cls.user_b])
        cls.db.commit()
        cls.db.refresh(cls.user_a)
        cls.db.refresh(cls.user_b)

        cls.token_a = create_access_token(data={"sub": cls.user_a.email})
        cls.token_b = create_access_token(data={"sub": cls.user_b.email})
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(LearningActivity).filter(
                LearningActivity.user_id.in_([cls.user_a.id, cls.user_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(User).filter(
                User.id.in_([cls.user_a.id, cls.user_b.id])
            ).delete(synchronize_session=False)
            cls.db.commit()
        finally:
            cls.db.close()

    @patch("orchestrator.RoadmapAgent.create")
    def test_12_roadmap_generation_resolves_db_assessment_when_payload_assessment_none(self, mock_create):
        """When localStorage is empty (request sends assessment=None), endpoint resolves assessment from DB."""
        mock_create.return_value = LearningRoadmap(
            title="Data Science Roadmap",
            target_role="Data Scientist",
            steps=[
                RoadmapStep(
                    title="Pandas and NumPy",
                    description="Data analysis basics",
                    skills=["Pandas", "NumPy"],
                    estimated_hours=10.0,
                    completed=False,
                )
            ],
        )

        # Alice has an assessment in learning history
        assessment_act = LearningActivity(
            user_id=self.user_a.id,
            activity_type="assessment",
            title="Initial Assessment",
            data={
                "summary": {
                    "student_name": "Alice Roadmap",
                    "degree": "B.Tech",
                    "branch": "CSE",
                    "current_year": 3,
                    "semester": 6,
                    "career_goal": "Data Scientist",
                    "weekly_study_hours": 15,
                },
                "skill_gaps": [
                    {
                        "skill_name": "Pandas",
                        "priority": "high",
                        "current_level": "20",
                        "target_level": "80",
                        "gap": 60,
                        "task": "Master Pandas dataframe operations",
                        "timeline": "2 weeks",
                    }
                ],
                "recommendations": [],
            },
        )
        self.db.add(assessment_act)
        self.db.commit()

        # Alice calls /api/roadmap with assessment: None (simulating cleared localStorage)
        payload = {
            "student": {
                "name": "Ignored Name",
                "email": "ignored@example.com",
                "degree": "B.Tech",
                "branch": "CSE",
                "current_year": 3,
                "semester": 6,
                "career_goal": "Data Scientist",
                "interests": ["Data"],
                "weekly_hours": 15,
                "skills": [],
            },
            "assessment": None,
        }

        res = self.client.post("/api/roadmap", json=payload, headers=self.headers_a)
        self.assertEqual(res.status_code, 200, res.text)
        mock_create.assert_called_once()
        # Verify passed student identity was bound to Alice
        passed_student = mock_create.call_args.kwargs.get("student") or mock_create.call_args[0][0]
        self.assertEqual(passed_student.name, "Alice Roadmap")
        self.assertEqual(passed_student.email, "roadmap_alice@example.com")
        # Verify assessment was resolved from Alice's history in DB
        passed_assessment = mock_create.call_args.kwargs.get("assessment") or mock_create.call_args[0][1]
        self.assertIsNotNone(passed_assessment)
        self.assertEqual(passed_assessment.summary.student_name, "Alice Roadmap")
    def test_13_cross_user_mastery_isolation(self):
        """Alice's quiz attempts and roadmap mastery must not leak into Bob's progress."""
        # Alice creates roadmap and quiz
        act_road_a = LearningActivity(
            user_id=self.user_a.id,
            activity_type="roadmap",
            title="Alice ML Roadmap",
            score=100.0,
            data={
                "steps": [
                    {"milestone": "ML Algorithms", "completed": True, "skills": ["Linear Regression"]}
                ]
            },
        )
        act_quiz_a = LearningActivity(
            user_id=self.user_a.id,
            activity_type="quiz",
            title="Quiz: ML Algorithms",
            score=98.0,
            data={"topic": "ML Algorithms"},
        )
        # Bob creates the same roadmap title but has NO quizzes
        act_road_b = LearningActivity(
            user_id=self.user_b.id,
            activity_type="roadmap",
            title="Bob ML Roadmap",
            score=0.0,
            data={
                "steps": [
                    {"milestone": "ML Algorithms", "completed": False, "skills": ["Linear Regression"]}
                ]
            },
        )
        self.db.add_all([act_road_a, act_quiz_a, act_road_b])
        self.db.commit()

        # Alice's progress shows MASTERED 98%
        res_a = self.client.get("/api/progress", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        m_a = data_a["roadmap_progress"]["milestones"][0]
        self.assertEqual(m_a["mastery_status"], "MASTERED")
        self.assertEqual(m_a["latest_score"], 98.0)

        # Bob's progress must be NOT_STARTED with zero attempts
        res_b = self.client.get("/api/progress", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        m_b = data_b["roadmap_progress"]["milestones"][0]
        self.assertEqual(m_b["mastery_status"], "NOT_STARTED")
        self.assertIsNone(m_b["latest_score"])
        self.assertEqual(m_b["attempt_count"], 0)


if __name__ == "__main__":
    unittest.main()
