from webtest import TestApp

from slamon_afm.afm_app import app
from slamon_afm.tests.afm_test import AFMTest
from slamon_afm.routes import status_routes  # Shows as unused but is actually required for routes


class TestStatusValid(AFMTest):
    @staticmethod
    def test_status_ok():
        test_app = TestApp(app)

        result = test_app.get('/status').json

        assert 'agents' in result
        assert 'tasks_waiting' in result
