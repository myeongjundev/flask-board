"""강사님 최신 보안 대응 코드를 우리 숫자 등급 구조에 맞춘 통합 테스트."""
import os
import unittest
from unittest.mock import patch


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-at-least-32-bytes"
os.environ["SECURITY_API_KEY"] = "test-only-security-api-key"
os.environ["ADMIN_API_KEY"] = "test-only-admin-api-key"

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import ROLE_ADMIN, ROLE_USER, Incident, SecurityEvent, User  # noqa: E402


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "test-only-jwt-secret-at-least-32-bytes"
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    SECURITY_API_KEY = "test-only-security-api-key"
    ADMIN_API_KEY = "test-only-admin-api-key"
    ADMIN_ALLOWLIST = ["allowed-admin"]
    AUTO_POST_ON_DENY = False
    GELF_HOST = "localhost"
    GELF_PORT = 12201
    PUBLIC_API_KEY = ""
    PUBLIC_API_URL = "https://example.invalid"


class SecurityResponseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.admin_headers = {"X-API-Key": TestConfig.ADMIN_API_KEY}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def register(self, username="student"):
        response = self.client.post(
            "/api/auth/register", json={"username": username, "password": "pw1234"}
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))

    def test_failed_login_lock_and_unlock_flow(self):
        self.register()
        with patch("controllers.auth_controller.send_gelf") as send_gelf:
            for _ in range(2):
                response = self.client.post(
                    "/api/auth/login",
                    json={"username": "student", "password": "wrong"},
                )
                self.assertEqual(response.status_code, 401)
            self.assertEqual(send_gelf.call_count, 2)

        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username="student").first().failed_logins, 2)

        locked = self.client.post(
            "/api/admin/lock",
            headers=self.admin_headers,
            json={
                "username": "student",
                "src_ip": "192.0.2.10",
                "fail_count": 2,
                "reason": "합성 브루트포스 탐지",
            },
        )
        self.assertEqual(locked.status_code, 200)
        self.assertTrue(locked.get_json()["locked"])

        with patch("controllers.auth_controller.send_gelf") as send_gelf:
            response = self.client.post(
                "/api/auth/login",
                json={"username": "student", "password": "pw1234"},
            )
            self.assertEqual(response.status_code, 423)
            send_gelf.assert_called_once()

        unlocked = self.client.post(
            "/api/admin/unlock",
            headers=self.admin_headers,
            json={"username": "student"},
        )
        self.assertEqual(unlocked.status_code, 200)
        self.assertFalse(unlocked.get_json()["locked"])
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"username": "student", "password": "pw1234"},
            ).status_code,
            200,
        )

        with self.app.app_context():
            user = User.query.filter_by(username="student").first()
            self.assertFalse(user.is_locked)
            self.assertEqual(user.failed_logins, 0)
            self.assertEqual(SecurityEvent.query.count(), 1)

    def test_admin_api_key_is_fail_closed(self):
        self.register()
        payload = {"username": "student"}
        self.assertEqual(self.client.post("/api/admin/lock", json=payload).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/admin/lock", headers={"X-API-Key": "wrong"}, json=payload
            ).status_code,
            401,
        )

    def test_ip_block_guard_and_recovery_endpoint(self):
        blocked = self.client.post(
            "/api/admin/block",
            headers=self.admin_headers,
            json={"ip": "127.0.0.1", "reason": "합성 공격 IP"},
        )
        self.assertEqual(blocked.status_code, 200)
        self.assertTrue(blocked.get_json()["blocked"])

        denied = self.client.get("/")
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(denied.get_json()["blocked"])

        # 관리자 API는 차단 중에도 열어 두어 복구할 수 있어야 한다.
        listing = self.client.get("/api/admin/blocked", headers=self.admin_headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.get_json()["count"], 1)
        self.assertEqual(
            self.client.post(
                "/api/admin/unblock",
                headers=self.admin_headers,
                json={"ip": "127.0.0.1"},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_incident_lifecycle_collects_security_events(self):
        event = self.client.post(
            "/api/security/events",
            headers={"X-API-Key": TestConfig.SECURITY_API_KEY},
            json={
                "student": "합성학생",
                "src_ip": "192.0.2.55",
                "decision": "deny",
                "severity": "High",
                "fail_count": 5,
                "reason": "합성 로그인 실패",
            },
        )
        self.assertEqual(event.status_code, 201)

        created = self.client.post(
            "/api/admin/incident",
            headers=self.admin_headers,
            json={"src_ip": "192.0.2.55"},
        )
        self.assertEqual(created.status_code, 201)
        incident = created.get_json()["incident"]
        self.assertEqual(incident["event_count"], 1)
        self.assertIn("합성 로그인 실패", incident["summary"])

        listing = self.client.get(
            "/api/admin/incidents?status=open", headers=self.admin_headers
        ).get_json()
        self.assertEqual(listing["count"], 1)

        closed = self.client.post(
            "/api/admin/incident/close",
            headers=self.admin_headers,
            json={"id": incident["id"]},
        )
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.get_json()["incident"]["status"], "closed")

        with self.app.app_context():
            self.assertEqual(Incident.query.count(), 1)
            self.assertIsNotNone(Incident.query.first().closed_at)

    def test_privilege_grant_audit_and_revoke_flow(self):
        self.register("allowed-admin")
        self.register("unexpected-admin")

        granted = self.client.post(
            "/api/admin/grant",
            headers=self.admin_headers,
            json={
                "username": "unexpected-admin",
                "role": "admin",
                "reason": "합성 권한 부여",
            },
        )
        self.assertEqual(granted.status_code, 200)
        self.assertEqual(granted.get_json()["new_role"], ROLE_ADMIN)

        self.client.post(
            "/api/admin/grant",
            headers=self.admin_headers,
            json={"username": "allowed-admin", "role": ROLE_ADMIN},
        )
        admins = self.client.get(
            "/api/admin/users?role=admin", headers=self.admin_headers
        ).get_json()
        self.assertEqual(admins["count"], 2)

        violations = self.client.get(
            "/api/admin/violations", headers=self.admin_headers
        ).get_json()
        self.assertEqual(violations["count"], 1)
        self.assertEqual(
            violations["violations"][0]["username"], "unexpected-admin"
        )

        revoked = self.client.post(
            "/api/admin/revoke",
            headers=self.admin_headers,
            json={"username": "unexpected-admin", "student": "합성학생"},
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(revoked.get_json()["new_role"], ROLE_USER)

        with self.app.app_context():
            user = User.query.filter_by(username="unexpected-admin").first()
            self.assertEqual(user.role, ROLE_USER)
            self.assertEqual(user.role_granted_by, "apikey")
            event = SecurityEvent.query.filter_by(source="privilege-guard").one()
            self.assertEqual(event.users, "unexpected-admin")


if __name__ == "__main__":
    unittest.main()
