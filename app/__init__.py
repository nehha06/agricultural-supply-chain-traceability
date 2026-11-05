
import os
from flask import Flask
from app.database import initialize_database


def create_app():

    project_folder = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    app = Flask(
        __name__,
        template_folder=os.path.join(project_folder, "templates"),
        static_folder=os.path.join(project_folder, "static")
    )

    app.config["SECRET_KEY"] = "agritrace-development-secret-key"

    initialize_database()

    from app.routes import main
    app.register_blueprint(main)

    return app
