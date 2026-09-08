"""n8n 판정 결과를 저장하고 조회하는 보안 이벤트 API."""
import os
import secrets
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from extensions import db
from models import Post, SecurityEvent, User

security_bp = Blueprint("security", __name__, url_prefix="/api/security")


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("SECURITY_API_KEY", "")
        supplied = request.headers.get("X-API-Key", "")
        if not expected or not secrets.compare_digest(supplied, expected):
            return jsonify({"msg": "API 키가 없거나 잘못되었습니다."}), 401
        return fn(*args, **kwargs)
    return wrapper


def _optional_int(data, field, default=None):
    value = data.get(field, default)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}는 정수여야 합니다.") from exc


def _create_security_post(event):
    bot = User.query.filter_by(username="soarbot").first()
    if not bot:
        bot = User(
            username="soarbot",
            password=generate_password_hash(os.urandom(16).hex()),
        )
        db.session.add(bot)
        db.session.flush()
    post = Post(
        title=f"[보안][{event.student}] {event.src_ip} 접근 거부 ({event.severity})",
        content=(
            f"{event.reason or ''}\n시도 계정: {event.users or '-'}\n"
            f"마지막 시도: {event.last_seen or '-'}\n수집: {event.generated_at or '-'}"
        ),
        category="보안",
        author_id=bot.id,
    )
    db.session.add(post)
    db.session.flush()
    return post.id


@security_bp.post("/events")
@require_api_key
def create_security_event():
    data = request.get_json(silent=True) or {}
    student = str(data.get("student") or "").strip()
    src_ip = str(data.get("src_ip") or "").strip()
    decision = str(data.get("decision") or "").strip().lower()
    if not student or not src_ip or decision not in ("allow", "deny"):
        return jsonify({"msg": "student, src_ip, decision(allow|deny)은 필수입니다."}), 400
    try:
        fail_count = _optional_int(data, "fail_count", 0)
        window_min = _optional_int(data, "window_min")
    except ValueError as exc:
        return jsonify({"msg": str(exc)}), 400
    if fail_count < 0 or (window_min is not None and window_min < 0):
        return jsonify({"msg": "fail_count와 window_min은 음수일 수 없습니다."}), 400

    event = SecurityEvent(
        student=student[:50], src_ip=src_ip[:45], fail_count=fail_count,
        decision=decision, severity=str(data.get("severity") or "Low")[:10],
        reason=str(data.get("reason") or "")[:200] or None,
        users=str(data.get("users") or "")[:255] or None,
        last_seen=str(data.get("last_seen") or "")[:32] or None,
        window_min=window_min,
        source=str(data.get("source") or "login_guard")[:50],
        generated_at=str(data.get("generated_at") or "")[:32] or None,
    )
    db.session.add(event)
    db.session.flush()
    post_id = None
    if decision == "deny" and current_app.config.get("AUTO_POST_ON_DENY"):
        post_id = _create_security_post(event)
    db.session.commit()
    return jsonify({
        "id": event.id, "student": event.student,
        "decision": event.decision, "post_id": post_id,
    }), 201


@security_bp.get("/events")
def list_security_events():
    student = request.args.get("student", type=str)
    decision = request.args.get("decision", type=str)
    requested_limit = request.args.get("limit", default=20, type=int)
    limit = min(max(requested_limit if requested_limit is not None else 20, 1), 100)
    query = SecurityEvent.query
    if student:
        query = query.filter_by(student=student)
    if decision in ("allow", "deny"):
        query = query.filter_by(decision=decision)
    rows = query.order_by(SecurityEvent.id.desc()).limit(limit).all()
    return jsonify({"count": len(rows), "events": [row.to_dict() for row in rows]})


@security_bp.get("/events/summary")
def security_events_summary():
    student = request.args.get("student", type=str)
    counts = db.session.query(SecurityEvent.decision, func.count(SecurityEvent.id))
    top_ips = db.session.query(SecurityEvent.src_ip, func.sum(SecurityEvent.fail_count)).filter(
        SecurityEvent.decision == "deny"
    )
    if student:
        counts = counts.filter(SecurityEvent.student == student)
        top_ips = top_ips.filter(SecurityEvent.student == student)
    by_decision = dict(counts.group_by(SecurityEvent.decision).all())
    top = (
        top_ips.group_by(SecurityEvent.src_ip)
        .order_by(func.sum(SecurityEvent.fail_count).desc())
        .limit(5).all()
    )
    return jsonify({
        "student": student,
        "by_decision": by_decision,
        "top_deny_ips": [{"src_ip": ip, "fails": int(total)} for ip, total in top],
    })


@security_bp.get("/students")
def list_students():
    rows = db.session.query(SecurityEvent.student).distinct().order_by(SecurityEvent.student).all()
    return jsonify({"students": [row[0] for row in rows]})
