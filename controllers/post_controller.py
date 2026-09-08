from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Post

post_bp = Blueprint("post", __name__, url_prefix="/api/posts")


@post_bp.get("")
def get_posts():
    cursor = request.args.get("cursor", type=int)
    requested_limit = request.args.get("limit", default=5, type=int)
    limit = min(max(requested_limit if requested_limit is not None else 5, 1), 50)
    search = request.args.get("search", default="", type=str)
    category = request.args.get("category", default="", type=str)
    query = Post.query
    if category and category != "전체":
        query = query.filter(Post.category == category)
    if search:
        query = query.filter(
            (Post.title.like(f"%{search}%")) | (Post.content.like(f"%{search}%"))
        )
    if cursor:
        query = query.filter(Post.id < cursor)
    posts = query.order_by(Post.id.desc()).limit(limit + 1).all()
    has_more = len(posts) > limit
    posts = posts[:limit]
    return jsonify({
        "posts": [post.to_dict() for post in posts],
        "next_cursor": posts[-1].id if has_more else None,
        "has_more": has_more,
    })


@post_bp.post("")
@jwt_required()
def create_post():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("content"):
        return jsonify({"msg": "title, content는 필수입니다."}), 400
    post = Post(
        title=str(data["title"])[:200], content=str(data["content"]),
        category=str(data.get("category") or "일반")[:50], author_id=user_id,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"msg": "게시글이 등록되었습니다.", "id": post.id}), 201


@post_bp.put("/<int:post_id>")
@jwt_required()
def update_post(post_id):
    user_id = int(get_jwt_identity())
    post = db.get_or_404(Post, post_id)
    if post.author_id != user_id:
        return jsonify({"msg": "권한이 없습니다."}), 403
    data = request.get_json(silent=True) or {}
    post.title = str(data.get("title", post.title))[:200]
    post.content = str(data.get("content", post.content))
    post.category = str(data.get("category", post.category))[:50]
    db.session.commit()
    return jsonify({"msg": "수정되었습니다."})


@post_bp.delete("/<int:post_id>")
@jwt_required()
def delete_post(post_id):
    user_id = int(get_jwt_identity())
    post = db.get_or_404(Post, post_id)
    if post.author_id != user_id:
        return jsonify({"msg": "권한이 없습니다."}), 403
    db.session.delete(post)
    db.session.commit()
    return jsonify({"msg": "삭제되었습니다."})
