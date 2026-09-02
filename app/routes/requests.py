from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.extensions import db
from app.models import (
    Event,
    Resource,
    ResourceRequest,
    RequestItem,
)
from app.services.availability import (
    available_quantity,
    find_alternatives,
)
from app.utils import parse_datetime


requests_bp = Blueprint(
    "requests",
    __name__,
    url_prefix="/requests"
)


# =========================================================
# LIST REQUESTS
# =========================================================

@requests_bp.route("/")
def list_requests():

    status_filter = request.args.get("status", "")

    query = ResourceRequest.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    requests_list = (
        query
        .order_by(ResourceRequest.id.desc())
        .all()
    )

    return render_template(
        "requests/list.html",
        requests=requests_list,
        current_status=status_filter
    )


# =========================================================
# NEW REQUEST
# =========================================================

@requests_bp.route("/new", methods=["GET", "POST"])
def new_request():

    # Only approved events can request resources
    events = (
        Event.query
        .filter_by(status="Approved")
        .order_by(Event.start_time)
        .all()
    )

    # Only active resources can be requested
    resources = (
        Resource.query
        .filter_by(is_active=True)
        .order_by(Resource.type, Resource.name)
        .all()
    )

    selected_event = None
    form_data = request.form if request.method == "POST" else {}
    suggestions = {}

    if request.method == "POST":

        errors = []

        # -------------------------------------------------
        # EVENT
        # -------------------------------------------------

        event_id = request.form.get("event_id", type=int)

        if not event_id:
            errors.append("Please select an event.")
        else:
            selected_event = db.session.get(Event, event_id)

            if not selected_event:
                errors.append("Selected event does not exist.")

            elif selected_event.status != "Approved":
                errors.append(
                    "Resources can only be requested for an approved event."
                )

        # -------------------------------------------------
        # DATE/TIME
        # -------------------------------------------------

        start_raw = request.form.get("start_time", "")
        end_raw = request.form.get("end_time", "")

        start_time = parse_datetime(start_raw)
        end_time = parse_datetime(end_raw)

        if not start_time or not end_time:
            errors.append(
                "Please enter a valid start and end date/time."
            )

        elif start_time >= end_time:
            errors.append(
                "End date/time must be after start date/time."
            )

        # -------------------------------------------------
        # RESOURCE DATA
        # -------------------------------------------------

        resource_ids = request.form.getlist("resource_id[]")
        quantities = request.form.getlist("quantity[]")

        if not resource_ids:
            errors.append(
                "Please select at least one resource."
            )

        if len(resource_ids) != len(quantities):
            errors.append(
                "Invalid resource request data."
            )

        selected_items = []

        for resource_id_raw, quantity_raw in zip(
            resource_ids,
            quantities
        ):

            # Skip completely empty rows
            if not resource_id_raw:
                continue

            try:
                resource_id = int(resource_id_raw)
            except ValueError:
                errors.append("Invalid resource selected.")
                continue

            try:
                quantity = int(quantity_raw)
            except ValueError:
                errors.append(
                    "Quantity must be a whole number."
                )
                continue

            if quantity <= 0:
                errors.append(
                    "Quantity must be at least 1."
                )
                continue

            resource = db.session.get(
                Resource,
                resource_id
            )

            if not resource:
                errors.append(
                    "Selected resource does not exist."
                )
                continue

            if not resource.is_active:
                errors.append(
                    f'"{resource.name}" is inactive and cannot be requested.'
                )
                continue

            selected_items.append({
                "resource": resource,
                "quantity": quantity
            })

        if not selected_items:
            errors.append(
                "Please select at least one valid resource."
            )

        # -------------------------------------------------
        # SUITABILITY + AVAILABILITY
        # -------------------------------------------------

        if (
            selected_event
            and start_time
            and end_time
            and start_time < end_time
        ):

            attendance = selected_event.expected_attendance

            for item in selected_items:

                resource = item["resource"]
                quantity = item["quantity"]

                # Capacity check
                if (
                    resource.capacity is not None
                    and attendance > resource.capacity
                ):

                    errors.append(
                        f'"{resource.name}" has capacity '
                        f'{resource.capacity}, but the event has '
                        f'{attendance} expected attendees.'
                    )

                    # Find alternatives
                    alternatives = find_alternatives(
                        resource,
                        start_time,
                        end_time,
                        attendance,
                        quantity
                    )

                    suggestions[resource.id] = alternatives

                    continue

                # Availability check
                available = available_quantity(
                    resource,
                    start_time,
                    end_time
                )

                if quantity > available:

                    errors.append(
                        f'"{resource.name}" has only '
                        f'{available} unit(s) available for this time.'
                    )

                    # Find alternatives
                    alternatives = find_alternatives(
                        resource,
                        start_time,
                        end_time,
                        attendance,
                        quantity
                    )

                    suggestions[resource.id] = alternatives

        # -------------------------------------------------
        # IF ERRORS, SHOW FORM AGAIN
        # -------------------------------------------------

        if errors:

            for error in errors:
                flash(error, "error")

            return render_template(
                "requests/new.html",
                events=events,
                resources=resources,
                selected_event=selected_event,
                form_data=form_data,
                suggestions=suggestions
            )

        # -------------------------------------------------
        # CREATE REQUEST ATOMICALLY
        # -------------------------------------------------

        try:

            resource_request = ResourceRequest(
                event_id=selected_event.id,
                start_time=start_time,
                end_time=end_time,
                status="Pending"
            )

            db.session.add(resource_request)

            # Get request ID
            db.session.flush()

            # Add all requested resources
            for item in selected_items:

                request_item = RequestItem(
                    request_id=resource_request.id,
                    resource_id=item["resource"].id,
                    quantity=item["quantity"]
                )

                db.session.add(request_item)

            # Commit everything together
            db.session.commit()

            flash(
                "Resource request submitted successfully.",
                "success"
            )

            return redirect(
                url_for("requests.list_requests")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to submit resource request. "
                "Please try again.",
                "error"
            )

            return render_template(
                "requests/new.html",
                events=events,
                resources=resources,
                selected_event=selected_event,
                form_data=form_data,
                suggestions=suggestions
            )

    # =====================================================
    # GET
    # =====================================================

    return render_template(
        "requests/new.html",
        events=events,
        resources=resources,
        selected_event=selected_event,
        form_data=form_data,
        suggestions=suggestions
    )


