from app.extensions import db
from app.models import Resource, ResourceRequest, RequestItem, RequestStatus, CAPACITY_TYPES


def booked_quantity(resource_id, start, end, exclude_request_id=None):
    """Total quantity of `resource_id` already reserved by Approved/Allocated
    requests whose time window overlaps [start, end)."""
    query = (
        db.session.query(db.func.coalesce(db.func.sum(RequestItem.quantity), 0))
        .join(ResourceRequest, RequestItem.request_id == ResourceRequest.id)
        .filter(RequestItem.resource_id == resource_id)
        .filter(ResourceRequest.status.in_(RequestStatus.RESERVING))
        .filter(ResourceRequest.start_time < end)
        .filter(ResourceRequest.end_time > start)
    )
    if exclude_request_id:
        query = query.filter(ResourceRequest.id != exclude_request_id)
    return query.scalar() or 0


def available_quantity(resource, start, end, exclude_request_id=None):
    used = booked_quantity(resource.id, start, end, exclude_request_id)
    return resource.total_quantity - used


def check_suitability(resource, event, required_type=None):
    """Returns a list of human-readable errors, empty if the resource is suitable."""
    errors = []
    if not resource.is_active:
        errors.append(f'"{resource.name}" is inactive and cannot be allocated.')
    if required_type and resource.type != required_type:
        errors.append(f'"{resource.name}" is a {resource.type}, but a {required_type} was required.')
    if resource.type in CAPACITY_TYPES and resource.capacity is not None:
        if resource.capacity < event.expected_attendance:
            errors.append(
                f'"{resource.name}" capacity ({resource.capacity}) is insufficient '
                f"for expected attendance ({event.expected_attendance})."
            )
    return errors


def find_alternatives(resource, needed_quantity, event, start, end, limit=3):
    """Suggests active resources of the same type that are suitable and available.

    Selection order: same type -> active -> meets capacity requirement (if applicable)
    -> has enough free quantity in the requested window -> smallest suitable capacity first
    (closest fit, avoids over-allocating a huge hall for a small event).
    """
    candidates = (
        Resource.query.filter(
            Resource.type == resource.type,
            Resource.is_active.is_(True),
            Resource.id != resource.id,
        )
        .order_by(Resource.capacity.asc().nullslast())
        .all()
    )

    suggestions = []
    for candidate in candidates:
        if candidate.type in CAPACITY_TYPES and candidate.capacity is not None:
            if candidate.capacity < event.expected_attendance:
                continue
        avail = available_quantity(candidate, start, end)
        if avail >= needed_quantity:
            suggestions.append({"resource": candidate, "available_quantity": avail})
        if len(suggestions) >= limit:
            break
    return suggestions


def validate_request_items(event, start, end, items, exclude_request_id=None):
    """Validates every requested line item together.

    items: list of dicts -> {resource_id, quantity, required_type (optional)}
    Returns (errors: list[str], suggestions: dict[resource_id -> list of alternatives])

    Nothing is written to the DB here — this is pure validation, which is what lets the
    caller guarantee "all resources succeed or none are allocated".
    """
    errors = []
    suggestions = {}

    if start is None or end is None or start >= end:
        errors.append("Invalid time range: end time must be after the start time.")
        return errors, suggestions

    if not items:
        errors.append("At least one resource must be requested.")
        return errors, suggestions

    for item in items:
        resource = Resource.query.get(item["resource_id"])
        quantity = item["quantity"]
        required_type = item.get("required_type")

        if not resource:
            errors.append(f"Selected resource (ID {item['resource_id']}) does not exist.")
            continue
        if quantity <= 0:
            errors.append(f'Quantity for "{resource.name}" must be at least 1.')
            continue

        suit_errors = check_suitability(resource, event, required_type)
        if suit_errors:
            errors.extend(suit_errors)
            suggestions[resource.id] = find_alternatives(resource, quantity, event, start, end)
            continue

        avail = available_quantity(resource, start, end, exclude_request_id)
        if avail < quantity:
            errors.append(
                f'"{resource.name}" is already booked for the requested time '
                f"(only {max(avail, 0)} of {resource.total_quantity} available)."
            )
            suggestions[resource.id] = find_alternatives(resource, quantity, event, start, end)

    return errors, suggestions
