from flask import Blueprint, render_template

from controllers.authz import admin_page_required, current_user, gold_page_required
from models import ROLE_ADMIN, ROLE_GOLD, ROLE_NAMES

page_bp = Blueprint("page", __name__)


@page_bp.app_context_processor
def inject_current_user():
    """모든 템플릿에서 로그인 사용자와 등급 상수를 쓸 수 있게 한다."""
    user = current_user()
    return {
        "current_user": user,
        "ROLE_GOLD": ROLE_GOLD,
        "ROLE_ADMIN": ROLE_ADMIN,
        "ROLE_NAMES": ROLE_NAMES,
    }


@page_bp.get("/")
def index():
    return render_template("index.html")


@page_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@page_bp.get("/gold")
@gold_page_required
def gold_lounge():
    """골드(1) 이상만 볼 수 있는 라운지."""
    return render_template("gold.html")


@page_bp.get("/admin")
@admin_page_required
def admin_console():
    """관리자(2)만 볼 수 있는 회원 관리 화면."""
    return render_template("admin.html")
