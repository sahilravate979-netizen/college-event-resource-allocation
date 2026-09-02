from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Event, EventStatus
from app.utils import parse_datetime

events_bp = Blueprint("events", __name__, url_prefix="/events")


def validate_event_form(form):
    errors = []
    name = (form.get("name") or "").strip()
    organizer = (form.get("organizer") or "").strip()
    attendance_raw = (form.get("expected_attendance") or "").strip()
    start = parse_datetime(form.get("start_time"))
    end = parse_datetime(form.get("end_time"))

    if not name:
        errors.append("Event name is required.")
    if not organizer:
        errors.append("Organizer is required.")

    attendance = None
    if not attendance_raw:
        errors.append("Expected attendance is required.")
    else:
        try:
            attendance = int(attendance_raw)
            if attendance <= 0:
                errors.append("Expected attendance must be a positive number.")
        except ValueError:
            errors.append("Expected attendance must be a whole number.")

    if start is None or end is None:
        errors.append("Start and end date/time are required and must be valid.")
    elif start >= end:
        errors.append("End date/time must be after the start date/time.")

    data = {
        "name": name, "organizer": organizer, "expected_attendance": attendance,
        "start_time": start, "end_time": end,
    }
    return errors, data


@events_bp.route("/")
def list_events():
    status = request.args.get("status")
    date_from = parse_datetime(request.args.get("date_from"), date_only=True)
    date_to = parse_datetime(request.args.get("date_to"), date_only=True)

    query = Event.query
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(Event.start_time >= date_from)
    if date_to:
        query = query.filter(Event.start_time <= date_to)

    events = query.order_by(Event.start_time.asc()).all()
    return render_template(
        "events/list.html", events=events, statuses=EventStatus.ALL, current_status=status,
        date_from=request.args.get("date_from", ""), date_to=request.args.get("date_to", ""),
    )


@events_bp.route("/new", methods=["GET", "POST"])
def new_event():
    if request.method == "POST":
        errors, data = validate_event_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("events/form.html", event=None, values=request.form)

        event = Event(
            name=data["name"], organizer=data["organizer"], expected_attendance=data["expected_attendance"],
            start_time=data["start_time"], end_time=data["end_time"], status=EventStatus.DRAFT,
        )
        db.session.add(event)
        db.session.commit()
        flash("Event created as a draft.", "success")
        return redirect(url_for("events.view_event", event_id=event.id))

    return render_template("events/form.html", event=None, values={})


@events_bp.route("/<int:event_id>")
def view_event(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template("events/details.html", event=event)


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status in (EventStatus.CANCELLED, EventStatus.COMPLETED):
        flash(f"A {event.status.lower()} event cannot be edited.", "error")
        return redirect(url_for("events.view_event", event_id=event.id))

    if request.method == "POST":
        errors, data = validate_event_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("events/form.html", event=event, values=request.form)

        event.name = data["name"]
        event.organizer = data["organizer"]
        event.expected_attendance = data["expected_attendance"]
        event.start_time = data["start_time"]
        event.end_time = data["end_time"]
        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("events.view_event", event_id=event.id))

    values = {
        "name": event.name, "organizer": event.organizer, "expected_attendance": event.expected_attendance,
        "start_time": event.start_time.strftime("%Y-%m-%dT%H:%M"), "end_time": event.end_time.strftime("%Y-%m-%dT%H:%M"),
    }
    return render_template("events/form.html", event=event, values=values)


@events_bp.route("/<int:event_id>/submit", methods=["POST"])
def submit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != EventStatus.DRAFT:
        flash("Only draft events can be submitted for approval.", "error")
    else:
        event.status = EventStatus.PENDING
        db.session.commit()
        flash("Event submitted for approval.", "success")
    return redirect(url_for("events.view_event", event_id=event.id))


@events_bp.route("/<int:event_id>/approve", methods=["POST"])
def approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != EventStatus.PENDING:
        flash("Only pending events can be approved.", "error")
    else:
        event.status = EventStatus.APPROVED
        db.session.commit()
        flash("Event approved. Resources can now be requested for it.", "success")
    return redirect(url_for("events.view_event", event_id=event.id))


@events_bp.route("/<int:event_id>/reject", methods=["POST"])
def reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != EventStatus.PENDING:
        flash("Only pending events can be rejected.", "error")
    else:
        event.status = EventStatus.REJECTED
        db.session.commit()
        flash("Event rejected.", "success")
    return redirect(url_for("events.view_event", event_id=event.id))


@events_bp.route("/<int:event_id>/complete", methods=["POST"])
def complete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != EventStatus.APPROVED:
        flash("Only approved events can be marked completed.", "error")
    elif event.end_time > datetime.utcnow():
        flash("Cannot mark an event completed before it has ended.", "error")
    else:
        event.status = EventStatus.COMPLETED
        db.session.commit()
        flash("Event marked as completed.", "success")
    return redirect(url_for("events.view_event", event_id=event.id))


@events_bp.route("/<int:event_id>/cancel", methods=["POST"])
def cancel_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status == EventStatus.COMPLETED:
        flash("A completed event cannot be cancelled.", "error")
        return redirect(url_for("events.view_event", event_id=event.id))

    event.status = EventStatus.CANCELLED
    for req in event.requests:
        if req.status in ("Pending", "Approved", "Allocated"):
            req.status = "Cancelled"
    db.session.commit()
    flash("Event cancelled. Any reserved resources have been released.", "success")
    return redirect(url_for("events.view_event", event_id=event.id))
