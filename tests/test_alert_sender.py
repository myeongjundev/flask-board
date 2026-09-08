import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

import requests

import alert_sender


class AlertSenderTestCase(unittest.TestCase):
    def test_payload_has_student_and_allow_deny_candidates(self):
        with patch.object(alert_sender, "STUDENT_NAME", "합성학생"):
            payload = alert_sender.build_payload()
        self.assertEqual(payload["student"], "합성학생")
        self.assertGreaterEqual(len(payload["alerts"]), 2)
        self.assertTrue(any(item["level"] >= 10 for item in payload["alerts"]))
        self.assertTrue(any(item["level"] < 10 for item in payload["alerts"]))

    def test_missing_configuration_exits_cleanly(self):
        with (
            patch.object(alert_sender, "N8N_WEBHOOK_URL", ""),
            patch.object(alert_sender, "STUDENT_NAME", ""),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(alert_sender.main(), 2)

    def test_network_failure_is_reported_without_traceback(self):
        stderr = io.StringIO()
        secret_url = "http://example.invalid/webhook/secret-path"
        with (
            patch.object(alert_sender, "N8N_WEBHOOK_URL", secret_url),
            patch.object(alert_sender, "STUDENT_NAME", "합성학생"),
            patch.object(
                alert_sender.requests,
                "post",
                side_effect=requests.ConnectionError(f"연결 실패: {secret_url}"),
            ),
            redirect_stdout(io.StringIO()),
            redirect_stderr(stderr),
        ):
            self.assertEqual(alert_sender.main(), 1)
        self.assertIn("전송 실패 (ConnectionError)", stderr.getvalue())
        self.assertNotIn(secret_url, stderr.getvalue())

    def test_success_reports_http_status(self):
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        with (
            patch.object(alert_sender, "N8N_WEBHOOK_URL", "http://example.invalid/webhook/test"),
            patch.object(alert_sender, "STUDENT_NAME", "합성학생"),
            patch.object(alert_sender.requests, "post", return_value=response),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(alert_sender.main(), 0)


if __name__ == "__main__":
    unittest.main()
