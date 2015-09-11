from datetime import datetime

from slamon_afm.models import db, Task
from slamon_afm.tests.afm_test import AFMTest


class TestBMPSRoutes(AFMTest):
    def test_post_task(self):
        self.assertEqual(
            200,
            self.test_app.post_json('/task', {
                'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
                'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
                'task_type': 'wait',
                'task_version': 1,
                'task_data': {
                    'wait_time': 3600
                }
            }).status_int
        )

        task = db.session.query(Task).filter(Task.uuid == str('de305d54-75b4-431b-adb2-eb6b9e546013')).one()
        self.assertIsInstance(task.data, dict)
        self.assertEqual(task.data['wait_time'], 3600)

        # Test without data
        self.assertEqual(
            200,
            self.test_app.post_json('/task', {
                'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546014',
                'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
                'task_type': 'wait',
                'task_version': 1
            }).status_int
        )

    def test_post_task_invalid(self):
        assert self.test_app.post_json('/task', expect_errors=True).status_int == 400

        assert self.test_app.post_json('/task', {
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_type': 'wait',
            'task_version': 'invalid_version',
            'task_data': {
                'wait_time': 3600
            }
        }, expect_errors=True).status_int == 400

        assert self.test_app.post_json('/task', {
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013_not_valid',
            'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_type': 'wait',
            'task_version': 1,
            'task_data': {
                'wait_time': 3600
            }
        }, expect_errors=True).status_int == 400

        assert self.test_app.post_json('/task', {
            'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_type': 'wait',
            'task_version': 1,
            'task_data': {
                'wait_time': 3600
            }
        }, expect_errors=True).status_int == 400

    def test_post_task_duplicate(self):
        task1 = Task()
        task1.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546018'
        task1.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546018'
        task1.claimed = datetime.utcnow()
        task1.data = {'wait_time': 123}
        db.session.add(task1)
        db.session.commit()
        db.session.close()

        assert self.test_app.post_json('/task', {
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546018',
            'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_type': 'wait',
            'task_version': 1
        }, expect_errors=True).status_int == 400

    def test_pull_task(self):
        task1 = Task()
        task1.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546018'
        task1.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546018'
        task1.claimed = datetime.utcnow()
        task1.data = {'wait_time': 123}
        db.session.add(task1)

        task2 = Task()
        task2.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546019'
        task2.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546019'
        task2.claimed = datetime.utcnow()
        task2.completed = datetime.utcnow()
        task2.result_data = {'result': 'epic success'}
        db.session.add(task2)

        task3 = Task()
        task3.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546020'
        task3.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546020'
        task3.claimed = datetime.utcnow()
        task3.failed = datetime.utcnow()
        task3.error = 'unknown error'
        db.session.add(task3)

        db.session.commit()

        self.test_app.get('/task/de305d54-75b4-431b-adb2-eb6b9e546018')
        self.test_app.get('/task/de305d54-75b4-431b-adb2-eb6b9e546019')
        self.test_app.get('/task/de305d54-75b4-431b-adb2-eb6b9e546020')

    def test_pull_task_invalid(self):
        assert self.test_app.get('/task/de305d54-75b4-431b-adb2-eb6b9e546013', expect_errors=True).status_int == 404
