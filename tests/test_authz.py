"""등급(0 일반 / 1 골드 / 2 관리자) 접근 제어 테스트."""
import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-at-least-32-bytes"
os.environ["SECURITY_API_KEY"] = "test-only-security-api-key"

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import ROLE_ADMIN, ROLE_GOLD, ROLE_USER, User  # noqa: E402


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
    AUTO_POST_ON_DENY = False
    PUBLIC_API_KEY = ""
    PUBLIC_API_URL = "https://example.invalid"


class RoleAccessTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    # ---------- 도우미 ----------

    def register(self, username, password="pw1234"):
        response = self.client.post(
            "/api/auth/register", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()

    def set_role(self, username, role):
        with self.app.app_context():
            user = User.query.filter_by(username=username).first()
            user.role = role
            db.session.commit()
            return user.id

    def login(self, username, password="pw1234", client=None):
        """로그인하면 해당 클라이언트에 쿠키가 심기고 헤더용 토큰을 돌려준다."""
        client = client or self.client
        response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["access_token"]

    def sign_in_as(self, username, role):
        """가입 → 등급 지정 → 로그인까지 한 번에. (user_id, token) 반환."""
        self.register(username)
        user_id = self.set_role(username, role)
        return user_id, self.login(username)

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    # ---------- 4) 가입 등급 / 인가 값 ----------

    def test_register_always_starts_as_normal_user(self):
        body = self.register("newbie")
        self.assertEqual(body["role"], ROLE_USER)
        self.assertEqual(body["role_name"], "일반")

    def test_register_ignores_role_sent_by_client(self):
        response = self.client.post(
            "/api/auth/register",
            json={"username": "sneaky", "password": "pw1234", "role": ROLE_ADMIN},
        )
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username="sneaky").first().role, ROLE_USER)

    def test_me_reports_role(self):
        self.sign_in_as("gold_user", ROLE_GOLD)
        body = self.client.get("/api/auth/me").get_json()
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["user"]["role"], ROLE_GOLD)
        self.assertEqual(body["user"]["role_name"], "골드")

    def test_me_allows_anonymous(self):
        body = self.client.get("/api/auth/me").get_json()
        self.assertFalse(body["authenticated"])
        self.assertIsNone(body["user"])

    # ---------- 6) 페이지 접근 제어와 예외 화면 ----------

    def test_anonymous_is_blocked_with_401_exception_page(self):
        for path in ("/gold", "/admin"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            html = response.get_data(as_text=True)
            self.assertIn("로그인이 필요합니다", html)

    def test_normal_user_is_blocked_from_gold_and_admin(self):
        self.sign_in_as("normal", ROLE_USER)
        for path in ("/gold", "/admin"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403, path)
            html = response.get_data(as_text=True)
            self.assertIn("접근 권한이 없습니다", html)
            self.assertIn("현재 등급은 일반입니다", html)

    def test_gold_user_opens_gold_but_not_admin(self):
        self.sign_in_as("gold", ROLE_GOLD)
        self.assertEqual(self.client.get("/gold").status_code, 200)
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 403)
        self.assertIn("관리자 등급 이상만", response.get_data(as_text=True))

    def test_admin_opens_every_role_page(self):
        self.sign_in_as("boss", ROLE_ADMIN)
        self.assertEqual(self.client.get("/gold").status_code, 200)
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_public_pages_stay_open_to_everyone(self):
        for path in ("/", "/dashboard", "/public-post"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    # ---------- 1) 헤더 링크 노출 ----------

    def test_nav_shows_role_links_only_to_qualified_users(self):
        anonymous_html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('href="/gold"', anonymous_html)
        self.assertNotIn('href="/admin"', anonymous_html)

        self.sign_in_as("gold", ROLE_GOLD)
        gold_html = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/gold"', gold_html)
        self.assertNotIn('href="/admin"', gold_html)

        admin_client = self.app.test_client()
        self.register("boss")
        self.set_role("boss", ROLE_ADMIN)
        self.login("boss", client=admin_client)
        admin_html = admin_client.get("/").get_data(as_text=True)
        self.assertIn('href="/gold"', admin_html)
        self.assertIn('href="/admin"', admin_html)

    def test_header_shows_username_and_role_on_every_page(self):
        """제출 증거용: 헤더에 로그인 유저명과 권한이 함께 찍히는지 확인한다."""
        cases = (
            ("normal", ROLE_USER, "일반 (0)", ("/",)),
            ("gold", ROLE_GOLD, "골드 (1)", ("/", "/gold")),
            ("boss", ROLE_ADMIN, "관리자 (2)", ("/", "/gold", "/admin")),
        )
        for username, role, label, paths in cases:
            client = self.app.test_client()
            self.register(username)
            self.set_role(username, role)
            self.login(username, client=client)
            for path in paths:
                html = client.get(path).get_data(as_text=True)
                self.assertIn(username, html, f"{username} @ {path}")
                self.assertIn(label, html, f"{username} @ {path}")

    def test_header_shows_login_buttons_when_signed_out(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('onclick="openAuthModal(false)"', html)
        self.assertNotIn('onclick="navLogout()"', html)
        self.assertIn("window.CURRENT_USER = null", html)

    def test_hidden_link_is_not_the_actual_guard(self):
        """링크가 안 보여도 URL을 직접 치면 서버가 막는지 확인한다."""
        self.sign_in_as("normal", ROLE_USER)
        self.assertEqual(self.client.get("/admin").status_code, 403)

    # ---------- 5) 관리자 회원 관리 API ----------

    def test_admin_api_rejects_anonymous_and_non_admin(self):
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)

        _, token = self.sign_in_as("normal", ROLE_USER)
        response = self.client.get("/api/admin/users", headers=self.bearer(token))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["reason"], "insufficient_role")

        _, gold_token = self.sign_in_as("gold", ROLE_GOLD)
        self.assertEqual(
            self.client.get("/api/admin/users", headers=self.bearer(gold_token)).status_code,
            403,
        )

    def test_admin_lists_users_with_roles(self):
        self.register("normal")
        self.register("gold")
        self.set_role("gold", ROLE_GOLD)
        _, token = self.sign_in_as("boss", ROLE_ADMIN)

        body = self.client.get("/api/admin/users", headers=self.bearer(token)).get_json()
        by_name = {user["username"]: user for user in body["users"]}
        self.assertEqual(by_name["normal"]["role"], ROLE_USER)
        self.assertEqual(by_name["gold"]["role_name"], "골드")
        self.assertTrue(by_name["boss"]["is_me"])
        self.assertEqual(len(body["roles"]), 3)

    def test_admin_can_change_role(self):
        self.register("normal")
        _, token = self.sign_in_as("boss", ROLE_ADMIN)
        target_id = self.set_role("normal", ROLE_USER)

        response = self.client.patch(
            f"/api/admin/users/{target_id}",
            headers=self.bearer(token),
            json={"role": ROLE_GOLD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["role"], ROLE_GOLD)

        with self.app.app_context():
            self.assertEqual(db.session.get(User, target_id).role, ROLE_GOLD)

    def test_promoted_user_gains_page_access(self):
        """승급 전 403 → 승급 후 200 으로 바뀌는지 끝까지 확인한다."""
        member = self.app.test_client()
        self.register("member")
        self.login("member", client=member)
        self.assertEqual(member.get("/gold").status_code, 403)

        _, token = self.sign_in_as("boss", ROLE_ADMIN)
        with self.app.app_context():
            member_id = User.query.filter_by(username="member").first().id
        self.client.patch(
            f"/api/admin/users/{member_id}",
            headers=self.bearer(token),
            json={"role": ROLE_GOLD},
        )
        self.assertEqual(member.get("/gold").status_code, 200)

    def test_admin_rejects_invalid_role_values(self):
        self.register("normal")
        _, token = self.sign_in_as("boss", ROLE_ADMIN)
        target_id = self.set_role("normal", ROLE_USER)

        for payload in ({"role": 9}, {"role": "gold"}, {}):
            response = self.client.patch(
                f"/api/admin/users/{target_id}", headers=self.bearer(token), json=payload
            )
            self.assertEqual(response.status_code, 400, payload)

    def test_admin_cannot_demote_self_or_last_admin(self):
        admin_id, token = self.sign_in_as("boss", ROLE_ADMIN)
        response = self.client.patch(
            f"/api/admin/users/{admin_id}",
            headers=self.bearer(token),
            json={"role": ROLE_USER},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("자기 자신", response.get_json()["msg"])

    def test_admin_can_delete_user_and_their_posts(self):
        self.register("victim")
        victim_token = self.login("victim")
        self.client.post(
            "/api/posts",
            headers=self.bearer(victim_token),
            json={"title": "합성 글", "content": "합성 내용"},
        )
        with self.app.app_context():
            victim_id = User.query.filter_by(username="victim").first().id

        _, token = self.sign_in_as("boss", ROLE_ADMIN)
        response = self.client.delete(
            f"/api/admin/users/{victim_id}", headers=self.bearer(token)
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertIn("게시글 1건", response.get_json()["msg"])

        with self.app.app_context():
            self.assertIsNone(db.session.get(User, victim_id))
        self.assertEqual(self.client.get("/api/posts").get_json()["posts"], [])

    def test_admin_cannot_delete_self_or_last_admin(self):
        admin_id, token = self.sign_in_as("boss", ROLE_ADMIN)
        response = self.client.delete(
            f"/api/admin/users/{admin_id}", headers=self.bearer(token)
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("자기 자신", response.get_json()["msg"])

    def test_admin_delete_missing_user_returns_404(self):
        _, token = self.sign_in_as("boss", ROLE_ADMIN)
        self.assertEqual(
            self.client.delete("/api/admin/users/9999", headers=self.bearer(token)).status_code,
            404,
        )

    # ---------- 게시글 관리자 삭제 ----------

    def _write_post(self, username, title="합성 제목"):
        token = self.login(username, client=self.app.test_client())
        response = self.client.post(
            "/api/posts",
            headers=self.bearer(token),
            json={"title": title, "content": "합성 내용"},
        )
        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        return response.get_json()["id"]

    def test_admin_can_delete_someone_elses_post(self):
        self.register("writer")
        post_id = self._write_post("writer")

        _, admin_token = self.sign_in_as("boss", ROLE_ADMIN)
        response = self.client.delete(
            f"/api/posts/{post_id}", headers=self.bearer(admin_token)
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        body = response.get_json()
        self.assertTrue(body["moderated"])
        self.assertIn("writer", body["msg"])
        self.assertEqual(self.client.get("/api/posts").get_json()["posts"], [])

    def test_owner_delete_is_not_marked_as_moderation(self):
        self.register("writer")
        post_id = self._write_post("writer")
        own_token = self.login("writer")

        body = self.client.delete(
            f"/api/posts/{post_id}", headers=self.bearer(own_token)
        ).get_json()
        self.assertFalse(body["moderated"])

    def test_gold_and_normal_cannot_delete_others_post(self):
        self.register("writer")
        post_id = self._write_post("writer")

        for username, role in (("normal", ROLE_USER), ("gold", ROLE_GOLD)):
            _, token = self.sign_in_as(username, role)
            response = self.client.delete(
                f"/api/posts/{post_id}", headers=self.bearer(token)
            )
            self.assertEqual(response.status_code, 403, username)

        # 거절당한 뒤에도 글은 그대로 남아 있어야 한다.
        self.assertEqual(len(self.client.get("/api/posts").get_json()["posts"]), 1)

    def test_admin_still_cannot_edit_someone_elses_post(self):
        """삭제만 열어 준다. 남의 글 내용을 고치는 건 여전히 막는다."""
        self.register("writer")
        post_id = self._write_post("writer")

        _, admin_token = self.sign_in_as("boss", ROLE_ADMIN)
        response = self.client.put(
            f"/api/posts/{post_id}",
            headers=self.bearer(admin_token),
            json={"title": "관리자가 고친 제목"},
        )
        self.assertEqual(response.status_code, 403)

    # ---------- 로그아웃 ----------

    def test_logout_closes_page_access(self):
        self.sign_in_as("boss", ROLE_ADMIN)
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/admin").status_code, 401)


if __name__ == "__main__":
    unittest.main()
