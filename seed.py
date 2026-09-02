from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import Event, Resource, EventStatus

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    resources = [
        Resource(name="Main Auditorium", type="Auditorium", capacity=300, total_quantity=1, is_active=True),
        Resource(name="Seminar Hall B", type="Auditorium", capacity=120, total_quantity=1, is_active=True),
        Resource(name="Computer Lab 1", type="Laboratory", capacity=60, total_quantity=1, is_active=True),
        Resource(name="Projector", type="Projector", capacity=None, total_quantity=4, is_active=True),
        Resource(name="Wireless Microphone", type="Microphone", capacity=None, total_quantity=6, is_active=True),
        Resource(name="DSLR Camera", type="Camera", capacity=None, total_quantity=2, is_active=True),
        Resource(name="Laptop", type="Computer", capacity=None, total_quantity=10, is_active=True),
        Resource(name="Old Projector (Retired)", type="Projector", capacity=None, total_quantity=1, is_active=False),
    ]
    db.session.add_all(resources)

    now = datetime.utcnow()
    events = [
        Event(name="Technical Workshop", organizer="CS Department", expected_attendance=150,
              start_time=now + timedelta(days=19, hours=10), end_time=now + timedelta(days=19, hours=14),
              status=EventStatus.APPROVED),
        Event(name="Annual Cultural Fest", organizer="Student Council", expected_attendance=400,
              start_time=now + timedelta(days=30), end_time=now + timedelta(days=30, hours=6),
              status=EventStatus.PENDING),
        Event(name="Guest Lecture on AI", organizer="ECE Department", expected_attendance=80,
              start_time=now + timedelta(days=5, hours=11), end_time=now + timedelta(days=5, hours=13),
              status=EventStatus.DRAFT),
    ]
    db.session.add_all(events)
    db.session.commit()
    print("Database seeded successfully.")
