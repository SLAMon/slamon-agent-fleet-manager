from datetime import datetime, timedelta
import json

import jsonschema
from flask import request, abort, current_app
from flask.blueprints import Blueprint
from flask.json import jsonify
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import and_
from dateutil import tz

from slamon_afm.models import db, Agent, AgentCapability, Task

blueprint = Blueprint('agent', __name__)

TASK_REQUEST_SCHEMA = {
    'type': 'object',
    'properties': {
        'protocol': {
            'type': 'integer',
            'minimum': 1
        },
        'agent_id': {
            'type': 'string',
            'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
        },
        'agent_name': {'type': 'string'},
        'agent_location': {
            'type': 'object',
            'properties': {
                'country': {
                    'type': 'string',
                    'minLength': 2,
                    'maxLength': 2
                },
                'region': {
                    'type': 'string',
                    'minLength': 2,
                    'maxLength': 4
                },
                'latitude': {
                    'type': 'number'
                },
                'longitude': {
                    'type': 'number'
                }
            },
            'required': ['country', 'region'],
            'additionalProperties': False
        },
        'agent_capabilities': {
            'type': 'object',
            'patternProperties': {
                '^.+$': {
                    'type': 'object',
                    'properties': {
                        'version': {'type': 'integer'}
                    }
                }
            }
        },
        'agent_time': {
            'type': 'string'
        },
        'max_tasks': {
            'type': 'integer'
        }
    },
    'required': ['protocol', 'agent_id', 'agent_name', 'agent_time', 'agent_capabilities', 'max_tasks'],
    'additionalProperties': False
}

TASK_RESPONSE_SCHEMA = {
    'type': 'object',
    'oneOf': [
        {
            'type': 'object',
            'properties': {
                'protocol': {
                    'type': 'integer'
                },
                'task_id': {
                    'type': 'string',
                    'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
                },
                'task_data': {
                    'type': 'object'
                }
            },
            'additionalProperties': False,
            'required': ['protocol', 'task_id', 'task_data']
        },
        {
            'type': 'object',
            'properties': {
                'protocol': {
                    'type': 'integer'
                },
                'task_id': {
                    'type': 'string',
                    'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
                },
                'task_error': {
                    'type': 'string'
                }
            },
            'additionalProperties': False,
            'required': ['protocol', 'task_id', 'task_error']
        }
    ]
}


@blueprint.route('/tasks', methods=['POST'], strict_slashes=False)
def request_tasks():
    data = request.json

    if data is None:
        current_app.logger.error('No JSON data provided with request.')
        abort(400)

    try:
        jsonschema.validate(data, TASK_REQUEST_SCHEMA)
    except jsonschema.ValidationError:
        current_app.logger.error('Invalid JSON data provided with request.')
        abort(400)

    protocol = int(data['protocol'])
    agent_uuid = str(data['agent_id'])
    agent_name = str(data['agent_name'])
    # agent_time = data['agent_time']
    agent_capabilities = data['agent_capabilities']
    max_tasks = int(data['max_tasks'])
    # agent_location = data['agent_location'] if 'agent_location' in data else None

    # Only protocol 1 supported for now
    if protocol != 1:
        abort(400)

    try:
        query = db.session.query(Agent)
        agent = query.filter(Agent.uuid == agent_uuid).one()

        db.session.query(AgentCapability).filter(AgentCapability.agent_uuid == agent.uuid).delete()
    except NoResultFound:
        current_app.logger.debug('Registering new agent {0}'.format(agent_uuid))
        agent = Agent(uuid=agent_uuid, name=agent_name)
        db.session.add(agent)

    for agent_capability, agent_capability_info in agent_capabilities.items():
        capability = AgentCapability(type=agent_capability,
                                     version=int(agent_capability_info['version']),
                                     agent=agent)
        db.session.add(capability)

    # Find all non-claimed tasks that the agent is able to handle and assign them to the agent
    query = db.session.query(AgentCapability, Task).filter(Task.assigned_agent_uuid.is_(None)). \
        filter(AgentCapability.agent_uuid == agent.uuid). \
        filter(and_(AgentCapability.type == Task.type, AgentCapability.version == Task.version))

    tasks = []

    # Assign available tasks to the agent and mark them as being in process
    for _, task in query[0:max_tasks]:
        task.assigned_agent_uuid = agent.uuid
        task.claimed = datetime.utcnow()
        tasks.append({
            'task_id': task.uuid,
            'task_type': task.type,
            'task_version': task.version,
            'task_data': json.loads(task.data)
        })

    agent.last_seen = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.error("Failed to commit database changes for task request")
        abort(500)

    current_app.logger.info("Assigning tasks {} to agent {}, {}"
                            .format([task.id for task in tasks], agent_name, agent_uuid))
    current_app.logger.debug("Task details: {}".format(tasks))

    return jsonify(
        tasks=tasks,
        return_time=(
            datetime.now(tz.tzlocal()) + timedelta(0, current_app.config.get('AGENT_RETURN_TIME', 5))).isoformat()
    )


@blueprint.route('/tasks/response', methods=['POST'], strict_slashes=False)
def post_tasks():
    data = request.json

    if data is None:
        current_app.logger.error("No JSON content in task response request!")
        abort(400)

    try:
        jsonschema.validate(data, TASK_RESPONSE_SCHEMA)
    except jsonschema.ValidationError as e:
        current_app.logger.error("Invalid JSON in task reponse: {0}".format(e))
        abort(400)

    protocol = int(data['protocol'])
    task_id = str(data['task_id'])

    # Only protocol 1 supported for now
    if protocol != 1:
        current_app.logger.error("Invalid protocol in task response: {0}".format(protocol))
        abort(400)

    try:
        task = db.session.query(Task).filter(Task.uuid == str(task_id)).one()

        if task.claimed is None or (task.completed is not None or task.failed is not None):
            current_app.logger.error("Incomplete task posted!")
            abort(400)

        result = ""
        if 'task_data' in data:
            task.result_data = json.dumps(data['task_data'])
            task.completed = datetime.utcnow()
            result = json.dumps(task.result_data)
        elif 'task_error' in data:
            task.error = data['task_error']
            task.failed = datetime.utcnow()
            result = task.error

        db.session.add(task)
    except NoResultFound:
        current_app.logger.error("No matching task in for task response!")
        abort(400)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.error("Failed to commit database changes for task result POST")
        abort(500)

    current_app.logger.info("An agent returned task with results - uuid: {}".format(task_id))
    current_app.logger.debug("Task results: {}".format(result))

    return ('', 200)
