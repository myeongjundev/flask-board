"""등급 기반 접근 제어(인가) 도구.

인증(로그인 여부)과 인가(등급 충족 여부)를 분리해서 다룬다.
 - 인증 실패 -> 401
 - 인증은 됐지만 등급 부족 -> 403
"""
from functools import wraps

from flask import g, jsonify, render_template
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError

from extensions import db
from models import ROLE_ADMIN, ROLE_GOLD, User, role_name


def load_current_user():
    """헤더 또는 쿠키의 토큰으로 현재 사용자를 찾는다. 없으면 None."""
    try:
        verify_jwt_in_request(optional=True)
    except (JWTExtendedException, PyJWTError):
        # 만료·위조·CSRF 불일치 토큰은 비로그인과 동일하게 취급한다.
        return None
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def current_user():
    """요청 한 번 안에서는 조회 결과를 재사용한다."""
    if "current_user" not in g:
        g.current_user = load_current_user()
    return g.current_user


def _denial(user, required_role):
    """거절 사유를 한 곳에서 만든다. (상태코드, 사유, 안내문)"""
    if user is None:
        return 401, "unauthenticated", "로그인이 필요한 페이지입니다."
    return (
        403,
        "insufficient_role",
        f"{role_name(required_role)} 등급 이상만 접근할 수 있습니다. "
        f"현재 등급은 {user.role_name}입니다.",
    )


def api_role_required(required_role):
    """JSON API용 등급 검사. 거절하면 JSON으로 사유를 돌려준다."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None or not user.has_role(required_role):
                status, reason, message = _denial(user, required_role)
                return (
                    jsonify(
                        {
                            "msg": message,
                            "reason": reason,
                            "required_role": required_role,
                            "required_role_name": role_name(required_role),
                            "current_role": user.role if user else None,
                        }
                    ),
                    status,
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator


def page_role_required(required_role):
    """페이지용 등급 검사. 거절하면 예외 화면을 그대로 렌더링한다."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None or not user.has_role(required_role):
                status, reason, message = _denial(user, required_role)
                return (
                    render_template(
                        "403.html",
                        status=status,
                        reason=reason,
                        message=message,
                        required_role=required_role,
                        required_role_name=role_name(required_role),
                        user=user,
                    ),
                    status,
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator


def gold_page_required(view):
    return page_role_required(ROLE_GOLD)(view)


def admin_page_required(view):
    return page_role_required(ROLE_ADMIN)(view)
