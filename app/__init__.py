import os
from flask import Flask, render_template
from dotenv import load_dotenv
from app.extensions import db

load_dotenv()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-me"
    )

    os.makedirs(app.instance_path, exist_ok=True)

    default_db_path = "sqlite:///" + os.path.join(
        app.instance_path,
        "app.db"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        default_db_path
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.events import events_bp
    from app.routes.resources import resources_bp
    from app.routes.requests import requests_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(requests_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    # 404 error
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    # 500 error
    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return f"SERVER ERROR: {e}", 500

    return app