from flask import Flask

from slamon_afm.models import db
from slamon_afm.routes import agent_routes, bpms_routes, status_routes, dashboard_routes


class DefaultConfig(object):
    """
    Container for default configuration values
    """
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    AGENT_RETURN_TIME = 60
    AGENT_ACTIVE_THRESHOLD = 300
    AUTO_CREATE = True


def create_app(config=None, config_file=None):
    """
    Create AFM Flask application instance and init the database
    """

    # setup app & configuration
    app = Flask(__name__)
    app.config.from_object(DefaultConfig)
    app.config.from_envvar('SLAMON_AFM_CFG', silent=True)
    if config_file:
        app.config.from_pyfile(config_file)
    if config:
        app.config.update(**config)

    # register app routes
    app.register_blueprint(agent_routes.blueprint)
    app.register_blueprint(bpms_routes.blueprint)
    app.register_blueprint(status_routes.blueprint)
    app.register_blueprint(dashboard_routes.blueprint)

    # set to auto create tables before first request
    if app.config['AUTO_CREATE']:
        @app.before_first_request
        def create_database():
            db.create_all()

    # register app for Flask-SQLAlchemy DB
    db.init_app(app)

    return app
