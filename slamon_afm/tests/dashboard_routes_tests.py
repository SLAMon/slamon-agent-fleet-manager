import jsonschema

from slamon_afm.tests.agent_routes_tests import AFMTest


class TestDevRoutes(AFMTest):
    task_list_response_schema = {
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
                        'task_type': {
                            'type': 'string'
                        },
                        'task_version': {
                            'type': 'integer'
                        },
                        'task_data': {
                            'type': 'string'
                        }
                    },
                    'required': ['task_id', 'task_type', 'task_version']
                },
            },
            'agents': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'agent_id': {
                            'type': 'string',
                            'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
                        },
                        'agent_name': {
                            'type': 'string'
                        }
                    },
                    'additionalProperties': True,
                    'required': ['agent_id', 'agent_name', 'task_version']
                }
            }
        },
        'required': ['tasks'],
        'additionalProperties': False
    }

    def test_get_tasks(self):
        resp = self.test_app.get('/dashboard/status')
        jsonschema.validate(resp.json, TestDevRoutes.task_list_response_schema)
