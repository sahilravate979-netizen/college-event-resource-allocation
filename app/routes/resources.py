



from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Resource, RESOURCE_TYPES, CAPACITY_TYPES
from app.services.availability import available_quantity
from app.utils import parse_datetime

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


def validate_resource_form(form):
    errors = []
    name = (form.get("name") or "").strip()
    rtype = (form.get("type") or "").strip()
    capacity_raw = (form.get("capacity") or "").strip()
    quantity_raw = (form.get("total_quantity") or "1").strip()

    if not name:
        errors.append("Resource name is required.")
    if not rtype:
        errors.append("Resource type is required.")

    capacity = None
    if capacity_raw:
        try:
            capacity = int(capacity_raw)
            if capacity <= 0:
                errors.append("Capacity must be a positive number.")
        except ValueError:
            errors.append("Capacity must be a whole number.")
    elif rtype in CAPACITY_TYPES:
        errors.append(f"Capacity is required for {rtype} resources.")

    quantity = 1
    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            errors.append("Total quantity must be at least 1.")
    except ValueError:
        errors.append("Total quantity must be a whole number.")

    data = {"name": name, "type": rtype, "capacity": capacity, "total_quantity": quantity}
    return errors, data


@resources_bp.route("/")
def list_resources():
    type_filter = request.args.get("type")
    active_filter = request.args.get("active")

    query = Resource.query
    if type_filter:
        query = query.filter_by(type=type_filter)
    if active_filter == "yes":
        query = query.filter_by(is_active=True)
    elif active_filter == "no":
        query = query.filter_by(is_active=False)

    resources = query.order_by(Resource.type, Resource.name).all()
    return render_template(
        "resources/list.html", resources=resources, types=RESOURCE_TYPES,
        current_type=type_filter, current_active=active_filter,
    )

@resources_bp.route("/availability")
def availability():
    resources = Resource.query.order_by(Resource.type, Resource.name).all()

    resource_id = request.args.get("resource_id", type=int)
    start_raw = request.args.get("start_time", "")
    end_raw = request.args.get("end_time", "")

    selected_resource = None
    available = None
    error = None

    if resource_id:
        selected_resource = Resource.query.get(resource_id)

        if not selected_resource:
            error = "Selected resource does not exist."
        else:
            start = parse_datetime(start_raw)
            end = parse_datetime(end_raw)

            if not start or not end:
                error = "Please enter a valid start and end date/time."
            elif start >= end:
                error = "End date/time must be after the start date/time."
            elif not selected_resource.is_active:
                available = 0
                error = "This resource is inactive and cannot be allocated."
            else:
                available = max(
                    0,
                    available_quantity(selected_resource, start, end)
                )

    return render_template(
        "resources/availability.html",
        resources=resources,
        selected_resource_id=resource_id,
        start_time=start_raw,
        end_time=end_raw,
        selected_resource=selected_resource,
        available=available,
        error=error,
    )



    
@resources_bp.route("/new", methods=["GET", "POST"])
def new_resource():
    if request.method == "POST":
        errors, data = validate_resource_form(request.form)
        if data["name"] and Resource.query.filter_by(name=data["name"]).first():
            errors.append("A resource with this name already exists.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "resources/form.html", resource=None, types=RESOURCE_TYPES,
                capacity_types=CAPACITY_TYPES, values=request.form,
            )
        resource = Resource(**data, is_active=True)
        db.session.add(resource)
        db.session.commit()
        flash("Resource added successfully.", "success")
        return redirect(url_for("resources.list_resources"))

    return render_template("resources/form.html", resource=None, types=RESOURCE_TYPES, capacity_types=CAPACITY_TYPES, values={})


@resources_bp.route("/<int:resource_id>/edit", methods=["GET", "POST"])
def edit_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if request.method == "POST":
        errors, data = validate_resource_form(request.form)
        duplicate = Resource.query.filter(Resource.name == data["name"], Resource.id != resource.id).first()
        if duplicate:
            errors.append("A resource with this name already exists.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "resources/form.html", resource=resource, types=RESOURCE_TYPES,
                capacity_types=CAPACITY_TYPES, values=request.form,
            )
        resource.name = data["name"]
        resource.type = data["type"]
        resource.capacity = data["capacity"]
        resource.total_quantity = data["total_quantity"]
        db.session.commit()
        flash("Resource updated successfully.", "success")
        return redirect(url_for("resources.list_resources"))

    values = {
        "name": resource.name, "type": resource.type,
        "capacity": resource.capacity or "", "total_quantity": resource.total_quantity,
    }
    return render_template("resources/form.html", resource=resource, types=RESOURCE_TYPES, capacity_types=CAPACITY_TYPES, values=values)


@resources_bp.route("/<int:resource_id>/toggle", methods=["POST"])
def toggle_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    resource.is_active = not resource.is_active
    db.session.commit()
    state = "activated" if resource.is_active else "deactivated"
    flash(f'"{resource.name}" has been {state}.', "success")
    return redirect(url_for("resources.list_resources"))
