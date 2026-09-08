"""Flask 게시판 엔트리포인트."""
from flask import Flask

from config import Config
from controllers import all_blueprints
from extensions import db, jwt


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
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
