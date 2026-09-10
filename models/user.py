"""사용자 모델과 등급(권한) 정의."""
from extensions import db


ROLE_USER = 0
ROLE_GOLD = 1
ROLE_ADMIN = 2

ROLE_NAMES = {
    ROLE_USER: "일반",
    ROLE_GOLD: "골드",
    ROLE_ADMIN: "관리자",
}

VALID_ROLES = tuple(ROLE_NAMES)


def role_name(role):
    """등급 숫자를 사람이 읽는 이름으로 바꾼다."""
    return ROLE_NAMES.get(role, "알 수 없음")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # 회원가입은 항상 일반(0)으로 시작하고, 승급은 관리자만 할 수 있다.
    role = db.Column(
        db.Integer, nullable=False, default=ROLE_USER, server_default="0"
    )

    @property
    def role_name(self):
        return role_name(self.role)

    def has_role(self, minimum_role):
        """요구 등급 이상이면 True. 등급은 숫자가 클수록 권한이 넓다."""
        return self.role >= minimum_role

    @property
    def is_admin(self):
        return self.role >= ROLE_ADMIN

    @property
    def is_gold(self):
        return self.role >= ROLE_GOLD

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "role_name": self.role_name,
        }
