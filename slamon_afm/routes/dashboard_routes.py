import json

import os.path
from flask import abort, jsonify, send_file, current_app
from flask.blueprints import Blueprint

from slamon_afm.models import db, Agent, Task

blueprint = Blueprint('testing', __name__)


@blueprint.route('/testing/agents', strict_slashes=False)
def dev_get_agents():
    try:
        query = db.session.query(Agent)
        agents = query.all()
    except Exception as e:
        current_app.logger.exception(e)
        abort(500)

    agents_array = []
    for agent in agents:
        agent_json = {
            'agent_id': agent.uuid,
            'agent_name': agent.name,
            'last_seen': str(agent.last_seen)
        }

        if agent.capabilities:
            agent_json['agent_capabilities'] = {}
            for capability in agent.capabilities:
                agent_json['agent_capabilities'][capability.type] = {
                    'version': capability.version
                }

        agents_array.append(agent_json)

    return jsonify(agents=agents_array)


@blueprint.route('/testing/tasks', strict_slashes=False)
def dev_get_tasks():
    try:
        query = db.session.query(Task)
        tasks = query.all()
    except Exception as e:
        current_app.logger.exception(e)
        abort(500)

    tasks_array = []
    for task in tasks:
        task_desc = {
            'task_id': task.uuid,
            'task_type': task.type,
            'task_version': task.version,
            'test_id': task.test_id
        }

        if task.data is not None:
            task_desc['task_data'] = json.loads(task.data)
        if task.failed:
            task_desc['task_failed'] = str(task.failed)
            task_desc['task_error'] = str(task.error)
        elif task.completed:
            task_desc['task_completed'] = str(task.completed)
            task_desc['task_result'] = str(task.result_data)

        tasks_array.append(task_desc)

    return jsonify(tasks=tasks_array)


@blueprint.route('/testing', strict_slashes=False)
def dev_testing_index():
    print(os.path.join(os.path.dirname(__file__), 'testing.html'))
    print(current_app)
    return send_file(os.path.join(os.path.dirname(__file__), 'testing.html'))
