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
    AUTO_POST_ON_DENY = os.environ.get("AUTO_POST_ON_DENY", "0") == "1"
    PUBLIC_API_KEY = (
        os.environ.get("PUBLIC_API_KEY", "").strip()
        or os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
        or os.environ.get("TOURKEY", "").strip()
    )
    PUBLIC_API_URL = (
        "https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr"
    )
