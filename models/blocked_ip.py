from datetime import datetime

from extensions import db


class BlockedIP(db.Model):
    """애플리케이션 입구에서 거부할 IP 주소."""

    __tablename__ = "blocked_ips"

    ip = db.Column(db.String(45), primary_key=True)
    reason = db.Column(db.String(200))
    blocked_by = db.Column(db.String(80))
    blocked_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def to_dict(self):
        return {
            "ip": self.ip,
            "reason": self.reason,
            "blocked_by": self.blocked_by,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None,
        }
