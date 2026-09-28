"""대시보드용 인시던트 티켓 조회 API 테스트 (강사님 test_dashboard_incidents.py 이식).

대시보드는 로그인·API 키 없이 여는 화면이라 /api/security/events 처럼
조회만 키 없이 열고, 생성·종료는 그대로 관리자 키를 요구한다.
"""
import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-at-least-32-bytes"
os.environ["SECURITY_API_KEY"] = "test-only-security-api-key"
os.environ["ADMIN_API_KEY"] = "test-only-admin-api-key"

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from test_security_response import TestConfig  # noqa: E402


class IncidentDashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.admin_headers = {"X-API-Key": TestConfig.ADMIN_API_KEY}
        self.security_headers = {"X-API-Key": TestConfig.SECURITY_API_KEY}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def seed(self, src_ip, severity="High"):
        """보안 이벤트 1건과 그 출발지의 인시던트 티켓 1건을 만든다."""
        response = self.client.post(
            "/api/security/events",
            headers=self.security_headers,
            json={
                "student": "lab", "src_ip": src_ip, "decision": "deny",
                "severity": severity, "reason": f"{severity} seed", "source": "ip-guard",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        response = self.client.post(
            "/api/admin/incident",
            headers=self.admin_headers,
            json={"src_ip": src_ip, "student": "lab"},
        )
        self.assertIn(response.status_code, (200, 201), response.get_data(as_text=True))
        return response.get_json()["incident"]

    def close(self, incident_id):
        response = self.client.post(
            "/api/admin/incident/close", headers=self.admin_headers, json={"id": incident_id}
        )
        self.assertEqual(response.status_code, 200)

    def test_list_incidents_without_api_key(self):
        incident = self.seed("203.0.113.1")

        response = self.client.get("/api/security/incidents")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["incidents"][0]["id"], incident["id"])
        self.assertEqual(body["incidents"][0]["src_ip"], "203.0.113.1")
        self.assertEqual(body["incidents"][0]["status"], "open")

    def test_list_is_newest_first_and_limited(self):
        for i in range(1, 4):
            self.seed(f"203.0.113.{10 + i}")

        body = self.client.get("/api/security/incidents?limit=2").get_json()
        self.assertEqual(body["count"], 2)
        ids = [row["id"] for row in body["incidents"]]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_status_and_student_filter(self):
        first = self.seed("203.0.113.21")
        self.seed("203.0.113.22")
        self.close(first["id"])

        opened = self.client.get("/api/security/incidents?status=open").get_json()
        closed = self.client.get("/api/security/incidents?status=closed").get_json()
        other = self.client.get("/api/security/incidents?student=nobody").get_json()
        self.assertEqual([row["src_ip"] for row in opened["incidents"]], ["203.0.113.22"])
        self.assertEqual([row["src_ip"] for row in closed["incidents"]], ["203.0.113.21"])
        self.assertEqual(other["count"], 0)

    def test_summary_counts_and_open_severity(self):
        critical = self.seed("203.0.113.31", "Critical")
        self.seed("203.0.113.32", "High")
        self.close(critical["id"])

        body = self.client.get("/api/security/incidents/summary").get_json()
        self.assertEqual(body["by_status"], {"open": 1, "closed": 1})
        # 심각도 분포는 열린 티켓만 센다.
        self.assertEqual(body["open_by_severity"], {"High": 1})

    def test_read_endpoint_does_not_open_writes(self):
        self.seed("203.0.113.41")
        self.assertIn(self.client.post("/api/security/incidents").status_code, (404, 405))
        self.assertEqual(
            self.client.post("/api/admin/incident", json={"src_ip": "203.0.113.41"}).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
