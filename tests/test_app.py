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

    def test_security_events_support_paging_search_and_source(self):
        headers = {"X-API-Key": "test-only-security-api-key"}
        rows = [
            ("192.0.2.1", "deny", "privilege-guard", "과잉권한 자동회수", "zz_rogue"),
            ("192.0.2.1", "deny", "login-guard", "계정 잠금", "zz_user"),
            ("192.0.2.2", "deny", "login-guard", "계정 잠금", "zz_other"),
            ("192.0.2.3", "allow", "login_alert_lab", "허용", ""),
        ]
        for ip, decision, source, reason, users in rows:
            response = self.client.post("/api/security/events", headers=headers, json={
                "student": "합성학생", "src_ip": ip, "decision": decision,
                "severity": "High", "fail_count": 1, "reason": reason,
                "users": users, "source": source,
            })
            self.assertEqual(response.status_code, 201)

        page = self.client.get("/api/security/events?limit=2&offset=2").get_json()
        self.assertEqual((page["total"], page["count"], page["offset"]), (4, 2, 2))
        # 최신순이라 둘째 쪽에는 두 번째·첫 번째로 넣은 이벤트가 온다.
        self.assertEqual([e["source"] for e in page["events"]], ["login-guard", "privilege-guard"])

        by_source = self.client.get("/api/security/events?source=login-guard").get_json()
        self.assertEqual(by_source["total"], 2)
        by_user = self.client.get("/api/security/events?q=zz_rogue").get_json()
        self.assertEqual([e["source"] for e in by_user["events"]], ["privilege-guard"])
        by_ip = self.client.get("/api/security/events?q=192.0.2.1&decision=deny").get_json()
        self.assertEqual(by_ip["total"], 2)

        summary = self.client.get("/api/security/events/summary").get_json()
        self.assertEqual(
            summary["by_source"],
            {"privilege-guard": 1, "login-guard": 2, "login_alert_lab": 1},
        )
        # 거부 건수가 많은 IP가 먼저 온다.
        self.assertEqual(summary["top_deny_ips"][0], {"src_ip": "192.0.2.1", "events": 2, "fails": 2})


def tearDownModule():
    with default_app.app_context():
        db.session.remove()
        db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
