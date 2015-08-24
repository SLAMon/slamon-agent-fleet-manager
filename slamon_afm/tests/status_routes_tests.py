from unittest import TestCase

from webtest import TestApp

from slamon_afm.tests.afm_test import AFMTest
from slamon_afm.app import create_app


class TestStatusValid(AFMTest):
    def test_status_ok(self):
        result = self.test_app.get('/status').json

        assert 'agents' in result
        assert 'tasks_waiting' in result


class TestStatusSQLProblem(TestCase):
    """
    TestCase that doesn't actually setup proper database connection to make sure that /status works as expected
    """

    AFM_CONFIG = {
        'SQLALCHEMY_DATABASE_URI': 'postgresql+psycopg2://invalid:invalid@127.0.01/inv'
    }

    def setUp(self):
        self.app = create_app(config=self.AFM_CONFIG)
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.test_app = TestApp(self.app)

    def tearDown(self):
        self.app_context.pop()

    def test_status_broken_session(self):
        response = self.test_app.get('/status', expect_errors=True)
        self.assertEqual(response.status_int, 500)
