from datetime import datetime
from app.extensions import db


class EventStatus:
    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"
    ALL = [DRAFT, PENDING, APPROVED, REJECTED, CANCELLED, COMPLETED]


class RequestStatus:
    PENDING = "Pending"
    APPROVED = "Approved"
    ALLOCATED = "Allocated"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    ALL = [PENDING, APPROVED, ALLOCATED, REJECTED, CANCELLED]
    # Statuses that actually consume/reserve resource capacity
    RESERVING = [APPROVED, ALLOCATED]


RESOURCE_TYPES = ["Auditorium", "Laboratory", "Projector", "Microphone", "Camera", "Computer"]
# Resource types where "capacity" means audience/seating capacity checked against event attendance
CAPACITY_TYPES = ["Auditorium", "Laboratory"]


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    organizer = db.Column(db.String(120), nullable=False)
    expected_attendance = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=EventStatus.DRAFT)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requests = db.relationship(
        "ResourceRequest", backref="event", cascade="all, delete-orphan", order_by="ResourceRequest.created_at.desc()"
    )


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)  # audience capacity, only meaningful for CAPACITY_TYPES
    total_quantity = db.Column(db.Integer, nullable=False, default=1)  # units available (e.g. 6 microphones)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResourceRequest(db.Model):
    __tablename__ = "resource_requests"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=RequestStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("RequestItem", backref="request", cascade="all, delete-orphan")


class RequestItem(db.Model):
    __tablename__ = "request_items"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("resource_requests.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    resource = db.relationship("Resource")
