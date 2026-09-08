from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

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
    user = User(username=username[:80], password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "회원가입 성공"}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "아이디 또는 비밀번호가 잘못되었습니다."}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token, username=user.username)
