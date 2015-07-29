import unittest
import os

from webtest import TestApp

from slamon_afm.afm_app import app
from slamon_afm.database import init_connection
from slamon_afm.routes import status_routes  # Shows as unused but is actually required for routes


class TestStatusSQLProblem(unittest.TestCase):
    """
    TestCase that doesn't actually setup proper database connection to make sure that /status works as expected
    """
    def tearDown(self):
        if 'OPENSHIFT_POSTGRESQL_DB_URL' in os.environ:
            del os.environ['OPENSHIFT_POSTGRESQL_DB_URL']

    @staticmethod
    def test_status_broken_session():
        test_app = TestApp(app)
        os.environ['OPENSHIFT_POSTGRESQL_DB_URL'] = 'postgresql+psycopg2://slamon:slamon@localhost/whatever'
        init_connection()

        assert test_app.get('/status', expect_errors=True).status_int == 500
