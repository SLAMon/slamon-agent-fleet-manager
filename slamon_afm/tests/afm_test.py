from unittest import TestCase
import logging

from webtest import TestApp

from slamon_afm.app import create_app
from slamon_afm.models import db


# Log everything during tests
logging.basicConfig(level=logging.DEBUG)


class AFMTest(TestCase):
    AFM_CONFIG = {
        'SQLALCHEMY_DATABASE_URI': 'sqlite://'
    }

    def setUp(self):
        self.app = create_app(config=self.AFM_CONFIG)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.test_app = TestApp(self.app)

    def tearDown(self):
        db.drop_all()
        self.app_context.pop()
