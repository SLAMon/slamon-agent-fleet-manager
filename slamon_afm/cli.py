#!/usr/bin/env python
import argparse
import logging

from slamon_afm.app import create_app
from slamon_afm.models import db


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='SLAMon Agent Fleet Manager')
    parser.add_argument('--database-uri', type=str, default=None)

    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser('run', help='Run AFM',
                                       description='Run an instance of an Agent Fleet Manager '
                                                   'that listens to given host address')
    run_parser.add_argument('host', action='store', help='Host name or address e.g. localhost or 127.0.0.1')
    run_parser.add_argument('port', type=int, default=8080, help='Listening port')
    run_parser.set_defaults(func=run_afm)

    create_parser = subparsers.add_parser('create-tables', help='Create SQL tables',
                                          description='Create required database tables to PostgreSQL')
    create_parser.set_defaults(func=create)

    drop_parser = subparsers.add_parser('drop-tables', help='Drop SQL tables',
                                        description='Drop created database tables from PostgreSQL')
    drop_parser.set_defaults(func=drop)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        exit(1)

    app = create_app()

    if args.database_uri:
        app.config.update(SQLALCHEMY_DATABASE_URI=args.database_uri)

    args.func(app, args)


def run_afm(app, args):
    # with app.app_context():
    #    import slamon_afm.tables
    #    db.create_all()

    @app.before_first_request
    def create_database():
        db.create_all()

    app.run(args.host, args.port, debug=True)


def create(app, args):
    with app.app_context():
        db.create_all()


def drop(app, args):
    with app.app_context():
        db.drop_all()


if __name__ == '__main__':
    main()
