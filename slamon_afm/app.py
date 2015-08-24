from flask import Flask

from slamon_afm.models import db
from slamon_afm.routes import agent_routes, bpms_routes, status_routes, dashboard_routes


class DefaultConfig(object):
    """
    Container for default configuration values
    """
    AGENT_RETURN_TIME = 5
    AGENT_ACTIVE_THRESHOLD = 500
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


def create_app(config=None):
    """
    Create AFM Flask application instance and init the database
    """

    # setup app & configuration
    app = Flask(__name__)
    app.config.from_object(DefaultConfig)
    if config:
        print("Loading custom Config")
        app.config.update(**config)

    # register app routes
    app.register_blueprint(agent_routes.blueprint)
    app.register_blueprint(bpms_routes.blueprint)
    app.register_blueprint(status_routes.blueprint)
    app.register_blueprint(dashboard_routes.blueprint)

    # register app for Flask-SQLAlchemy DB
    db.init_app(app)

    return app
