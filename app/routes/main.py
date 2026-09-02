from datetime import datetime
from flask import Blueprint, render_template
from app.models import Event, Resource, ResourceRequest, EventStatus, RequestStatus

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    event_counts = {s: Event.query.filter_by(status=s).count() for s in EventStatus.ALL}
    upcoming_events = (
        Event.query.filter(Event.start_time >= datetime.utcnow(), Event.status.in_(["Pending", "Approved"]))
        .order_by(Event.start_time)
        .limit(5)
        .all()
    )
    pending_requests = (
        ResourceRequest.query.filter_by(status=RequestStatus.PENDING)
        .order_by(ResourceRequest.created_at.desc())
        .limit(5)
        .all()
    )
    total_resources = Resource.query.count()
    active_resources = Resource.query.filter_by(is_active=True).count()

    return render_template(
        "dashboard.html",
        event_counts=event_counts,
        upcoming_events=upcoming_events,
        pending_requests=pending_requests,
        total_resources=total_resources,
        active_resources=active_resources,
    )
