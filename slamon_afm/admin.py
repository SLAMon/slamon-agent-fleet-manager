#!/usr/bin/env python

import logging
import argparse
import sys

from slamon_afm.tables import Agent, AgentCapability, Task
from slamon_afm.database import Base, engine, init_connection

logger = logging.getLogger('admin')


def create_tables():
    logger.info('Creating tables')
    Base.metadata.create_all(engine)


def drop_tables():
    logger.info('Dropping tables')
    Base.metadata.drop_all(engine)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Admin util for SLAMon Agent Fleet Manager')
    parser.add_argument('--create-tables', help='Create tables', action='store_true', default=False)
    parser.add_argument('--drop-tables', help='Drop all tables', action='store_true', default=False)

    init_connection(unittest=False)

    args = parser.parse_args()
    if args.create_tables is True:
        create_tables()
    elif args.drop_tables is True:
        drop_tables()
    else:
        parser.print_help()
        sys.exit(1)
