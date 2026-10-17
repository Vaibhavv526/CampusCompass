"""Phase 3.5 End-to-End Regression Tests for Student Journey Reliability.

Tests cover:
1. Assessment fallback and history retrieval.
2. Milestone quiz attribution and deterministic mastery status transitions.
3. Advisory warnings on completed milestones without blocking completion.
4. Tutor activity attribution with milestone context.
5. Cross-user isolation for activities, assessments, and progress intelligence.
6. Backward compatibility for legacy activities without milestone context.
"""

import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.learning_activity import LearningActivity
from backend.services.progress_service import (
    calculate_milestone_mastery,
    calculate_roadmap_progress,
    calculate_student_progress,
    extract_skill_gaps,
)


class TestJourneyReliabilityPhase35(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.user_a_email = "phase35_usera@campuscompass.org"
        cls.user_b_email = "phase35_userb@campuscompass.org"
        cls.password = "ValidPassword123!"

        cls._cleanup()

        # Register User A
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Student Alpha",
                "email": cls.user_a_email,
                "password": cls.password,
            },
        )
        assert res_a.status_code == 201, f"User A registration failed: {res_a.text}"

        # Login User A
        login_a = cls.client.post(
            "/auth/login",
            data={"username": cls.user_a_email, "password": cls.password},
        )
        assert login_a.status_code == 200, f"User A login failed: {login_a.text}"
        cls.token_a = login_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Register User B
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Student Beta",
                "email": cls.user_b_email,
                "password": cls.password,
            },
        )
        assert res_b.status_code == 201, f"User B registration failed: {res_b.text}"

        # Login User B
        login_b = cls.client.post(
            "/auth/login",
            data={"username": cls.user_b_email, "password": cls.password},
        )
        assert login_b.status_code == 200, f"User B login failed: {login_b.text}"
        cls.token_b = login_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.db.close()

    @classmethod
    def _cleanup(cls):
        for email in [cls.user_a_email, cls.user_b_email]:
            user = cls.db.query(User).filter(User.email == email).first()
            if user:
                cls.db.query(LearningActivity).filter(LearningActivity.user_id == user.id).delete()
                cls.db.delete(user)
        cls.db.commit()

    def test_01_assessment_fallback_and_history_retrieval(self):
        """Assessment saved in learning history can be retrieved for fallback restoration."""
        assessment_payload = {
            "career_goal": "Cloud Architect",
            "skill_gaps": [
                {
                    "skill_name": "Kubernetes",
                    "current_level": 40,
                    "target_level": 90,
                    "gap": 50,
                    "priority": "High",
                    "task": "Deploy multi-node clusters",
                    "timeline": "3 weeks",
                },
                {
                    "skill_name": "Terraform",
                    "current_level": 60,
                    "target_level": 85,
                    "gap": 25,
                    "priority": "Medium",
                    "task": "Automate AWS infrastructure",
                    "timeline": "2 weeks",
                },
            ],
            "recommendations": [
                {
                    "task": "Study CKAD course",
                    "goal": "Kubernetes Certification",
                    "timeline": "1 month",
                }
            ],
        }

        # User A saves an assessment activity
        create_res = self.client.post(
            "/api/learning-history",
            headers=self.headers_a,
            json={
                "activity_type": "assessment",
                "title": "Skill Gap Assessment (Cloud Architect)",
                "summary": "2 skills analyzed, 1 high-priority gap(s)",
                "score": None,
                "data": assessment_payload,
            },
        )
        self.assertEqual(create_res.status_code, 201)

        # Retrieve assessment from history via filter
        get_res = self.client.get(
            "/api/learning-history?activity_type=assessment&limit=1",
            headers=self.headers_a,
        )
        self.assertEqual(get_res.status_code, 200)
        items = get_res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["data"]["career_goal"], "Cloud Architect")
        self.assertEqual(len(items[0]["data"]["skill_gaps"]), 2)

        # Service-level gap extraction
        activity_obj = LearningActivity(
            activity_type="assessment",
            title="Skill Gap Assessment (Cloud Architect)",
            data=assessment_payload,
        )
        gaps = extract_skill_gaps([activity_obj])
        self.assertEqual(len(gaps), 2)
        self.assertEqual(gaps[0].skill_name, "Kubernetes")
        self.assertEqual(gaps[0].priority.lower(), "high")

    def test_02_milestone_quiz_attribution_and_mastery_updates(self):
        """Quiz activities with milestone context properly attribute and update mastery."""
        raw_steps = [
            {
                "milestone": "Python Core & OOP",
                "completed": False,
                "skills": ["Classes", "Inheritance", "Decorators"],
                "estimated_hours": 12.0,
            },
            {
                "milestone": "Relational Databases & SQL",
                "completed": False,
                "skills": ["PostgreSQL", "Queries", "Indexing"],
                "estimated_hours": 14.0,
            },
        ]

        # Initially NOT_STARTED
        m_initial = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[],
            tutor_activities=[],
            weak_topics=[],
        )
        self.assertEqual(m_initial[0].mastery_status, "NOT_STARTED")
        self.assertEqual(m_initial[0].attempt_count, 0)

        # Quiz 1: Explicit milestone attribution with score 80% (MASTERED)
        quiz_1 = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Core & OOP",
            score=80.0,
            created_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
            data={
                "topic": "Python Core & OOP",
                "milestone": "Python Core & OOP",
                "evaluation": {"score": 80.0, "weak_topics": []},
            },
        )

        m_after_q1 = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[quiz_1],
            tutor_activities=[],
            weak_topics=[],
        )
        self.assertEqual(m_after_q1[0].mastery_status, "MASTERED")
        self.assertEqual(m_after_q1[0].latest_score, 80.0)
        self.assertEqual(m_after_q1[0].highest_score, 80.0)
        self.assertEqual(m_after_q1[0].attempt_count, 1)
        self.assertEqual(m_after_q1[0].evidence_source, "quiz")

        # Quiz 2: Subsequent retake score 65% (IN_PROGRESS)
        quiz_2 = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Core & OOP",
            score=65.0,
            created_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
            data={
                "topic": "Python Core & OOP",
                "milestone": "Python Core & OOP",
                "evaluation": {"score": 65.0, "weak_topics": []},
            },
        )

        m_after_q2 = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[quiz_1, quiz_2],
            tutor_activities=[],
            weak_topics=[],
        )
        self.assertEqual(m_after_q2[0].mastery_status, "IN_PROGRESS")
        self.assertEqual(m_after_q2[0].latest_score, 65.0)
        self.assertEqual(m_after_q2[0].highest_score, 80.0)
        self.assertEqual(m_after_q2[0].attempt_count, 2)

        # Quiz 3: Score drops below 60% -> NEEDS_REVIEW
        quiz_3 = LearningActivity(
            activity_type="quiz",
            title="Quiz: Python Core & OOP",
            score=50.0,
            created_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
            data={
                "topic": "Python Core & OOP",
                "milestone": "Python Core & OOP",
                "evaluation": {"score": 50.0, "weak_topics": ["Decorators"]},
            },
        )

        m_after_q3 = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[quiz_1, quiz_2, quiz_3],
            tutor_activities=[],
            weak_topics=["Decorators"],
        )
        self.assertEqual(m_after_q3[0].mastery_status, "NEEDS_REVIEW")
        self.assertEqual(m_after_q3[0].latest_score, 50.0)
        self.assertEqual(m_after_q3[0].attempt_count, 3)

    def test_03_advisory_review_warning_does_not_block_completion(self):
        """Milestone marked completed with quiz score < 60% shows advisory warning without blocking completion."""
        raw_steps = [
            {
                "milestone": "Relational Databases & SQL",
                "completed": True,  # Student marked complete
                "skills": ["PostgreSQL", "Queries"],
                "estimated_hours": 14.0,
            }
        ]

        quiz_low = LearningActivity(
            activity_type="quiz",
            title="Quiz: Relational Databases & SQL",
            score=45.0,
            created_at=datetime(2026, 10, 15, tzinfo=timezone.utc),
            data={
                "topic": "Relational Databases & SQL",
                "milestone": "Relational Databases & SQL",
                "evaluation": {"score": 45.0, "weak_topics": ["Queries"]},
            },
        )

        m_res = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[quiz_low],
            tutor_activities=[],
            weak_topics=["Queries"],
        )

        self.assertEqual(len(m_res), 1)
        # Crucial: completion status remains True (student choice respected)
        self.assertTrue(m_res[0].completed)
        self.assertEqual(m_res[0].mastery_status, "NEEDS_REVIEW")
        self.assertIsNotNone(m_res[0].review_warning)
        self.assertIn("Milestone is marked completed", m_res[0].review_warning)
        self.assertIn("45%", m_res[0].review_warning)

        # Verify roadmap progress includes warning and recommendations
        roadmap_act = LearningActivity(
            activity_type="roadmap",
            title="Backend Engineering Roadmap",
            data={"title": "Backend Engineering Roadmap", "steps": raw_steps},
        )
        prog = calculate_roadmap_progress(
            roadmap_activities=[roadmap_act],
            quiz_activities=[quiz_low],
            tutor_activities=[],
            weak_topics=["Queries"],
        )
        self.assertIsNotNone(prog)
        self.assertEqual(prog.completed_milestones, 1)
        self.assertEqual(prog.recommended_focus_milestone, "Relational Databases & SQL")

    def test_04_tutor_activity_attribution_sets_in_progress(self):
        """Tutor interaction with milestone context establishes IN_PROGRESS evidence."""
        raw_steps = [
            {
                "milestone": "System Architecture & Microservices",
                "completed": False,
                "skills": ["gRPC", "Kafka", "Service Discovery"],
                "estimated_hours": 20.0,
            }
        ]

        # Tutor activity with milestone
        tutor_act = LearningActivity(
            activity_type="tutor",
            title="AI Tutor: System Architecture & Microservices",
            created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
            data={
                "topic": "System Architecture & Microservices",
                "milestone": "System Architecture & Microservices",
                "question": "How does Kafka ensure partition ordering?",
            },
        )

        m_res = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[],
            tutor_activities=[tutor_act],
            weak_topics=[],
        )

        self.assertEqual(len(m_res), 1)
        self.assertEqual(m_res[0].mastery_status, "IN_PROGRESS")
        self.assertEqual(m_res[0].evidence_source, "tutor")
        self.assertEqual(m_res[0].attempt_count, 0)
        self.assertIsNone(m_res[0].latest_score)

    def test_05_cross_user_isolation(self):
        """User A data is isolated and completely invisible to User B."""
        # User A saves quiz activity
        res_a_quiz = self.client.post(
            "/api/learning-history",
            headers=self.headers_a,
            json={
                "activity_type": "quiz",
                "title": "Quiz: Python Concurrency",
                "summary": "Score: 5/5 (100%)",
                "score": 100.0,
                "data": {
                    "topic": "Python Concurrency",
                    "milestone": "Advanced Concurrency",
                },
            },
        )
        self.assertEqual(res_a_quiz.status_code, 201)
        a_activity_id = res_a_quiz.json()["id"]

        # User B queries their learning history - must NOT see User A's quiz
        res_b_history = self.client.get(
            "/api/learning-history",
            headers=self.headers_b,
        )
        self.assertEqual(res_b_history.status_code, 200)
        b_items = res_b_history.json()
        self.assertEqual(len(b_items), 0)

        # User B attempts to access User A's activity directly - must receive 404
        res_b_access = self.client.get(
            f"/api/learning-history/{a_activity_id}",
            headers=self.headers_b,
        )
        self.assertEqual(res_b_access.status_code, 404)

        # User B progress must reflect 0 attempts, not User A's 100% score
        res_b_progress = self.client.get(
            "/api/progress",
            headers=self.headers_b,
        )
        self.assertEqual(res_b_progress.status_code, 200)
        b_prog = res_b_progress.json()
        self.assertEqual(b_prog["quiz_analytics"]["total_attempts"], 0)
        self.assertIn(b_prog["quiz_analytics"]["average_score"], (0.0, None))

    def test_06_backward_compatibility_without_milestone_field(self):
        """Legacy activities without milestone field still calculate progress safely."""
        raw_steps = [
            {
                "milestone": "Networking & Protocols",
                "completed": False,
                "skills": ["TCP/IP", "HTTP/3"],
                "estimated_hours": 8.0,
            }
        ]

        # Legacy quiz activity without 'milestone' key in data
        legacy_quiz = LearningActivity(
            activity_type="quiz",
            title="Quiz: Networking & Protocols",
            score=75.0,
            created_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
            data={
                "topic": "Networking & Protocols",
                "evaluation": {"score": 75.0},
            },
        )

        # Legacy tutor activity without 'milestone' key in data
        legacy_tutor = LearningActivity(
            activity_type="tutor",
            title="AI Tutor: TCP/IP",
            created_at=datetime(2026, 10, 6, tzinfo=timezone.utc),
            data={
                "topic": "TCP/IP",
                "question": "What is the 3-way handshake?",
            },
        )

        m_res = calculate_milestone_mastery(
            raw_steps=raw_steps,
            quiz_activities=[legacy_quiz],
            tutor_activities=[legacy_tutor],
            weak_topics=[],
        )

        self.assertEqual(len(m_res), 1)
        self.assertEqual(m_res[0].mastery_status, "MASTERED")
        self.assertEqual(m_res[0].latest_score, 75.0)


if __name__ == "__main__":
    unittest.main()
