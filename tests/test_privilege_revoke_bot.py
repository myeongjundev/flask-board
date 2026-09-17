"""권한 회수 봇의 허용목록 판정과 GELF 메시지 테스트."""
import json
import unittest
from unittest.mock import MagicMock, patch

import privilege_revoke_bot as bot


class PrivilegeRevokeBotTestCase(unittest.TestCase):
    def test_find_violations_excludes_allowlisted_admin(self):
        config = {
            "board": "http://example.invalid",
            "key": "test-key",
            "allowlist": ["allowed-admin"],
        }
        response = {
            "users": [
                {"username": "allowed-admin", "role": 2},
                {"username": "unexpected-admin", "role": 2},
            ]
        }
        with patch.object(bot, "get_json", return_value=response) as get_json:
            violations = bot.find_violations(config)

        self.assertEqual([user["username"] for user in violations], ["unexpected-admin"])
        get_json.assert_called_once_with(
            "http://example.invalid/api/admin/users?role=admin", key="test-key"
        )

    def test_send_gelf_contains_privilege_rule_and_user(self):
        config = {
            "gelf_host": "localhost",
            "gelf_port": 12201,
            "src_ip": "192.0.2.1",
            "student": "합성학생",
        }
        client = MagicMock()
        client.__enter__.return_value = client
        with patch.object(bot.socket, "socket", return_value=client):
            bot.send_gelf(
                config,
                {"username": "unexpected-admin", "role_granted_by": "apikey"},
            )

        payload, address = client.sendto.call_args.args
        message = json.loads(payload.decode("utf-8"))
        self.assertEqual(address, ("localhost", 12201))
        self.assertEqual(message["_rule"], "priv-unauthorized-admin")
        self.assertEqual(message["_user"], "unexpected-admin")


if __name__ == "__main__":
    unittest.main()
