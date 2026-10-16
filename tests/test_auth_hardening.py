import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth.security import hash_password, verify_password
from backend.core.rate_limit import rate_limiter
from backend.database.session import SessionLocal
from backend.main import app
from backend.models.user import User


class TestAuthHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        cls.test_email = "auth_hardening_test@campuscompass.org"
        cls.test_name = "Auth Hardening Tester"
        cls.test_password = "P" * 72

        cls._cleanup_user(cls.test_email)

        # Register valid base test user
        cls.client.post(
            "/auth/register",
            json={
                "full_name": cls.test_name,
                "email": cls.test_email,
                "password": cls.test_password,
            },
        )

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_user(cls.test_email)
        cls.db.close()
        rate_limiter.reset()

    @classmethod
    def _cleanup_user(cls, email: str):
        user = cls.db.query(User).filter(User.email == email).first()
        if user:
            cls.db.delete(user)
            cls.db.commit()

    def setUp(self):
        rate_limiter.reset()

    def tearDown(self):
        rate_limiter.reset()

    def test_01_security_helpers_72_byte_boundary(self):
        """Verify hash_password and verify_password enforce bcrypt 72-byte limit."""
        exact_72 = "A" * 72
        over_72 = "A" * 73

        # Exactly 72 bytes can be hashed and verified
        hashed = hash_password(exact_72)
        self.assertTrue(verify_password(exact_72, hashed))

        # Over 72 bytes raises ValueError in hash_password
        with self.assertRaises(ValueError):
            hash_password(over_72)

        # Over 72 bytes returns False in verify_password without crashing
        self.assertFalse(verify_password(over_72, hashed))

    def test_02_register_password_length_validation(self):
        """Registration rejects passwords exceeding 72 bytes with HTTP 422."""
        # 73-char password rejected by schema
        res = self.client.post(
            "/auth/register",
            json={
                "full_name": "Too Long Pass User",
                "email": "toolong_pass@campuscompass.org",
                "password": "P" * 73,
            },
        )
        self.assertEqual(res.status_code, 422)

        # 72-char password accepted
        email_72 = "pass72_user@campuscompass.org"
        self._cleanup_user(email_72)
        res_valid = self.client.post(
            "/auth/register",
            json={
                "full_name": "Pass 72 User",
                "email": email_72,
                "password": "P" * 72,
            },
        )
        self.assertEqual(res_valid.status_code, 201)
        self.assertEqual(res_valid.headers.get("X-RateLimit-Limit"), "25")
        self._cleanup_user(email_72)

    def test_03_login_oversized_password_graceful_rejection(self):
        """Login with >72 byte password returns 401 Unauthorized, never 500 error."""
        # Oversized password against existing user
        res = self.client.post(
            "/auth/login",
            data={
                "username": self.test_email,
                "password": "X" * 150,
            },
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json().get("detail"), "Invalid email or password")

        # Correct password succeeds and includes rate limit headers
        res_ok = self.client.post(
            "/auth/login",
            data={
                "username": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn("access_token", res_ok.json())
        self.assertEqual(res_ok.headers.get("X-RateLimit-Limit"), "30")

    def test_04_change_password_boundary_validation(self):
        """Change-password rejects new passwords over 72 bytes with HTTP 422."""
        # Use dedicated user so test 04 is self-contained
        chg_email = "change_pass_test@campuscompass.org"
        self._cleanup_user(chg_email)
        self.client.post(
            "/auth/register",
            json={
                "full_name": "Change Pass User",
                "email": chg_email,
                "password": "InitialPassword123!",
            },
        )

        login_res = self.client.post(
            "/auth/login",
            data={
                "username": chg_email,
                "password": "InitialPassword123!",
            },
        )
        token = login_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 73-char new_password rejected with 422
        res_oversized = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "InitialPassword123!",
                "new_password": "N" * 73,
            },
            headers=auth_headers,
        )
        self.assertEqual(res_oversized.status_code, 422)

        # 72-char new_password accepted
        res_valid = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "InitialPassword123!",
                "new_password": "N" * 72,
            },
            headers=auth_headers,
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(res_valid.headers.get("X-RateLimit-Limit"), "10")

        self._cleanup_user(chg_email)

    def test_05_login_ip_rate_limiting(self):
        """Verify login endpoint enforces 30 requests/minute IP rate limit."""
        # 1st request succeeds and reports remaining 29
        res_first = self.client.post(
            "/auth/login",
            data={
                "username": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(res_first.status_code, 200)
        self.assertEqual(res_first.headers.get("X-RateLimit-Limit"), "30")
        self.assertEqual(res_first.headers.get("X-RateLimit-Remaining"), "29")

        # Send remaining 29 requests to reach quota of 30
        for _ in range(29):
            res = self.client.post(
                "/auth/login",
                data={
                    "username": self.test_email,
                    "password": "wrong_password",
                },
            )
            self.assertEqual(res.status_code, 401)

        # 31st request triggers 429 Too Many Requests
        res_blocked = self.client.post(
            "/auth/login",
            data={
                "username": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(res_blocked.status_code, 429)
        self.assertIn("Retry-After", res_blocked.headers)
        self.assertEqual(res_blocked.headers.get("X-RateLimit-Limit"), "30")
        self.assertEqual(res_blocked.headers.get("X-RateLimit-Remaining"), "0")

    def test_06_register_ip_rate_limiting(self):
        """Verify register endpoint enforces 25 requests/minute IP rate limit."""
        # Send 25 requests
        for i in range(25):
            res = self.client.post(
                "/auth/register",
                json={
                    "full_name": f"Rate Limit User {i}",
                    "email": f"rl_probe_{i}@test.com",
                    "password": "ValidPassword123!",
                },
            )
            self.assertIn(res.status_code, [201, 400])
            self.assertEqual(res.headers.get("X-RateLimit-Limit"), "25")

        # 26th request triggers 429
        res_blocked = self.client.post(
            "/auth/register",
            json={
                "full_name": "Blocked User",
                "email": "rl_blocked@test.com",
                "password": "ValidPassword123!",
            },
        )
        self.assertEqual(res_blocked.status_code, 429)
        self.assertIn("Retry-After", res_blocked.headers)
        self.assertEqual(res_blocked.headers.get("X-RateLimit-Remaining"), "0")

        # Cleanup probe users
        for i in range(25):
            self._cleanup_user(f"rl_probe_{i}@test.com")


if __name__ == "__main__":
    unittest.main()
