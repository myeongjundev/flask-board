from datetime import datetime

from extensions import db


class Incident(db.Model):
    """탐지 이벤트와 대응 내역을 묶어 추적하는 보안 인시던트."""

    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    src_ip = db.Column(db.String(45), index=True)
    severity = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(12), nullable=False, default="open", index=True)
    summary = db.Column(db.Text)
    event_count = db.Column(db.Integer, nullable=False, default=0)
    actions = db.Column(db.String(255))
    student = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    closed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "src_ip": self.src_ip,
            "severity": self.severity,
            "status": self.status,
            "summary": self.summary,
            "event_count": self.event_count,
            "actions": self.actions,
            "student": self.student,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
