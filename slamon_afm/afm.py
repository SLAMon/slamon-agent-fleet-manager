#!/usr/bin/env python

import logging

from bottle import run

from slamon_afm import afm_app
from slamon_afm.settings import Settings
from slamon_afm.routes import agent_routes, bpms_routes, status_routes
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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if Settings.testing_urls_available:
        pass

    init_connection()
    run(afm_app.app, host='0.0.0.0', port=Settings.port, debug=True)
