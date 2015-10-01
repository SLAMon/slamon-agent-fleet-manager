import os.path
from flask import send_file
from flask.blueprints import Blueprint
from flask_restless import APIManager

from slamon_afm.models import db, Agent, Task

manager = APIManager(flask_sqlalchemy_db=db)

blueprint = Blueprint('testing', __name__)


def task_get_many_preprocessor(search_params=None, **unused):
    """
    By default, list only pending tasks ordered by creation time.
    """
    del unused  # unused arguments provided by Flask-restless
    if 'filters' not in search_params:
        search_params['filters'] = [{'and': [{'name': 'assigned_agent_uuid', 'op': 'is_null'},
                                             {'name': 'completed', 'op': 'is_null'},
                                             {'name': 'error', 'op': 'is_null'}]}]
    if 'order_by' not in search_params:
        search_params['order_by'] = [{'field': 'created', 'direction': 'desc'}]


def agent_get_many_preprocessor(search_params=None, **unused):
    """
    By default order agents by uuid
    """
    del unused  # unused arguments provided by Flask-restless
    if 'order_by' not in search_params:
        search_params['order_by'] = [{'field': 'uuid', 'direction': 'asc'}]


def register_blueprints(app):
    app.register_blueprint(blueprint)
    manager.init_app(app)
    with app.app_context():
        # Flask-restless provides no way to specify different serialization strategies for
        # list and single object requests. As a workaround to improve dashboard status query
        # efficiency, there's now two separate api endpoints for both tasks and agents:
        # one with full object serialization and one with limited columns

        # the /status -prefixed api endpoints will exclude all potentially large fields and relationships
        # to achieve fast listing on entities and only enable readonly access.
        manager.create_api(Agent, url_prefix='/status', app=app, methods=frozenset(['GET']),
                           include_methods=['tasks_summary'],
                           results_per_page=100, preprocessors={'GET_MANY': [agent_get_many_preprocessor]},
                           exclude_columns=['capabilities', 'tasks'])
        manager.create_api(Task, url_prefix='/status', app=app, methods=frozenset(['GET']),
                           results_per_page=100, max_results_per_page=1000,
                           preprocessors={'GET_MANY': [task_get_many_preprocessor]},
                           exclude_columns=['assigned_agent', 'data', 'result_data', 'error'])

        # /api -prefixed routes will enable full serialization of and posting new tasks, excluding implicit
        # nested relationships.
        manager.create_api(Agent, url_prefix='/api', exclude_columns=['tasks'], app=app,
                           methods=frozenset(['GET']))
        manager.create_api(Task, url_prefix='/api', exclude_columns=['assigned_agent'], app=app,
                           methods=frozenset(['GET', 'POST']))


@blueprint.route('/dashboard', strict_slashes=False)
def dev_testing_index():
    return send_file(os.path.join(os.path.dirname(__file__), 'dashboard.html'))