# =========================================================
# APPROVE REQUEST
# =========================================================

@requests_bp.route(
    "/<int:request_id>/approve",
    methods=["POST"]
)
def approve_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    if resource_request.status != "Pending":

        flash(
            "Only pending requests can be approved.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    # Final availability check
    for item in resource_request.items:

        available = available_quantity(
            item.resource,
            resource_request.start_time,
            resource_request.end_time
        )

        if item.quantity > available:

            flash(
                f'"{item.resource.name}" is no longer available.',
                "error"
            )

            return redirect(
                url_for("requests.list_requests")
            )

    resource_request.status = "Approved"

    db.session.commit()

    flash(
        "Resource request approved.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


# =========================================================
# REJECT REQUEST
# =========================================================

@requests_bp.route(
    "/<int:request_id>/reject",
    methods=["POST"]
)
def reject_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    if resource_request.status != "Pending":

        flash(
            "Only pending requests can be rejected.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    resource_request.status = "Rejected"

    db.session.commit()

    flash(
        "Resource request rejected.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


# =========================================================
# ALLOCATE REQUEST
# =========================================================

@requests_bp.route(
    "/<int:request_id>/allocate",
    methods=["POST"]
)
def allocate_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    if resource_request.status != "Approved":

        flash(
            "Only approved requests can be allocated.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    # Final availability check
    for item in resource_request.items:

        available = available_quantity(
            item.resource,
            resource_request.start_time,
            resource_request.end_time
        )

        if item.quantity > available:

            flash(
                f'"{item.resource.name}" is no longer available.',
                "error"
            )

            return redirect(
                url_for("requests.list_requests")
            )

    resource_request.status = "Allocated"

    db.session.commit()

    flash(
        "Resources allocated successfully.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


# =========================================================
# CANCEL REQUEST
# =========================================================

@requests_bp.route(
    "/<int:request_id>/cancel",
    methods=["POST"]
)
def cancel_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    if resource_request.status not in [
        "Pending",
        "Approved",
        "Allocated"
    ]:

        flash(
            "This request cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    resource_request.status = "Cancelled"

    db.session.commit()

    flash(
        "Request cancelled. Resources have been released.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


# =========================================================
# REQUEST DETAILS
# =========================================================

@requests_bp.route("/<int:request_id>")
def request_details(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    return render_template(
        "requests/details.html",
        resource_request=resource_request
    )