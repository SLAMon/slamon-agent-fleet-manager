from unittest import TestCase
import logging

from webtest import TestApp

from slamon_afm.app import create_app, _bool_from_str, _log_level_from_str
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


class ConfigUtilTest(TestCase):
    def testOkTrueValues(self):
        for value in ('True', 'TRUE', 'true', 'Yes', 'yes', 'YES'):
            self.assertTrue(_bool_from_str(value))

    def testOkFalseValues(self):
        for value in ('False', 'FALSE', 'false', 'No', 'no', 'NO'):
            self.assertFalse(_bool_from_str(value))

    def testNokValues(self):
        for value in ('f', 't', '0', '1', 'nope', 'yep'):
            with self.assertRaises(ValueError):
                _bool_from_str(value)

    def testOkLogLevels(self):
        # known values (standard logging levels)
        for name, value in {'CRITICAL': logging.CRITICAL, 'Error': logging.ERROR, 'warning': logging.WARNING,
                            'INFO': logging.INFO, 'DEBUG': logging.DEBUG, 'NOTSET': logging.NOTSET}.items():
            self.assertEqual(value, _log_level_from_str(name))
        # explicit integer values
        for value in (-1, 0, 1, 50, 100):
            self.assertEqual(value, _log_level_from_str('{}'.format(value)))

    def testNokLogLevels(self):
        for value in ('f', 't', 'nope', 'yep'):
            with self.assertRaises(ValueError):
                _log_level_from_str(value)
