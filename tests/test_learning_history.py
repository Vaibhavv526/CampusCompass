import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.learning_activity import LearningActivity


class TestPhase2ALearningHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.email_a = "alice_history@campuscompass.org"
        cls.email_b = "bob_history@campuscompass.org"
        cls.password = "ValidPassword123!"

        cls._cleanup_users()

        # Register User A
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Alice History",
                "email": cls.email_a,
                "password": cls.password,
            },
        )
        assert res_a.status_code == 201, f"User A reg failed: {res_a.text}"

        # Register User B
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Bob History",
                "email": cls.email_b,
                "password": cls.password,
            },
        )
        assert res_b.status_code == 201, f"User B reg failed: {res_b.text}"

        # Login User A
        login_a = cls.client.post(
            "/auth/login",
            data={
                "username": cls.email_a,
                "password": cls.password,
            },
        )
        assert login_a.status_code == 200, f"User A login failed: {login_a.text}"
        cls.token_a = login_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Login User B
        login_b = cls.client.post(
            "/auth/login",
            data={
                "username": cls.email_b,
                "password": cls.password,
            },
        )
        assert login_b.status_code == 200, f"User B login failed: {login_b.text}"
        cls.token_b = login_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_users()
        cls.db.close()

    @classmethod
    def _cleanup_users(cls):
        try:
            users = (
                cls.db.query(User)
                .filter(User.email.in_([cls.email_a, cls.email_b]))
                .all()
            )
            for user in users:
                cls.db.delete(user)
            cls.db.commit()
        except Exception:
            cls.db.rollback()

    def test_01_unauthenticated_requests_fail(self):
        """Unauthenticated requests must be rejected with 401."""
        res_get = self.client.get("/api/learning-history")
        self.assertEqual(res_get.status_code, 401)

        res_post = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "Test Quiz",
            },
        )
        self.assertEqual(res_post.status_code, 401)

        res_detail = self.client.get("/api/learning-history/1")
        self.assertEqual(res_detail.status_code, 401)

        res_patch = self.client.patch("/api/learning-history/1", json={"summary": "Updated"})
        self.assertEqual(res_patch.status_code, 401)

        res_delete = self.client.delete("/api/learning-history/1")
        self.assertEqual(res_delete.status_code, 401)

    def test_02_validation_errors(self):
        """Invalid activity types, lengths, scores, and bounds return 422."""
        # Invalid activity type
        res_invalid_type = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "unknown_action",
                "title": "Valid Title",
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_invalid_type.status_code, 422)

        # Empty title
        res_empty_title = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "",
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_empty_title.status_code, 422)

        # Score > 100
        res_high_score = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "Math Quiz",
                "score": 150.0,
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_high_score.status_code, 422)

        # Score < 0
        res_low_score = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "Math Quiz",
                "score": -5.0,
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_low_score.status_code, 422)

        # Pagination limits
        res_bad_limit = self.client.get(
            "/api/learning-history?limit=0",
            headers=self.headers_a,
        )
        self.assertEqual(res_bad_limit.status_code, 422)

        res_excess_limit = self.client.get(
            "/api/learning-history?limit=101",
            headers=self.headers_a,
        )
        self.assertEqual(res_excess_limit.status_code, 422)

        res_bad_offset = self.client.get(
            "/api/learning-history?offset=-1",
            headers=self.headers_a,
        )
        self.assertEqual(res_bad_offset.status_code, 422)

    def test_03_create_and_list_activities(self):
        """Alice creates multiple activity types; ordering and ownership are verified."""
        # 1. Assessment
        res_ass = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "assessment",
                "title": "Initial Skill Gap Assessment",
                "summary": "Identified 4 skill gaps in Machine Learning",
                "score": None,
                "data": {"high_priority_gaps": ["PyTorch", "Calculus"]},
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_ass.status_code, 201)
        data_ass = res_ass.json()
        self.assertEqual(data_ass["activity_type"], "assessment")
        self.assertEqual(data_ass["title"], "Initial Skill Gap Assessment")
        self.assertIn("id", data_ass)

        # 2. Quiz
        res_quiz = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "Quiz: Python Basics",
                "summary": "Scored 4/5 (80%)",
                "score": 80.0,
                "data": {"topic": "Python", "score": 4, "total": 5},
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_quiz.status_code, 201)

        # 3. Roadmap
        res_road = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "roadmap",
                "title": "AI Engineer Career Roadmap",
                "summary": "0/4 milestones completed",
                "score": 0.0,
                "data": {"steps": [{"title": "Learn Numpy", "completed": False}]},
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_road.status_code, 201)

        # List activities for Alice
        res_list = self.client.get(
            "/api/learning-history",
            headers=self.headers_a,
        )
        self.assertEqual(res_list.status_code, 200)
        items = res_list.json()
        self.assertGreaterEqual(len(items), 3)

        # Reverse chronological order check
        created_times = [item["created_at"] for item in items]
        self.assertEqual(created_times, sorted(created_times, reverse=True))

    def test_04_filtering_and_pagination(self):
        """Filter by activity_type and paginate using limit/offset."""
        res_quiz = self.client.get(
            "/api/learning-history?activity_type=quiz",
            headers=self.headers_a,
        )
        self.assertEqual(res_quiz.status_code, 200)
        quizzes = res_quiz.json()
        self.assertTrue(all(item["activity_type"] == "quiz" for item in quizzes))

        # Pagination
        res_p1 = self.client.get(
            "/api/learning-history?limit=1&offset=0",
            headers=self.headers_a,
        )
        self.assertEqual(res_p1.status_code, 200)
        self.assertEqual(len(res_p1.json()), 1)

        res_p2 = self.client.get(
            "/api/learning-history?limit=1&offset=1",
            headers=self.headers_a,
        )
        self.assertEqual(res_p2.status_code, 200)
        self.assertEqual(len(res_p2.json()), 1)

        # Items should be distinct
        self.assertNotEqual(res_p1.json()[0]["id"], res_p2.json()[0]["id"])

    def test_05_detail_and_update(self):
        """Detail retrieval and non-duplicative updates (e.g. roadmap milestone toggle)."""
        # Create a roadmap activity
        res_create = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "roadmap",
                "title": "Updatable Roadmap",
                "summary": "0 of 2 milestones completed",
                "score": 0.0,
                "data": {
                    "steps": [
                        {"title": "Step 1", "completed": False},
                        {"title": "Step 2", "completed": False},
                    ]
                },
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_create.status_code, 201)
        activity_id = res_create.json()["id"]

        # Retrieve detail
        res_detail = self.client.get(
            f"/api/learning-history/{activity_id}",
            headers=self.headers_a,
        )
        self.assertEqual(res_detail.status_code, 200)
        self.assertEqual(res_detail.json()["title"], "Updatable Roadmap")

        # Update milestone progress via PATCH
        res_patch = self.client.patch(
            f"/api/learning-history/{activity_id}",
            json={
                "summary": "1 of 2 milestones completed",
                "score": 50.0,
                "data": {
                    "steps": [
                        {"title": "Step 1", "completed": True},
                        {"title": "Step 2", "completed": False},
                    ]
                },
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_patch.status_code, 200)
        updated = res_patch.json()
        self.assertEqual(updated["summary"], "1 of 2 milestones completed")
        self.assertEqual(updated["score"], 50.0)
        self.assertTrue(updated["data"]["steps"][0]["completed"])

    def test_06_ownership_isolation(self):
        """Bob cannot view, update, or delete Alice's activities (strict 404)."""
        # Alice creates a private activity
        res_a = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "quiz",
                "title": "Alice Secret Quiz",
                "score": 100.0,
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_a.status_code, 201)
        alice_act_id = res_a.json()["id"]

        # Bob lists his own activities
        res_bob_list = self.client.get(
            "/api/learning-history",
            headers=self.headers_b,
        )
        self.assertEqual(res_bob_list.status_code, 200)
        bob_ids = [item["id"] for item in res_bob_list.json()]
        self.assertNotIn(alice_act_id, bob_ids)

        # Bob attempts GET on Alice activity -> 404
        res_bob_get = self.client.get(
            f"/api/learning-history/{alice_act_id}",
            headers=self.headers_b,
        )
        self.assertEqual(res_bob_get.status_code, 404)
        self.assertIn("not found", res_bob_get.json()["detail"].lower())

        # Bob attempts PATCH on Alice activity -> 404
        res_bob_patch = self.client.patch(
            f"/api/learning-history/{alice_act_id}",
            json={"summary": "Hacked by Bob"},
            headers=self.headers_b,
        )
        self.assertEqual(res_bob_patch.status_code, 404)

        # Bob attempts DELETE on Alice activity -> 404
        res_bob_del = self.client.delete(
            f"/api/learning-history/{alice_act_id}",
            headers=self.headers_b,
        )
        self.assertEqual(res_bob_del.status_code, 404)

        # Verify Alice's activity is still intact
        res_check = self.client.get(
            f"/api/learning-history/{alice_act_id}",
            headers=self.headers_a,
        )
        self.assertEqual(res_check.status_code, 200)
        self.assertEqual(res_check.json()["title"], "Alice Secret Quiz")

    def test_07_delete_own_activity(self):
        """Alice can delete her own activity, returning 204 then 404 on subsequent get."""
        res_create = self.client.post(
            "/api/learning-history",
            json={
                "activity_type": "practice",
                "title": "Practice to Delete",
            },
            headers=self.headers_a,
        )
        self.assertEqual(res_create.status_code, 201)
        act_id = res_create.json()["id"]

        res_del = self.client.delete(
            f"/api/learning-history/{act_id}",
            headers=self.headers_a,
        )
        self.assertEqual(res_del.status_code, 204)

        res_get_again = self.client.get(
            f"/api/learning-history/{act_id}",
            headers=self.headers_a,
        )
        self.assertEqual(res_get_again.status_code, 404)

    def test_08_stateless_agent_compatibility(self):
        """Existing agent routes continue working for authenticated users with mocked agents."""
        assessment_payload = {
            "name": "Anonymous Student",
            "email": "anon@example.com",
            "degree": "B.Tech",
            "branch": "CS",
            "current_year": 2,
            "semester": 4,
            "career_goal": "Software Engineer",
            "interests": ["Python"],
            "weekly_hours": 10,
            "skills": [
                {
                    "name": "Python",
                    "category": "Technical",
                    "current_level": 50,
                    "target_level": 80,
                }
            ],
        }

        mock_assessment_resp = {
            "summary": {
                "student_name": "Anonymous Student",
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 2,
                "semester": 4,
                "career_goal": "Software Engineer",
                "weekly_study_hours": 10.0,
            },
            "skill_gaps": [],
            "recommendations": [],
        }

        with patch(
            "backend.routes.assessment.StudentMentorOrchestrator.assess_student",
            return_value=mock_assessment_resp,
        ) as mock_assess:
            res_ass = self.client.post(
                "/api/assessment",
                headers=self.headers_a,
                json=assessment_payload,
            )
            self.assertEqual(res_ass.status_code, 200)
            mock_assess.assert_called_once()
            self.assertEqual(
                res_ass.json()["summary"]["student_name"],
                "Anonymous Student",
            )

        quiz_eval_payload = {
            "quiz": {
                "topic": "Python",
                "difficulty": "Medium",
                "questions": [
                    {
                        "question": "What is 2+2?",
                        "options": ["3", "4", "5"],
                        "correct_answer": "4",
                        "explanation": "Math",
                    }
                ],
            },
            "student_answers": ["4"],
        }

        mock_eval_resp = {
            "topic": "Python",
            "total_questions": 1,
            "correct_answers": 1,
            "score_percentage": 100.0,
            "question_results": [
                {
                    "question": "What is 2+2?",
                    "student_answer": "4",
                    "correct_answer": "4",
                    "is_correct": True,
                    "explanation": "Math",
                }
            ],
            "weak_topics": [],
            "recommendation": "Great job!",
        }

        with patch(
            "backend.routes.quiz.QuizEvaluationAgent.evaluate",
            return_value=mock_eval_resp,
        ) as mock_eval:
            res_eval = self.client.post(
                "/api/quiz/evaluate",
                headers=self.headers_a,
                json=quiz_eval_payload,
            )
            self.assertEqual(res_eval.status_code, 200)
            mock_eval.assert_called_once()
            self.assertEqual(res_eval.json()["score_percentage"], 100.0)


if __name__ == "__main__":
    unittest.main()
