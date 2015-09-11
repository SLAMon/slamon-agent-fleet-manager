from datetime import datetime

import jsonschema

from slamon_afm.models import db, Agent, AgentCapability, Task
from slamon_afm.tests.afm_test import AFMTest


class TestPolling(AFMTest):
    task_request_response_schema = {
        'type': 'object',
        'properties': {
            'tasks': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'task_id': {
                            'type': 'string',
                            'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
                        },
                        'task_type': {'type': 'string'},
                        'task_version': {'type': 'integer'},
                        'task_data': {'type': 'object'}
                    },
                    'required': ['task_id', 'task_type', 'task_version', 'task_data'],
                    'additionalProperties': False
                }
            },
            'return_time': {
                'type': 'string'
            }
        },
        'required': ['tasks', 'return_time'],
        'additionalProperties': False
    }

    def test_poll_tasks_non_json_request(self):
        """Test a non-JSON request"""
        assert self.test_app.post('/tasks', expect_errors=True).status_int == 400

    def test_poll_tasks_empty_request(self):
        assert self.test_app.post_json('/tasks', {}, expect_errors=True).status_int == 400
        assert self.test_app.post_json('/tasks/', {}, expect_errors=True).status_int == 400

    def test_poll_tasks_empty(self):
        """Test if task polling behaves when no tasks are available."""
        resp = self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 5
        })
        jsonschema.validate(resp.json, TestPolling.task_request_response_schema)
        self.assertEqual(len(resp.json['tasks']), 0)

    def test_poll_tasks_claim_one(self):
        """Test if task is correctly claimed."""

        task = Task()
        task.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546013'
        task.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546013'
        task.type = 'task-type-1'
        task.version = 1
        task.data = {}
        db.session.add(task)
        db.session.commit()

        resp = self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 5
        })
        jsonschema.validate(resp.json, TestPolling.task_request_response_schema)
        self.assertEqual(len(resp.json['tasks']), 1)

    def test_poll_task_capability_change(self):
        self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 5
        })

        agent = db.session.query(Agent).filter(Agent.uuid == 'de305d54-75b4-431b-adb2-eb6b9e546013').one()
        self.assertEqual(len(agent.capabilities), 2)

        self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 2},
                'task-type-3': {'version': 3},
                'task-type-4': {'version': 4}
            },
            'max_tasks': 5
        })

        agent = db.session.query(Agent).filter(Agent.uuid == 'de305d54-75b4-431b-adb2-eb6b9e546013').one()
        self.assertEqual(len(agent.capabilities), 3)

        self.assertEqual(db.session.query(AgentCapability).filter(AgentCapability.agent_uuid == agent.uuid).
                         filter(AgentCapability.type == 'task-type-1').one().version, 2)
        self.assertEqual(db.session.query(AgentCapability).filter(AgentCapability.agent_uuid == agent.uuid).
                         filter(AgentCapability.type == 'task-type-3').one().version, 3)
        self.assertEqual(db.session.query(AgentCapability).filter(AgentCapability.agent_uuid == agent.uuid).
                         filter(AgentCapability.type == 'task-type-4').one().version, 4)

    def test_poll_tasks_invalid_data(self):
        # Invalid protocol
        assert self.test_app.post_json('/tasks', {
            'protocol': 'invalid',
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 1
        }, expect_errors=True).status_int == 400

        # Another invalid protocol - so far only protocol version 1 is supported
        assert self.test_app.post_json('/tasks', {
            'protocol': 5,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 1
        }, expect_errors=True).status_int == 400

        # Invalid agent_id
        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'invalid_agent',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 1
        }, expect_errors=True).status_int == 400

        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 'many_tasks'
        }, expect_errors=True).status_int == 400

        # Extra fields
        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 'many_tasks',
            'extra_field': 1234
        }, expect_errors=True).status_int == 400

        # Extra fields
        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18',
                'somewhere': 'else'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 'many_tasks'
        }, expect_errors=True).status_int == 400

    def test_poll_tasks_missing_data(self):
        # Missing max_tasks
        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            }
        }, expect_errors=True).status_int == 400

        # Missing agent_id
        assert self.test_app.post_json('/tasks', {
            'protocol': 1,
            'agent_name': 'Agent 007',
            'agent_location': {
                'country': 'FI',
                'region': '18'
            },
            'agent_time': '2012-04-23T18:25:43.511Z',
            'agent_capabilities': {
                'task-type-1': {'version': 1},
                'task-type-2': {'version': 2}
            },
            'max_tasks': 5
        }, expect_errors=True).status_int == 400


class TestPushing(AFMTest):
    def test_push_response_non_json(self):
        assert self.test_app.post('/tasks/response', expect_errors=True).status_int == 400
        assert self.test_app.post('/tasks/response/', expect_errors=True).status_int == 400

    def test_push_response_empty(self):
        assert self.test_app.post_json('/tasks/response', {}, expect_errors=True).status_int == 400
        assert self.test_app.post_json('/tasks/response/', {}, expect_errors=True).status_int == 400

    def test_push_response(self):
        task = Task()
        task.uuid = 'de305d54-75b4-431b-adb2-eb6b9e546013'
        task.test_id = 'de305d54-75b4-431b-adb2-eb6b9e546013'
        task.claimed = datetime.utcnow()
        db.session.add(task)
        db.session.commit()

        r = self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_data': {
                'key': 'value',
                'another_key': 5
            }
        })
        print(r)

        task = db.session.query(Task).filter(Task.uuid == 'de305d54-75b4-431b-adb2-eb6b9e546013').one()

        self.assertIsNotNone(task.completed)
        self.assertIsNotNone(task.completed)
        self.assertIsNotNone(task.result_data)
        self.assertIsNone(task.failed)
        self.assertIsNone(task.error)

        task.completed = None
        task.result_data = None
        db.session.commit()
        self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_error': 'Something went terribly wrong'
        })

        task = db.session.query(Task).filter(Task.uuid == 'de305d54-75b4-431b-adb2-eb6b9e546013').one()

        assert task.completed is None
        assert task.result_data is None
        assert task.failed is not None
        assert task.error is not None

    def test_push_response_invalid(self):
        # Invalid task id
        assert self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 5,
            'task_data': {
                'key': 'value',
                'another_key': 5
            }
        }, expect_errors=True).status_int == 400

        # Missing data and error
        assert self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546012'
        }, expect_errors=True).status_int == 400

        # Wrong type for error
        assert self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_error': 5
        }, expect_errors=True).status_int == 400

        # Task that doesn't exist
        assert self.test_app.post_json('/tasks/response', {
            'protocol': 1,
            'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'task_data': {
                'key': 'value',
                'another_key': 5
            }
        }, expect_errors=True).status_int == 400
