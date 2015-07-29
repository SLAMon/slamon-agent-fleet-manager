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

