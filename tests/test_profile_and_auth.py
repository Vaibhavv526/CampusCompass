import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.student_profile import StudentProfile
from backend.services.user_service import change_password


class TestPhase1ProfileAndAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.email_a = "alice_phase1@campuscompass.org"
        cls.email_b = "bob_phase1@campuscompass.org"
        cls.password_orig = "ValidPassword123!"
        cls.password_new = "NewSecurePassword456!"

        # Clean up any leftover test users
        cls._cleanup_users()

        # Register User A
        res_a = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Alice Original",
                "email": cls.email_a,
                "password": cls.password_orig,
            },
        )
        assert res_a.status_code == 201, f"User A registration failed: {res_a.text}"

        # Register User B
        res_b = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Bob Builder",
                "email": cls.email_b,
                "password": cls.password_orig,
            },
        )
        assert res_b.status_code == 201, f"User B registration failed: {res_b.text}"

        # Login User A
        login_a = cls.client.post(
            "/auth/login",
            data={
                "username": cls.email_a,
                "password": cls.password_orig,
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
                "password": cls.password_orig,
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
            for u in users:
                cls.db.delete(u)
            cls.db.commit()
        except Exception:
            cls.db.rollback()

    def test_01_unauthenticated_requests_rejected(self):
        # Unauthenticated profile update
        res = self.client.put(
            "/api/student-profile",
            json={
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 5,
                "career_goal": "AI Engineer",
            },
        )
        self.assertEqual(res.status_code, 401)

        # Unauthenticated password change
        res = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "any",
                "new_password": "anynewpassword",
            },
        )
        self.assertEqual(res.status_code, 401)

    def test_02_update_missing_profile_returns_404(self):
        # User A has not created profile yet
        res = self.client.put(
            "/api/student-profile",
            headers=self.headers_a,
            json={
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 5,
                "career_goal": "AI Engineer",
            },
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_03_create_initial_profile_and_validation(self):
        # Invalid creation (year > 10)
        res_bad = self.client.post(
            "/api/student-profile",
            headers=self.headers_a,
            json={
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 99,
                "semester": 5,
                "career_goal": "AI Engineer",
            },
        )
        self.assertEqual(res_bad.status_code, 422)

        # Valid creation
        res = self.client.post(
            "/api/student-profile",
            headers=self.headers_a,
            json={
                "degree": "B.Tech",
                "branch": "Computer Science",
                "current_year": 2,
                "semester": 4,
                "career_goal": "Software Engineer",
                "interests": "Python, Web Dev",
                "weekly_hours": 15,
            },
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["full_name"], "Alice Original")
        self.assertEqual(data["career_goal"], "Software Engineer")

    def test_04_update_profile_validation_and_success(self):
        # Invalid update: weekly_hours > 168
        res_invalid = self.client.put(
            "/api/student-profile",
            headers=self.headers_a,
            json={
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 5,
                "career_goal": "ML Researcher",
                "weekly_hours": 200,
            },
        )
        self.assertEqual(res_invalid.status_code, 422)

        # Valid update: updates fields AND updates full_name across User and StudentProfile
        res_valid = self.client.put(
            "/api/student-profile",
            headers=self.headers_a,
            json={
                "full_name": "Alice Wonder",
                "degree": "M.Tech",
                "branch": "Artificial Intelligence",
                "current_year": 1,
                "semester": 2,
                "career_goal": "Lead AI Researcher",
                "interests": "Deep Learning, LLMs, NLP",
                "weekly_hours": 25,
            },
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.json()
        self.assertEqual(data["full_name"], "Alice Wonder")
        self.assertEqual(data["degree"], "M.Tech")
        self.assertEqual(data["branch"], "Artificial Intelligence")
        self.assertEqual(data["career_goal"], "Lead AI Researcher")
        self.assertEqual(data["weekly_hours"], 25)

        # Verify /auth/me reflects the updated full_name from the User table
        me_res = self.client.get("/auth/me", headers=self.headers_a)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["full_name"], "Alice Wonder")

    def test_05_user_profile_isolation(self):
        # User B should NOT be able to access User A's profile data through their own token
        res_b = self.client.get("/api/student-profile", headers=self.headers_b)
        # User B hasn't created a profile yet, so it must return 404
        self.assertEqual(res_b.status_code, 404)

        # User B creates a profile
        res_b_create = self.client.post(
            "/api/student-profile",
            headers=self.headers_b,
            json={
                "degree": "B.Sc",
                "branch": "Math",
                "current_year": 1,
                "semester": 1,
                "career_goal": "Actuary",
            },
        )
        self.assertEqual(res_b_create.status_code, 201)

        # User B updates their profile
        res_b_update = self.client.put(
            "/api/student-profile",
            headers=self.headers_b,
            json={
                "full_name": "Bob The Builder",
                "degree": "B.Sc",
                "branch": "Applied Math",
                "current_year": 2,
                "semester": 3,
                "career_goal": "Data Analyst",
            },
        )
        self.assertEqual(res_b_update.status_code, 200)
        self.assertEqual(res_b_update.json()["full_name"], "Bob The Builder")

        # Verify User A's profile remains untouched
        res_a_get = self.client.get("/api/student-profile", headers=self.headers_a)
        self.assertEqual(res_a_get.status_code, 200)
        self.assertEqual(res_a_get.json()["full_name"], "Alice Wonder")
        self.assertEqual(res_a_get.json()["degree"], "M.Tech")

    def test_06_password_change_rejection_on_wrong_password(self):
        # Incorrect current password
        res = self.client.post(
            "/auth/change-password",
            headers=self.headers_a,
            json={
                "current_password": "WrongPassword999!",
                "new_password": self.password_new,
            },
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("incorrect", res.json()["detail"].lower())

        # Invalid new password (less than 8 chars)
        res_short = self.client.post(
            "/auth/change-password",
            headers=self.headers_a,
            json={
                "current_password": self.password_orig,
                "new_password": "short",
            },
        )
        self.assertEqual(res_short.status_code, 422)

    def test_07_password_change_success_and_login_verification(self):
        # Change password successfully
        res = self.client.post(
            "/auth/change-password",
            headers=self.headers_a,
            json={
                "current_password": self.password_orig,
                "new_password": self.password_new,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("message", res.json())

        # Verify old password no longer works
        old_login = self.client.post(
            "/auth/login",
            data={
                "username": self.email_a,
                "password": self.password_orig,
            },
        )
        self.assertEqual(old_login.status_code, 401)

        # Verify new password works
        new_login = self.client.post(
            "/auth/login",
            data={
                "username": self.email_a,
                "password": self.password_new,
            },
        )
        self.assertEqual(new_login.status_code, 200)
        self.assertIn("access_token", new_login.json())

    def test_08_database_transaction_rollback_handling(self):
        # Test change_password rollback on error
        user = (
            self.db.query(User).filter(User.email == self.email_a).first()
        )
        self.assertIsNotNone(user)

        # Calling change_password with wrong password returns False safely
        result = change_password(
            db=self.db,
            user=user,
            current_password="bad_password",
            new_password="anynewpassword123",
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
