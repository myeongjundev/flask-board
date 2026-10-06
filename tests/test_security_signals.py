"""강사님 2026-09-25 보안 신호·자기차단 수정 이식 테스트.

- 새 GELF 신호 4종: login-success, blocked-retry(S5), admin-auth-fail(S6), gold-access(S9)
- 자기차단: 올바른 API 키를 낸 SOAR 요청은 자기 IP가 차단돼도 통과
- 테스트 격리: GELF_ENABLED=False면 실습 Graylog로 아무것도 보내지 않음
"""
import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-at-least-32-bytes"
os.environ["SECURITY_API_KEY"] = "test-only-security-api-key"
os.environ["ADMIN_API_KEY"] = "test-only-admin-api-key"

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import ROLE_ADMIN, ROLE_GOLD, ROLE_USER, User  # noqa: E402
from test_security_response import TestConfig  # noqa: E402

# send_gelf를 이름으로 가져다 쓰는 모듈 전부. 하나라도 빠지면 그 신호는 못 잡는다.
GELF_USERS = (
    "app",
    "controllers.auth_controller",
    "controllers.page_controller",
    "controllers.security_controller",
    "controllers.admin_controller",
)
WRONG_KEY = "totally-wrong-key"


class SecuritySignalTestCase(unittest.TestCase):
    def setUp(self):
        self.sent = []

        def fake_send_gelf(short_message, rule, **fields):
            self.sent.append({"msg": short_message, "rule": rule, **fields})
            return True

        self.patches = ExitStack()
        for module in GELF_USERS:
            self.patches.enter_context(patch(f"{module}.send_gelf", fake_send_gelf))
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.admin_headers = {"X-API-Key": TestConfig.ADMIN_API_KEY}
        self.security_headers = {"X-API-Key": TestConfig.SECURITY_API_KEY}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.patches.close()

    # ---------- 도우미 ----------

    def rules(self):
        return [call["rule"] for call in self.sent]

    def signals(self, rule):
        return [call for call in self.sent if call["rule"] == rule]

    def sign_in_as(self, username, role, password="pw1234"):
        response = self.client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        with self.app.app_context():
            User.query.filter_by(username=username).first().role = role
            db.session.commit()
        response = self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["access_token"]

    def block_self(self):
        """테스트 클라이언트 주소(127.0.0.1)를 차단한다."""
        response = self.client.post(
            "/api/admin/block",
            headers=self.admin_headers,
            json={"ip": "127.0.0.1", "reason": "자기차단 재현"},
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.sent.clear()

    def post_event(self, headers):
        return self.client.post(
            "/api/security/events",
            headers=headers,
            json={
                "student": "lab", "src_ip": "203.0.113.77", "decision": "deny",
                "severity": "High", "reason": "wazuh alert", "source": "wazuh",
            },
        )

    # ---------- login-success ----------

    def test_successful_login_is_reported_without_secrets(self):
        token = self.sign_in_as("zz_ok", ROLE_USER, password="Aa!23456789")
        signal = self.signals("login-success")
        self.assertEqual(len(signal), 1, self.sent)
        self.assertEqual(signal[0]["username"], "zz_ok")
        self.assertEqual(signal[0]["src_ip"], "127.0.0.1")
        self.assertEqual(signal[0]["role"], "user")
        blob = repr(self.sent)
        self.assertNotIn("Aa!23456789", blob)
        self.assertNotIn(token, blob)

    def test_failed_login_is_not_reported_as_success(self):
        self.sign_in_as("zz_ok", ROLE_USER)
        self.sent.clear()
        response = self.client.post(
            "/api/auth/login", json={"username": "zz_ok", "password": "nope"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.rules(), ["login-bruteforce"])

    # ---------- blocked-retry (S5) ----------

    def test_blocked_retry_is_reported(self):
        self.block_self()
        self.assertEqual(self.client.get("/").status_code, 403)
        signal = self.signals("blocked-retry")
        self.assertEqual(len(signal), 1, self.sent)
        self.assertEqual(signal[0]["src_ip"], "127.0.0.1")
        self.assertEqual(signal[0]["path"], "/")

    # ---------- admin-auth-fail (S6) ----------

    def test_wrong_security_key_is_reported_without_key_value(self):
        self.assertEqual(self.post_event({"X-API-Key": WRONG_KEY}).status_code, 401)
        self.assertEqual(len(self.signals("admin-auth-fail")), 1, self.sent)
        self.assertNotIn(WRONG_KEY, repr(self.sent))

    def test_wrong_admin_key_is_reported(self):
        response = self.client.get("/api/admin/blocked", headers={"X-API-Key": WRONG_KEY})
        self.assertEqual(response.status_code, 401)
        signal = self.signals("admin-auth-fail")
        self.assertEqual(len(signal), 1, self.sent)
        self.assertEqual(signal[0]["path"], "/api/admin/blocked")
        self.assertNotIn(WRONG_KEY, repr(self.sent))

    def test_admin_screen_without_key_is_not_an_auth_attack(self):
        """관리자 화면은 쿠키로 들어오고 키를 보내지 않는다. 오탐이 나면 안 된다."""
        self.sign_in_as("boss", ROLE_ADMIN)
        self.sent.clear()
        self.assertEqual(self.client.get("/api/admin/blocked").status_code, 200)
        self.assertNotIn("admin-auth-fail", self.rules())

    def test_normal_traffic_emits_no_new_signal(self):
        self.client.get("/")
        self.client.get("/dashboard")
        self.client.get("/api/security/events")
        self.assertEqual(self.sent, [])

    # ---------- web-scan ----------

    def test_missing_paths_emit_scan_signals_with_client_ip(self):
        for path in ("/missing-scan-path-one", "/missing-scan-path-two"):
            response = self.client.get(
                path + "?token=do-not-log",
                headers={"X-Forwarded-For": "203.0.113.77, 127.0.0.1"},
            )
            self.assertEqual(response.status_code, 404)
        signals = self.signals("web-scan")
        self.assertEqual(len(signals), 2, self.sent)
        self.assertEqual(signals[0]["src_ip"], "203.0.113.77")
        self.assertEqual(signals[0]["path"], "/missing-scan-path-one")
        self.assertEqual(signals[0]["code"], 404)
        self.assertNotIn("do-not-log", repr(signals))

    def test_admin_api_404_does_not_emit_scan_signal(self):
        response = self.client.get("/api/admin/missing-scan-path")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("web-scan", self.rules())

    def test_blocked_scan_emits_retry_instead_of_scan_signal(self):
        self.block_self()
        response = self.client.get("/missing-scan-path")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.rules(), ["blocked-retry"])

    def test_scan_logging_failure_preserves_404_response(self):
        with patch("app.send_gelf", side_effect=OSError("Graylog unavailable")):
            with self.assertLogs(self.app.logger, level="WARNING"):
                response = self.client.get("/missing-scan-path")
        self.assertEqual(response.status_code, 404)

    # ---------- gold-access (S9) ----------

    def test_gold_and_admin_access_is_reported(self):
        for username, role, code in (("zz_gold", ROLE_GOLD, "gold"), ("zz_admin", ROLE_ADMIN, "admin")):
            with self.subTest(role=code):
                self.client = self.app.test_client()
                self.sign_in_as(username, role)
                self.sent.clear()
                self.assertEqual(self.client.get("/gold").status_code, 200)
                signal = self.signals("gold-access")
                self.assertEqual(len(signal), 1, self.sent)
                self.assertEqual(signal[0]["username"], username)
                self.assertEqual(signal[0]["role"], code)

    def test_denied_gold_access_is_not_reported(self):
        self.assertEqual(self.client.get("/gold").status_code, 401)
        self.sign_in_as("zz_user", ROLE_USER)
        self.sent.clear()
        self.assertEqual(self.client.get("/gold").status_code, 403)
        self.assertNotIn("gold-access", self.rules())

    # ---------- 자기차단 ----------

    def test_soar_can_record_events_even_when_own_ip_blocked(self):
        self.block_self()
        response = self.post_event(self.security_headers)
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        self.assertNotIn("blocked-retry", self.rules())

    def test_admin_key_also_passes_block(self):
        self.block_self()
        response = self.client.get("/api/security/students", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)

    def test_plain_request_from_blocked_ip_still_403(self):
        self.block_self()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.get_json()["blocked"])

    def test_wrong_key_does_not_bypass_block(self):
        self.block_self()
        self.assertEqual(self.post_event({"X-API-Key": WRONG_KEY}).status_code, 403)
        self.assertIn("blocked-retry", self.rules())

    def test_admin_api_still_exempt_for_recovery(self):
        self.block_self()
        self.assertEqual(self.client.get("/api/admin/blocked", headers=self.admin_headers).status_code, 200)
        response = self.client.post(
            "/api/admin/unblock", headers=self.admin_headers, json={"ip": "127.0.0.1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)


class GelfIsolationTestCase(unittest.TestCase):
    """GELF_ENABLED=False면 소켓을 열지 않는다(테스트가 실습 SIEM을 오염시키지 않음)."""

    def test_disabled_gelf_opens_no_socket(self):
        from controllers.gelf import send_gelf

        app = create_app(TestConfig)
        with patch("controllers.gelf.socket.socket") as socket_factory, app.app_context():
            self.assertFalse(send_gelf("test", rule="login-success"))
        socket_factory.assert_not_called()
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
