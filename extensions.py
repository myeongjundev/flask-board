"""순환 참조 없이 공유하는 Flask 확장 객체."""
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
jwt = JWTManager()
