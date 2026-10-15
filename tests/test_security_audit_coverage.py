import unittest
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.core.config import settings
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.student_profile import StudentProfile
from backend.models.student_skill import StudentSkill
from backend.models.learning_activity import LearningActivity


class TestSecurityAuditCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        cls.email_a = "sec_test_a@campuscompass.org"
        cls.email_b = "sec_test_b@campuscompass.org"
        cls.email_no_prof = "sec_test_no_prof@campuscompass.org"
        cls.password = "SecurePassword123!"

        cls._cleanup()

        # 1. Register User A
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Security User A",
                "email": cls.email_a,
                "password": cls.password,
            },
        )
        assert res_a.status_code == 201, f"User A registration failed: {res_a.text}"

        # 2. Register User B
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Security User B",
                "email": cls.email_b,
                "password": cls.password,
            },
        )
        assert res_b.status_code == 201, f"User B registration failed: {res_b.text}"

        # 3. Register User No Profile
        res_np = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Security User No Profile",
                "email": cls.email_no_prof,
                "password": cls.password,
            },
        )
        assert res_np.status_code == 201, f"User No Profile registration failed: {res_np.text}"

        # Logins to get valid JWTs
        login_a = cls.client.post(
            "/auth/login",
            data={"username": cls.email_a, "password": cls.password},
        )
        assert login_a.status_code == 200
        cls.token_a = login_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        login_b = cls.client.post(
            "/auth/login",
            data={"username": cls.email_b, "password": cls.password},
        )
        assert login_b.status_code == 200
        cls.token_b = login_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        login_np = cls.client.post(
            "/auth/login",
            data={"username": cls.email_no_prof, "password": cls.password},
        )
        assert login_np.status_code == 200
        cls.token_np = login_np.json()["access_token"]
        cls.headers_no_profile = {"Authorization": f"Bearer {cls.token_np}"}

        # Create profiles for User A and User B
        prof_a = cls.client.post(
            "/api/student-profile",
            headers=cls.headers_a,
            json={
                "degree": "B.Tech",
                "branch": "Computer Science",
                "current_year": 3,
                "semester": 6,
                "career_goal": "Security Engineer",
                "interests": "AppSec, Cryptography",
                "weekly_hours": 20,
            },
        )
        assert prof_a.status_code == 201, f"Profile A failed: {prof_a.text}"

        prof_b = cls.client.post(
            "/api/student-profile",
            headers=cls.headers_b,
            json={
                "degree": "B.Sc",
                "branch": "Information Tech",
                "current_year": 2,
                "semester": 4,
                "career_goal": "Fullstack Dev",
                "interests": "React, FastAPI",
                "weekly_hours": 15,
            },
        )
        assert prof_b.status_code == 201, f"Profile B failed: {prof_b.text}"

        # Generate specialized tokens for security testing
        # 1. Expired JWT
        expired_exp = datetime.now(timezone.utc) - timedelta(hours=2)
        cls.token_expired = jwt.encode(
            {"sub": cls.email_a, "exp": expired_exp},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # 2. Wrong secret key JWT
        cls.token_wrong_secret = jwt.encode(
            {"sub": cls.email_a, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "completely_wrong_secret_key_987654321",
            algorithm=settings.ALGORITHM,
        )

        # 3. Missing sub claim JWT
        cls.token_no_sub = jwt.encode(
            {"role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # 4. Non-existent user email in sub
        cls.token_nonexistent_user = jwt.encode(
            {"sub": "ghost_nonexistent_user@campuscompass.org", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # 5. Tampered token (modify last signature character)
        cls.token_tampered = cls.token_a[:-5] + ("abcde" if cls.token_a[-5:] != "abcde" else "vwxyz")

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.db.close()

    @classmethod
    def _cleanup(cls):
        test_emails = [
            "sec_test_a@campuscompass.org",
            "sec_test_b@campuscompass.org",
            "sec_test_no_prof@campuscompass.org",
        ]
        for email in test_emails:
            user = cls.db.query(User).filter(User.email == email).first()
            if user:
                profile = cls.db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
                if profile:
                    cls.db.query(StudentSkill).filter(StudentSkill.student_profile_id == profile.id).delete()
                    cls.db.delete(profile)
                cls.db.query(LearningActivity).filter(LearningActivity.user_id == user.id).delete()
                cls.db.delete(user)
        cls.db.commit()

    # =========================================================================
    # Group 1: JWT Handling & Edge Cases (Rule 2)
    # =========================================================================

    def test_01_malformed_jwt_strings_rejected(self):
        """Malformed, non-JWT token strings must be rejected with 401 and Bearer header."""
        malformed_tokens = [
            "not-a-token",
            "invalid.token",
            "Bearer invalid.jwt.structure",
            "ey-bad-base64-content",
        ]
        for bad_token in malformed_tokens:
            res = self.client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {bad_token}"},
            )
            self.assertEqual(res.status_code, 401, f"Expected 401 for bad token: {bad_token}")
            self.assertEqual(res.json()["detail"], "Could not validate credentials")
            self.assertEqual(res.headers.get("www-authenticate"), "Bearer")

    def test_02_expired_jwt_rejected(self):
        """Expired JWT tokens must be rejected with 401 across endpoints."""
        endpoints = [
            ("GET", "/auth/me"),
            ("GET", "/api/skills"),
            ("GET", "/api/learning-history"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                res = self.client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.token_expired}"},
                )
            self.assertEqual(res.status_code, 401, f"Endpoint {endpoint} allowed expired token")
            self.assertEqual(res.json()["detail"], "Could not validate credentials")

    def test_03_wrong_secret_signature_rejected(self):
        """Tokens signed with an invalid or untrusted secret key must be rejected with 401."""
        res = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.token_wrong_secret}"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Could not validate credentials")

    def test_04_tampered_jwt_signature_rejected(self):
        """Tokens with tampered payloads or signatures must be rejected with 401."""
        res = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.token_tampered}"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Could not validate credentials")

    def test_05_missing_sub_claim_rejected(self):
        """Tokens lacking the 'sub' claim must be rejected with 401."""
        res = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.token_no_sub}"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Could not validate credentials")

    def test_06_nonexistent_user_token_rejected(self):
        """Tokens with a valid signature but non-existent user email in 'sub' must return 401."""
        res = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.token_nonexistent_user}"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Could not validate credentials")

    # =========================================================================
    # Group 2: Skills Routes Cross-User Isolation & CRUD (Rule 3)
    # =========================================================================

    def test_07_skills_unauthenticated_rejected(self):
        """All /api/skills endpoints require authentication (401)."""
        # GET
        res = self.client.get("/api/skills")
        self.assertEqual(res.status_code, 401)

        # POST
        res = self.client.post("/api/skills", json={"name": "Python", "proficiency": 50})
        self.assertEqual(res.status_code, 401)

        # PUT
        res = self.client.put("/api/skills/1", json={"name": "Python", "proficiency": 60})
        self.assertEqual(res.status_code, 401)

        # DELETE
        res = self.client.delete("/api/skills/1")
        self.assertEqual(res.status_code, 401)

    def test_08_skills_no_profile_returns_404(self):
        """Authenticated users without a student profile receive 404 on skills endpoints."""
        res_get = self.client.get("/api/skills", headers=self.headers_no_profile)
        self.assertEqual(res_get.status_code, 404)
        self.assertIn("student profile not found", res_get.json()["detail"].lower())

        res_post = self.client.post(
            "/api/skills",
            headers=self.headers_no_profile,
            json={"name": "Python", "proficiency": 50},
        )
        self.assertEqual(res_post.status_code, 404)
        self.assertIn("student profile not found", res_post.json()["detail"].lower())

        res_put = self.client.put(
            "/api/skills/999",
            headers=self.headers_no_profile,
            json={"name": "Python", "proficiency": 60},
        )
        self.assertEqual(res_put.status_code, 404)
        self.assertIn("student profile not found", res_put.json()["detail"].lower())

        res_del = self.client.delete("/api/skills/999", headers=self.headers_no_profile)
        self.assertEqual(res_del.status_code, 404)
        self.assertIn("student profile not found", res_del.json()["detail"].lower())

    def test_09_skills_cross_user_isolation(self):
        """Cross-user skills operations (read, update, delete) must be strictly isolated."""
        # 1. User A creates Skill A
        res_a = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={
                "name": "User A Private Skill",
                "proficiency": 80,
                "strengths": "FastAPI, PostgreSQL",
                "weak_areas": "None",
                "experience": "2 years",
            },
        )
        self.assertEqual(res_a.status_code, 201)
        skill_a_id = res_a.json()["id"]

        # 2. User B creates Skill B
        res_b = self.client.post(
            "/api/skills",
            headers=self.headers_b,
            json={
                "name": "User B Separate Skill",
                "proficiency": 65,
                "strengths": "CSS, React",
                "weak_areas": "Backend",
                "experience": "1 year",
            },
        )
        self.assertEqual(res_b.status_code, 201)
        skill_b_id = res_b.json()["id"]

        # 3. Read isolation
        res_a_list = self.client.get("/api/skills", headers=self.headers_a)
        self.assertEqual(res_a_list.status_code, 200)
        a_ids = [s["id"] for s in res_a_list.json()]
        self.assertIn(skill_a_id, a_ids)
        self.assertNotIn(skill_b_id, a_ids)

        res_b_list = self.client.get("/api/skills", headers=self.headers_b)
        self.assertEqual(res_b_list.status_code, 200)
        b_ids = [s["id"] for s in res_b_list.json()]
        self.assertIn(skill_b_id, b_ids)
        self.assertNotIn(skill_a_id, b_ids)

        # 4. Cross-user update rejected (User B attempts to modify Skill A)
        res_b_update = self.client.put(
            f"/api/skills/{skill_a_id}",
            headers=self.headers_b,
            json={
                "name": "Hacked Skill Name",
                "proficiency": 99,
                "strengths": "Malicious",
                "weak_areas": "Malicious",
                "experience": "Malicious",
            },
        )
        self.assertEqual(res_b_update.status_code, 404)
        self.assertIn("skill not found", res_b_update.json()["detail"].lower())

        # Verify Skill A remains unchanged
        res_a_check = self.client.get("/api/skills", headers=self.headers_a)
        skill_a_current = next(s for s in res_a_check.json() if s["id"] == skill_a_id)
        self.assertEqual(skill_a_current["name"], "User A Private Skill")
        self.assertEqual(skill_a_current["proficiency"], 80)

        # 5. Cross-user delete rejected (User B attempts to delete Skill A)
        res_b_del = self.client.delete(f"/api/skills/{skill_a_id}", headers=self.headers_b)
        self.assertEqual(res_b_del.status_code, 404)
        self.assertIn("skill not found", res_b_del.json()["detail"].lower())

        # Verify Skill A is still intact in User A's skills list
        res_a_check2 = self.client.get("/api/skills", headers=self.headers_a)
        self.assertTrue(any(s["id"] == skill_a_id for s in res_a_check2.json()))

        # 6. User A updates own skill -> 200
        res_a_update = self.client.put(
            f"/api/skills/{skill_a_id}",
            headers=self.headers_a,
            json={
                "name": "User A Updated Skill",
                "proficiency": 90,
                "strengths": "FastAPI, PostgreSQL, AppSec",
                "weak_areas": "None",
                "experience": "3 years",
            },
        )
        self.assertEqual(res_a_update.status_code, 200)
        self.assertEqual(res_a_update.json()["name"], "User A Updated Skill")
        self.assertEqual(res_a_update.json()["proficiency"], 90)

        # 7. User A deletes own skill -> 204
        res_a_del = self.client.delete(f"/api/skills/{skill_a_id}", headers=self.headers_a)
        self.assertEqual(res_a_del.status_code, 204)

        # Subsequent GET verifies skill is gone
        res_a_final = self.client.get("/api/skills", headers=self.headers_a)
        self.assertFalse(any(s["id"] == skill_a_id for s in res_a_final.json()))

    # =========================================================================
    # Group 3: Learning History Routes Cross-User Isolation (Rule 3)
    # =========================================================================

    def test_10_learning_history_cross_user_isolation(self):
        """Cross-user learning history operations (read list, read detail, update, delete) must return 404."""
        # 1. User A creates private activity
        res_a = self.client.post(
            "/api/learning-history",
            headers=self.headers_a,
            json={
                "activity_type": "quiz",
                "title": "User A Private Exam",
                "summary": "Confidential exam details",
                "score": 95.0,
            },
        )
        self.assertEqual(res_a.status_code, 201)
        act_a_id = res_a.json()["id"]

        # 2. User B creates separate activity
        res_b = self.client.post(
            "/api/learning-history",
            headers=self.headers_b,
            json={
                "activity_type": "roadmap",
                "title": "User B Roadmap",
                "summary": "User B milestones",
                "score": 50.0,
            },
        )
        self.assertEqual(res_b.status_code, 201)
        act_b_id = res_b.json()["id"]

        # 3. Read list isolation
        res_b_list = self.client.get("/api/learning-history", headers=self.headers_b)
        self.assertEqual(res_b_list.status_code, 200)
        b_ids = [act["id"] for act in res_b_list.json()]
        self.assertIn(act_b_id, b_ids)
        self.assertNotIn(act_a_id, b_ids)

        # 4. Read detail isolation (User B attempts GET on Act A) -> 404
        res_b_get = self.client.get(f"/api/learning-history/{act_a_id}", headers=self.headers_b)
        self.assertEqual(res_b_get.status_code, 404)
        self.assertIn("learning activity not found", res_b_get.json()["detail"].lower())

        # 5. Cross-user update isolation (User B attempts PATCH on Act A) -> 404
        res_b_patch = self.client.patch(
            f"/api/learning-history/{act_a_id}",
            headers=self.headers_b,
            json={"summary": "Tampered summary by Bob", "score": 0.0},
        )
        self.assertEqual(res_b_patch.status_code, 404)
        self.assertIn("learning activity not found", res_b_patch.json()["detail"].lower())

        # Verify Act A summary is untouched
        res_a_check = self.client.get(f"/api/learning-history/{act_a_id}", headers=self.headers_a)
        self.assertEqual(res_a_check.status_code, 200)
        self.assertEqual(res_a_check.json()["summary"], "Confidential exam details")
        self.assertEqual(res_a_check.json()["score"], 95.0)

        # 6. Cross-user delete isolation (User B attempts DELETE on Act A) -> 404
        res_b_del = self.client.delete(f"/api/learning-history/{act_a_id}", headers=self.headers_b)
        self.assertEqual(res_b_del.status_code, 404)
        self.assertIn("learning activity not found", res_b_del.json()["detail"].lower())

        # Verify Act A still exists
        res_a_check2 = self.client.get(f"/api/learning-history/{act_a_id}", headers=self.headers_a)
        self.assertEqual(res_a_check2.status_code, 200)

        # 7. User A deletes own activity -> 204
        res_a_del = self.client.delete(f"/api/learning-history/{act_a_id}", headers=self.headers_a)
        self.assertEqual(res_a_del.status_code, 204)

        # Subsequent GET returns 404
        res_a_final = self.client.get(f"/api/learning-history/{act_a_id}", headers=self.headers_a)
        self.assertEqual(res_a_final.status_code, 404)

    # =========================================================================
    # Group 4: AI Endpoints Targeted Regression (Rule 4)
    # =========================================================================

    def test_11_ai_endpoints_reject_expired_jwt(self):
        """AI endpoints must reject expired JWT tokens with 401."""
        # 1. /api/assessment with expired token
        res_ass = self.client.post(
            "/api/assessment",
            headers={"Authorization": f"Bearer {self.token_expired}"},
            json={
                "name": "Student A",
                "email": self.email_a,
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 6,
                "career_goal": "Security",
                "weekly_hours": 10,
            },
        )
        self.assertEqual(res_ass.status_code, 401)
        self.assertEqual(res_ass.json()["detail"], "Could not validate credentials")

        # 2. /api/quiz with expired token
        res_quiz = self.client.post(
            "/api/quiz",
            headers={"Authorization": f"Bearer {self.token_expired}"},
            json={
                "student": {
                    "name": "Student A",
                    "email": self.email_a,
                    "degree": "B.Tech",
                    "branch": "CS",
                    "current_year": 3,
                    "semester": 6,
                    "career_goal": "Security",
                    "weekly_hours": 10,
                },
                "topic": "Python Security",
                "num_questions": 3,
            },
        )
        self.assertEqual(res_quiz.status_code, 401)
        self.assertEqual(res_quiz.json()["detail"], "Could not validate credentials")

    def test_12_ai_endpoints_reject_tampered_jwt(self):
        """AI endpoints must reject tampered JWT signatures with 401."""
        # 1. /api/recommendations with tampered token
        res_rec = self.client.post(
            "/api/recommendations",
            headers={"Authorization": f"Bearer {self.token_tampered}"},
            json={
                "name": "Student A",
                "email": self.email_a,
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 6,
                "career_goal": "Security",
                "weekly_hours": 10,
            },
        )
        self.assertEqual(res_rec.status_code, 401)
        self.assertEqual(res_rec.json()["detail"], "Could not validate credentials")

        # 2. /api/skill-analysis with tampered token
        res_skill_an = self.client.post(
            "/api/skill-analysis",
            headers={"Authorization": f"Bearer {self.token_tampered}"},
            json={
                "skills": [
                    {
                        "name": "Cryptography",
                        "proficiency": 80,
                    }
                ]
            },
        )
        self.assertEqual(res_skill_an.status_code, 401)
        self.assertEqual(res_skill_an.json()["detail"], "Could not validate credentials")

    def test_13_ai_endpoints_reject_nonexistent_user_token(self):
        """AI endpoints must reject validly signed tokens for non-existent users with 401."""
        res_tutor = self.client.post(
            "/api/tutor",
            headers={"Authorization": f"Bearer {self.token_nonexistent_user}"},
            json={
                "student": {
                    "name": "Ghost",
                    "email": "ghost@campuscompass.org",
                    "degree": "B.Tech",
                    "branch": "CS",
                    "current_year": 1,
                    "semester": 1,
                    "career_goal": "None",
                    "weekly_hours": 5,
                },
                "topic": "Algorithms",
                "question": "What is binary search?",
            },
        )
        self.assertEqual(res_tutor.status_code, 401)
        self.assertEqual(res_tutor.json()["detail"], "Could not validate credentials")

    # =========================================================================
    # Group 5: Input Validation & Unbounded Payload Bounds (Rule 5)
    # =========================================================================

    def test_14_skills_input_validation_and_unbounded_payload_rejection(self):
        """SkillCreate and SkillUpdate must reject unbounded strings (>1000 chars) and invalid bounds."""
        # 1. Name validation
        res_empty_name = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "", "proficiency": 50},
        )
        self.assertEqual(res_empty_name.status_code, 422)

        res_long_name = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "A" * 101, "proficiency": 50},
        )
        self.assertEqual(res_long_name.status_code, 422)

        # 2. Proficiency bounds
        res_neg_prof = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "Valid Name", "proficiency": -1},
        )
        self.assertEqual(res_neg_prof.status_code, 422)

        res_over_prof = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "Valid Name", "proficiency": 101},
        )
        self.assertEqual(res_over_prof.status_code, 422)

        # 3. Unbounded payload rejection for strengths, weak_areas, experience (>1000 chars)
        oversized_str = "x" * 1001

        res_big_strengths = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "Python", "proficiency": 75, "strengths": oversized_str},
        )
        self.assertEqual(res_big_strengths.status_code, 422)

        res_big_weak = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "Python", "proficiency": 75, "weak_areas": oversized_str},
        )
        self.assertEqual(res_big_weak.status_code, 422)

        res_big_exp = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={"name": "Python", "proficiency": 75, "experience": oversized_str},
        )
        self.assertEqual(res_big_exp.status_code, 422)

        # 4. Valid payload at boundary (1000 chars) succeeds
        valid_boundary_str = "x" * 1000
        res_boundary = self.client.post(
            "/api/skills",
            headers=self.headers_a,
            json={
                "name": "Boundary Test Skill",
                "proficiency": 80,
                "strengths": valid_boundary_str,
                "weak_areas": "None",
                "experience": "Valid",
            },
        )
        self.assertEqual(res_boundary.status_code, 201)
        skill_id = res_boundary.json()["id"]

        # 5. SkillUpdate also rejects oversized fields
        res_update_oversized = self.client.put(
            f"/api/skills/{skill_id}",
            headers=self.headers_a,
            json={
                "name": "Updated Skill",
                "proficiency": 85,
                "strengths": oversized_str,
            },
        )
        self.assertEqual(res_update_oversized.status_code, 422)

        # Clean up created skill
        self.client.delete(f"/api/skills/{skill_id}", headers=self.headers_a)

    def test_15_learning_history_payload_bounds(self):
        """Learning activity data payload size (>500KB) and bounds must be rejected."""
        oversized_dict = {"large_field": "x" * 500001}
        res = self.client.post(
            "/api/learning-history",
            headers=self.headers_a,
            json={
                "activity_type": "practice",
                "title": "Oversized Payload Activity",
                "data": oversized_dict,
            },
        )
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
