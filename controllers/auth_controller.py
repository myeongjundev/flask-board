from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
)
from werkzeug.security import check_password_hash, generate_password_hash

from controllers.authz import current_user
from extensions import db
from models import ROLE_USER, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if not username or not password:
        return jsonify({"msg": "username, password는 필수입니다."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "이미 존재하는 사용자입니다."}), 400
    # 가입은 언제나 일반 등급으로 시작한다. 요청 본문의 role은 무시한다.
    user = User(
        username=username[:80],
        password=generate_password_hash(password),
        role=ROLE_USER,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "회원가입 성공", "role": user.role, "role_name": user.role_name}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "아이디 또는 비밀번호가 잘못되었습니다."}), 401
    token = create_access_token(identity=str(user.id))
    response = jsonify(
        access_token=token,
        username=user.username,
        role=user.role,
        role_name=user.role_name,
    )
    # 페이지 이동(GET)에서도 서버가 등급을 확인할 수 있도록 쿠키에도 실어 보낸다.
    set_access_cookies(response, token)
    return response


@auth_bp.post("/logout")
def logout():
    response = jsonify({"msg": "로그아웃되었습니다."})
    unset_jwt_cookies(response)
    return response


@auth_bp.get("/me")
def me():
    """현재 로그인 상태와 등급을 알려준다. 비로그인도 200으로 답한다."""
    user = current_user()
    if user is None:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user.to_dict()})
