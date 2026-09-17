"""환경변수 기반 애플리케이션 설정."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "").strip()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "").strip()
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    # 페이지 접근 제어를 서버에서 하려면 브라우저 주소창 이동(GET)에도 토큰이
    # 실려야 한다. 그래서 헤더와 쿠키 두 곳을 모두 인정한다.
    # - 기존 fetch API 호출: Authorization 헤더 그대로 사용
    # - /gold, /admin 같은 페이지 이동: 쿠키로 서버가 직접 등급 확인
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_ACCESS_COOKIE_PATH = "/"
    # CSRF 보호는 켜 둔다. 쿠키로 온 토큰의 POST/PUT/PATCH/DELETE만 CSRF 토큰을
    # 요구하므로, GET 페이지와 헤더 토큰을 쓰는 기존 API에는 영향이 없다.
    JWT_COOKIE_CSRF_PROTECT = True
    # 로컬 http 개발에서는 0, https 배포에서는 1로 둔다.
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "0") == "1"
    JWT_COOKIE_SAMESITE = "Lax"
    SECURITY_API_KEY = os.environ.get("SECURITY_API_KEY", "").strip()
    # n8n/SOAR가 계정 잠금, IP 차단, 인시던트 API를 호출할 때 쓴다.
    # 별도 값을 두지 않으면 기존 보안 이벤트 API 키를 함께 사용한다.
    ADMIN_API_KEY = (
        os.environ.get("ADMIN_API_KEY", "").strip() or SECURITY_API_KEY
    )
    ADMIN_ALLOWLIST = [
        username.strip()
        for username in os.environ.get("ADMIN_ALLOWLIST", "").split(",")
        if username.strip()
    ]
    AUTO_POST_ON_DENY = os.environ.get("AUTO_POST_ON_DENY", "0") == "1"
    # 로그인 실패 같은 앱 계층 보안 이벤트를 Graylog GELF UDP 입력으로 보낸다.
    GELF_HOST = os.environ.get("GELF_HOST", "localhost").strip() or "localhost"
    GELF_PORT = int(os.environ.get("GELF_PORT", "12201"))
    PUBLIC_API_KEY = (
        os.environ.get("PUBLIC_API_KEY", "").strip()
        or os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
        or os.environ.get("TOURKEY", "").strip()
    )
    PUBLIC_API_URL = (
        "https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr"
    )
