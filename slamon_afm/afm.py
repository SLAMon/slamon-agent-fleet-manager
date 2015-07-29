#!/usr/bin/env python
import argparse
import logging

from bottle import run

from slamon_afm import afm_app
from slamon_afm.admin import create_tables, drop_tables
from slamon_afm.settings import Settings
from slamon_afm.routes import agent_routes, bpms_routes, status_routes
from slamon_afm.routes.testing import testing_routes
from slamon_afm.database import init_connection

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'tasks': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO',
        },
        'testing': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG'
        }
    }
}


def main():
    logging.basicConfig(level=logging.INFO)

    if Settings.testing_urls_available:
        pass

    parser = argparse.ArgumentParser(description='Admin util for SLAMon Agent Fleet Manager')
    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser('run', help='Run AFM', description='Run an instance of an Agent Fleet Manager '
                                                                          'that listens to given host address')
    run_parser.add_argument('host', help='Host name or address e.g. localhost or 127.0.0.1', action='store')
    run_parser.set_defaults(func=run_afm)

    create_parser = subparsers.add_parser('create-tables', help='Create SQL tables',
                                          description='Create required database tables to PostgreSQL')
    create_parser.set_defaults(func=create)

    drop_parser = subparsers.add_parser('drop-tables', help='Drop SQL tables',
                                        description='Drop created database tables from PostgreSQL')
    drop_parser.set_defaults(func=drop)

    init_connection(unittest=False)

    args = parser.parse_args()
    args.func(args)


def run_afm(args):
    run(afm_app.app, host=args.host, port=Settings.port, debug=True)


def create(args):
    create_tables()


def drop(args):
    drop_tables()

if __name__ == '__main__':
    main()
