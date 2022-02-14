import os

from flask import Flask, render_template
from flask_session import Session

from config import SENTRY_DSN, SENTRY_SERVER_NAME

# set up sentry for error handling
if SENTRY_DSN != "":
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        server_name=SENTRY_SERVER_NAME,
    )


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.urandom(32)

    app.config.from_object(__name__)

    # read config.py file
    app.config.from_pyfile(os.path.join(".", "config.py"), silent=False)

    sess = Session()
    sess.init_app(app)

    from app import app as main_blueprint

    app.register_blueprint(main_blueprint)

    @app.errorhandler(400)
    def request_error(e):
        return render_template("error.html", error_type="400"), 400

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template("error.html", error_type="405"), 405

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error.html", error_type="404"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", error_type="500"), 500

    return app


create_app()
