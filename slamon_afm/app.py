import logging
from datetime import datetime, timedelta

import os
from flask import Flask

from sqlalchemy import event

from slamon_afm.models import db, Agent, Task
from slamon_afm.routes import agent_routes, bpms_routes, status_routes, dashboard_routes


def _log_level_from_str(log_level):
    try:
        return int(log_level)
    except ValueError:
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % log_level)
        return numeric_level


def _bool_from_str(value):
    if value.lower() in ['true', 'yes']:
        return True
    elif value.lower() in ['false', 'no']:
        return False
    raise ValueError('Invalid boolean value: %s' % value)


class DefaultConfig(object):
    """
    Container for default configuration values

    To simplify deployments using e.g. docker, each value is
    queried from the process environment variables before
    assigning the default value.
    """
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite://')
    AGENT_RETURN_TIME = int(os.getenv('AGENT_RETURN_TIME', 60))
    AGENT_ACTIVE_THRESHOLD = int(os.getenv('AGENT_ACTIVE_THRESHOLD', 300))
    AGENT_DROP_THRESHOLD = int(os.getenv('AGENT_DROP_THRESHOLD', 3600))
    AUTO_CREATE = _bool_from_str(os.getenv('AUTO_CREATE', 'True'))
    AUTO_CLEANUP = _bool_from_str(os.getenv('AUTO_CLEANUP', 'True'))
    LOG_FILE = os.getenv('LOG_FILE', None)
    LOG_LEVEL = _log_level_from_str(os.getenv('LOG_LEVEL', 'INFO'))
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message).120s')


def create_app(config=None, config_file=None):
    """
    Create AFM Flask application instance and init the database
    """

    # setup app & load configuration
    app = Flask(__name__)
    app.config.from_object(DefaultConfig)
    app.config.from_envvar('SLAMON_AFM_CFG', silent=True)
    if config_file:
        app.config.from_pyfile(config_file)
    if config:
        app.config.update(**config)

    # setup logging according to configuration
    app.logger_name = 'slamon_afm'
    handler = logging.FileHandler(app.config['LOG_FILE']) if app.config['LOG_FILE'] else logging.StreamHandler()
    handler.setLevel(app.config['LOG_LEVEL'])
    handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
    app.logger.setLevel(app.config['LOG_LEVEL'])
    app.logger.addHandler(handler)

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

    # register event listener to enable foreign_keys for SQLite databases
    def on_connect(conn, record):
        if db.engine.name == 'sqlite':
            conn.execute('pragma foreign_keys=ON')

    with app.app_context():
        event.listen(db.engine, 'connect', on_connect)

    return app
