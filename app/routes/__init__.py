from flask import Flask
from app.extensions import db
import os


def create_app():

    app = Flask(__name__)

    # -------------------------------------------------
    # Configuration
    # -------------------------------------------------

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-this"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///event_resource_allocation.db"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -------------------------------------------------
    # Initialize Database
    # -------------------------------------------------

    db.init_app(app)

    # -------------------------------------------------
    # Register Routes
    # -------------------------------------------------

    from app.routes.events import events_bp
    from app.routes.resources import resources_bp
    from app.routes.requests import requests_bp

    app.register_blueprint(events_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(requests_bp)

    # -------------------------------------------------
    # Create Database Tables
    # -------------------------------------------------

    with app.app_context():
        db.create_all()

    return app