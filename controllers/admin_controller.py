"""관리자 전용 회원 관리 API."""
from flask import Blueprint, jsonify, request

from controllers.authz import api_role_required, current_user
from extensions import db
from models import ROLE_ADMIN, VALID_ROLES, Post, User, role_name

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _admin_count(exclude_user_id=None):
    query = User.query.filter(User.role >= ROLE_ADMIN)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()


@admin_bp.get("/users")
@api_role_required(ROLE_ADMIN)
def list_users():
    """회원 목록을 등급 높은 순으로 불러온다."""
    users = User.query.order_by(User.role.desc(), User.id.asc()).all()
    post_counts = dict(
        db.session.query(Post.author_id, db.func.count(Post.id))
        .group_by(Post.author_id)
        .all()
    )
    me = current_user()
    return jsonify(
        {
            "users": [
                {
                    **user.to_dict(),
                    "post_count": post_counts.get(user.id, 0),
                    "is_me": user.id == me.id,
                }
                for user in users
            ],
            "roles": [
                {"value": value, "name": role_name(value)} for value in VALID_ROLES
            ],
            "me": me.to_dict(),
        }
    )


@admin_bp.patch("/users/<int:user_id>")
@api_role_required(ROLE_ADMIN)
def update_user(user_id):
    """회원 등급을 수정한다."""
    me = current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify({"msg": "존재하지 않는 회원입니다."}), 404

    data = request.get_json(silent=True) or {}
    if "role" not in data:
        return jsonify({"msg": "role 값이 필요합니다."}), 400
    try:
        new_role = int(data["role"])
    except (TypeError, ValueError):
        return jsonify({"msg": "role은 숫자여야 합니다."}), 400
    if new_role not in VALID_ROLES:
        return jsonify({"msg": f"role은 {list(VALID_ROLES)} 중 하나여야 합니다."}), 400

    # 스스로 강등해 관리자 화면에서 잠기는 사고를 막는다.
    if target.id == me.id and new_role < ROLE_ADMIN:
        return jsonify({"msg": "자기 자신의 등급은 내릴 수 없습니다."}), 400
    # 마지막 관리자가 사라지면 아무도 회원 관리를 할 수 없게 된다.
    if target.role >= ROLE_ADMIN and new_role < ROLE_ADMIN and _admin_count(target.id) == 0:
        return jsonify({"msg": "마지막 관리자는 강등할 수 없습니다."}), 400

    previous = target.role_name
    target.role = new_role
    db.session.commit()
    return jsonify(
        {
            "msg": f"{target.username}님의 등급을 {previous} → {target.role_name}(으)로 변경했습니다.",
            "user": target.to_dict(),
        }
    )


@admin_bp.delete("/users/<int:user_id>")
@api_role_required(ROLE_ADMIN)
def delete_user(user_id):
    """회원을 삭제한다. 남은 게시글도 함께 정리한다."""
    me = current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify({"msg": "존재하지 않는 회원입니다."}), 404
    if target.id == me.id:
        return jsonify({"msg": "자기 자신은 삭제할 수 없습니다."}), 400
    if target.role >= ROLE_ADMIN and _admin_count(target.id) == 0:
        return jsonify({"msg": "마지막 관리자는 삭제할 수 없습니다."}), 400

    # 게시글은 author_id 외래키로 묶여 있어 먼저 지워야 한다.
    removed_posts = Post.query.filter_by(author_id=target.id).delete()
    username = target.username
    db.session.delete(target)
    db.session.commit()
    return jsonify(
        {"msg": f"{username}님을 삭제했습니다. (게시글 {removed_posts}건 함께 삭제)"}
    )
