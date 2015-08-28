from datetime import datetime, timedelta

from flask.blueprints import Blueprint
from flask import abort, current_app
from flask.json import jsonify

from slamon_afm.models import db, Agent, Task

blueprint = Blueprint('status', __name__)


@blueprint.route('/status', methods=['GET'], strict_slashes=False)
def status():
    """
    Simple status page which verifies that database connectivity works and tells stats about pending tasks and active
    agents
    :return: dict in following format
    {
        'agents': 5,        # Number of agents that have been active within last Settings.agent_active_threshold seconds
        'tasks_waiting': 10 # Number of tasks that haven't been claimed yet
    }
    """

    agent_time_threshold = datetime.utcnow() - timedelta(0, current_app.config['AGENT_ACTIVE_THRESHOLD'])

    try:
        num_agents = db.session.query(Agent).filter(Agent.last_seen > agent_time_threshold).count()
        tasks_waiting = db.session.query(Task).filter(Task.claimed is None).count()
        return jsonify(agents=num_agents, tasks_waiting=tasks_waiting)
    except Exception as e:
        abort(500, 'Failed to query tasks and agents ' + str(e))
