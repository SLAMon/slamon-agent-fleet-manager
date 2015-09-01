import os.path
from flask import jsonify, send_file
from flask.blueprints import Blueprint

from slamon_afm.models import db, Agent, Task

blueprint = Blueprint('testing', __name__)


def serialize_task(task):
    return {
        'task_id': task.uuid,
        'task_type': task.type,
        'task_version': task.version,
        'test_id': task.test_id,
        'task_failed': str(task.failed) if task.failed else None,
        'task_completed': str(task.completed) if task.completed else None,
        'task_result': task.result_data,
        'task_error': task.error
    }


def serialize_agent(agent):
    return {
        'agent_id': agent.uuid,
        'agent_name': agent.name,
        'last_seen': str(agent.last_seen),
        'tasks': [serialize_task(task) for task in agent.tasks]
    }


@blueprint.route('/dashboard/status', strict_slashes=False)
def dev_get_agents():
    return jsonify(
        tasks=[serialize_task(task) for task in db.session.query(Task).filter(Task.assigned_agent_uuid == None)],
        agents=[serialize_agent(agent) for agent in db.session.query(Agent).all()]
    )


@blueprint.route('/dashboard', strict_slashes=False)
def dev_testing_index():
    return send_file(os.path.join(os.path.dirname(__file__), 'dashboard.html'))
