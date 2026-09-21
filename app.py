"""Flask 게시판 엔트리포인트."""
from flask import Flask, jsonify, request
from sqlalchemy import Integer, inspect, text

from config import Config
from controllers import all_blueprints
from extensions import db, jwt
from models import BlockedIP


def _client_ip():
    """랩 프록시 뒤에서 전달된 첫 IP를 사용하고, 없으면 직접 접속 IP를 쓴다."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or ""


def _ensure_user_security_schema():
    """기존 users 테이블에도 새 계정 잠금 컬럼을 한 번만 보강한다."""
    columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    additions = {
        "role_granted_by": (
            "ALTER TABLE users ADD COLUMN role_granted_by VARCHAR(80) NULL"
        ),
        "role_granted_at": (
            "ALTER TABLE users ADD COLUMN role_granted_at DATETIME NULL"
        ),
        "role_reason": (
            "ALTER TABLE users ADD COLUMN role_reason VARCHAR(200) NULL"
        ),
        "is_locked": (
            "ALTER TABLE users ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT 0"
        ),
        "locked_at": "ALTER TABLE users ADD COLUMN locked_at DATETIME NULL",
        "lock_reason": "ALTER TABLE users ADD COLUMN lock_reason VARCHAR(200) NULL",
        "failed_logins": (
            "ALTER TABLE users ADD COLUMN failed_logins INTEGER NOT NULL DEFAULT 0"
        ),
    }
    with db.engine.begin() as connection:
        for name, statement in additions.items():
            if name not in columns:
                connection.execute(text(statement))


def _ensure_user_role_schema():
    """이전 게시판의 문자열 등급을 현재 숫자 등급으로 한 번만 변환한다.

    예전 DB는 ``user/gold/admin``을 VARCHAR로 저장했지만 현재 애플리케이션은
    ``0/1/2`` 정수 등급을 사용한다. SQLAlchemy의 ``create_all``은 기존 컬럼의
    타입을 바꾸지 않으므로 시작 시 명시적으로 마이그레이션한다.
    """
    role_column = next(
        column
        for column in inspect(db.engine).get_columns("users")
        if column["name"] == "role"
    )
    if isinstance(role_column["type"], Integer):
        return

    if db.engine.dialect.name not in {"mysql", "mariadb"}:
        raise RuntimeError(
            "users.role이 숫자 컬럼이 아닙니다. DB 마이그레이션이 필요합니다."
        )

    with db.engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE users
                SET role = CASE LOWER(TRIM(CAST(role AS CHAR)))
                    WHEN 'admin' THEN '2'
                    WHEN 'gold' THEN '1'
                    WHEN 'user' THEN '0'
                    WHEN '2' THEN '2'
                    WHEN '1' THEN '1'
                    ELSE '0'
                END
                """
            )
        )
        connection.execute(
            text(
                "ALTER TABLE users "
                "MODIFY COLUMN role INTEGER NOT NULL DEFAULT 0"
            )
        )


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "DATABASE_URL이 없습니다. .env.example을 .env로 복사해 DB 접속값을 설정하세요."
        )
    if not app.config.get("JWT_SECRET_KEY"):
        raise RuntimeError(
            "JWT_SECRET_KEY가 없습니다. .env에 긴 랜덤 문자열을 설정하세요."
        )

    db.init_app(app)
    jwt.init_app(app)
    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)

    with app.app_context():
        db.create_all()
        _ensure_user_security_schema()
        _ensure_user_role_schema()

    @app.before_request
    def block_ip_guard():
        """차단 목록에 있는 IP의 일반 요청을 컨트롤러 실행 전에 거부한다."""
        # 복구가 불가능해지는 상황을 막기 위해 관리자 대응 API는 예외로 둔다.
        if request.path.startswith("/api/admin"):
            return None
        client_ip = _client_ip()
        if client_ip and db.session.get(BlockedIP, client_ip):
            return (
                jsonify(
                    {
                        "msg": "차단된 IP입니다. 관리자에게 문의하세요.",
                        "ip": client_ip,
                        "blocked": True,
                    }
                ),
                403,
            )
        return None

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
