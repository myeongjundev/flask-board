from datetime import datetime

from extensions import db


class SecurityEvent(db.Model):
    __tablename__ = "security_events"
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(50), nullable=False, index=True)
    src_ip = db.Column(db.String(45), nullable=False, index=True)
    fail_count = db.Column(db.Integer, nullable=False, default=0)
    decision = db.Column(db.String(10), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="Low")
    reason = db.Column(db.String(200))
    users = db.Column(db.String(255))
    last_seen = db.Column(db.String(32))
    window_min = db.Column(db.Integer)
    source = db.Column(db.String(50), default="login_guard")
    generated_at = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id, "student": self.student, "src_ip": self.src_ip,
            "fail_count": self.fail_count, "decision": self.decision,
            "severity": self.severity, "reason": self.reason,
            "users": self.users, "last_seen": self.last_seen,
            "window_min": self.window_min, "source": self.source,
            "generated_at": self.generated_at,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
