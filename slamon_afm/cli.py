#!/usr/bin/env python
import argparse

import os.path

from slamon_afm.app import create_app
from slamon_afm.models import db


def main():
    parser = argparse.ArgumentParser(description='SLAMon Agent Fleet Manager')
    parser.add_argument('--database-uri', type=str, default=None,
                        help='Set the AFM database URI, defaults to in memory sqlite')
    parser.add_argument('--config', '-c', type=str, default=None,
                        help='Load AFM configuration from a file')

    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser('run', help='Run AFM',
                                       description='Run an instance of an Agent Fleet Manager '
                                                   'that listens to given host address')
    run_parser.add_argument('host', type=str, help='Host name or address e.g. localhost or 127.0.0.1')
    run_parser.add_argument('port', type=int, default=8080, nargs='?', help='Listening port, defaults to 8080')
    run_parser.set_defaults(func=run_afm)

    create_parser = subparsers.add_parser('create-tables', help='Create SQL tables',
                                          description='Create required database tables to PostgreSQL')
    create_parser.set_defaults(func=create)

    drop_parser = subparsers.add_parser('drop-tables', help='Drop SQL tables',
                                        description='Drop created database tables from PostgreSQL')
    drop_parser.set_defaults(func=drop)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        # No function defined, print usage and exit
        parser.print_help()
        exit(1)

    app = create_app(config_file=os.path.abspath(args.config) if args.config else None)

    if args.database_uri:
        # override the database URI
        app.config.update(SQLALCHEMY_DATABASE_URI=args.database_uri)

    args.func(app, args)


def run_afm(app, args):
    app.run(args.host, args.port)


def create(app, args):
    del args  # unused
    with app.app_context():
        db.create_all()


def drop(app, args):
    del args  # unused
    with app.app_context():
        db.drop_all()


if __name__ == '__main__':
    main()
