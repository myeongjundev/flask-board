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
