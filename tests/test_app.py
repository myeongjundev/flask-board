import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-at-least-32-bytes"
os.environ["SECURITY_API_KEY"] = "test-only-security-api-key"

from app import app as default_app, create_app  # noqa: E402
from extensions import db  # noqa: E402


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "test-only-jwt-secret-at-least-32-bytes"
    SECURITY_API_KEY = "test-only-security-api-key"
    AUTO_POST_ON_DENY = False
    PUBLIC_API_KEY = ""
    PUBLIC_API_URL = "https://example.invalid"


class BoardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_pages_and_legacy_travel_aliases_open(self):
        paths = ("/", "/dashboard", "/public-post", "/public-posts", "/busan-travel")
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_auth_and_post_flow_remains_available(self):
        created = self.client.post(
            "/api/auth/register", json={"username": "student", "password": "pw1234"}
        )
        self.assertEqual(created.status_code, 201)
        login = self.client.post(
            "/api/auth/login", json={"username": "student", "password": "pw1234"}
        )
        self.assertEqual(login.status_code, 200)
        token = login.get_json()["access_token"]
        post = self.client.post(
            "/api/posts",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "합성 제목", "content": "합성 내용"},
        )
        self.assertEqual(post.status_code, 201)
        posts = self.client.get("/api/posts").get_json()["posts"]
        self.assertEqual(posts[0]["title"], "합성 제목")

    def test_security_api_rejects_missing_or_wrong_key(self):
        payload = {"student": "학생", "src_ip": "192.0.2.1", "decision": "deny"}
        self.assertEqual(self.client.post("/api/security/events", json=payload).status_code, 401)
        response = self.client.post(
            "/api/security/events", headers={"X-API-Key": "wrong"}, json=payload
        )
        self.assertEqual(response.status_code, 401)

    def test_security_api_validates_and_stores_both_decisions(self):
        headers = {"X-API-Key": "test-only-security-api-key"}
        self.assertEqual(
            self.client.post("/api/security/events", headers=headers, json={}).status_code,
            400,
        )
        invalid = {
            "student": "학생", "src_ip": "192.0.2.1",
            "decision": "deny", "fail_count": "x",
        }
        self.assertEqual(
            self.client.post("/api/security/events", headers=headers, json=invalid).status_code,
            400,
        )
        for decision, severity in (("deny", "High"), ("allow", "Low")):
            response = self.client.post(
                "/api/security/events", headers=headers,
                json={
                    "student": "합성학생", "src_ip": "192.0.2.10",
                    "decision": decision, "severity": severity,
                    "fail_count": 2, "reason": "합성 판정 사유",
                },
            )
            self.assertEqual(response.status_code, 201)
            self.assertIn("id", response.get_json())
        events = self.client.get("/api/security/events?student=합성학생").get_json()
        self.assertEqual(events["count"], 2)
        self.assertEqual(self.client.get("/api/security/events?limit=잘못된값").status_code, 200)
        self.assertEqual(self.client.get("/api/posts?limit=잘못된값").status_code, 200)
        summary = self.client.get("/api/security/events/summary?student=합성학생").get_json()
        self.assertEqual(summary["by_decision"], {"allow": 1, "deny": 1})
        students = self.client.get("/api/security/students").get_json()["students"]
        self.assertEqual(students, ["합성학생"])


def tearDownModule():
    with default_app.app_context():
        db.session.remove()
        db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
