# College Event Resource Allocation System

A Flask + SQLAlchemy + SQLite application for managing college events and shared resources
(auditoriums, labs, projectors, microphones, cameras, computers), with conflict-free resource
allocation.

## Installation & Running

1. `python3 -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `SECRET_KEY`.
4. `python seed.py` — creates `instance/app.db` and loads sample resources/events.
5. `python run.py` — visit `[127.0.0.1](http://127.0.0.1:5000)`.

Tables are also auto-created on first run via `db.create_all()`, so `seed.py` is only needed
if you want sample data.

## Database Setup

SQLite is used with SQLAlchemy ORM (no manual migration tool like Alembic, to keep the setup
lightweight per the assignment's scope). Schema:

- **Event**: name, organizer, expected_attendance, start/end time, status.
- **Resource**: name, type, capacity (audience capacity, nullable), total_quantity (units of
  that resource available, e.g. 6 microphones), is_active.
- **ResourceRequest**: belongs to an Event, has its own start/end time and status
  (Pending/Approved/Allocated/Rejected/Cancelled).
- **RequestItem**: a line item — resource + quantity — belonging to a ResourceRequest.

## How Conflict Detection Works

Instead of one database row per physical unit, each `Resource` carries a `total_quantity`
(e.g. Auditorium = 1, Microphones = 6). For any resource, time window, and requested quantity,
the system sums the quantities already reserved by other requests **whose status is Approved or
Allocated** and whose time window overlaps (`existing.start < new.end AND new.start < existing.end`).
If `already_reserved + requested > total_quantity`, the request is rejected.

This single rule handles both cases from the spec: a unique auditorium (quantity 1) can never be
double-booked for overlapping times, while multi-unit resources like microphones can be partially
shared across multiple events as long as the total in use never exceeds stock.

Only `Approved`/`Allocated` requests reserve capacity — `Pending` requests don't block each other,
so an admin can review multiple competing requests before deciding. Every check is re-run
server-side at both Approve and Allocate time (not just at submission), so a conflict that appears
after submission is always caught before resources are actually locked in.

**Atomicity**: all resource line items in one request are validated together *before* anything is
written to the database. If any single item fails (unavailable, inactive, wrong type, insufficient
capacity), the entire request creation/approval/allocation is aborted and nothing partial is saved
— exactly the "auditorium + projector available, microphone unavailable → whole request fails" case
from the spec.

## How Alternative Resources Are Selected

When a requested resource fails suitability or availability, `find_alternatives()`:

1. Filters to resources of the **same type**.
2. Keeps only **active** resources.
3. For capacity-relevant types (Auditorium, Laboratory), requires `capacity >= event.expected_attendance`.
4. Checks the candidate has enough **free quantity** in the exact requested time window.
5. Orders results by capacity ascending (smallest suitable option first, to avoid over-allocating
   a 500-seat hall for a 50-person meeting) and returns up to 3 matches.

Suggestions are shown directly on the request form when validation fails, so the organizer can
resubmit with a working alternative immediately.

## Workflow

