import jsonschema
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError, ProgrammingError
from flask.blueprints import Blueprint
from flask import request, abort, jsonify, current_app

from slamon_afm.models import db, Task

blueprint = Blueprint('bpms', __name__)

POST_TASK_SCHEMA = {
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
            'type': 'object'
        },
        'test_id': {
            'type': 'string',
            'pattern': '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
        }
    },
    'required': ['task_id', 'task_type', 'task_version', 'test_id'],
    'additionalProperties': False
}


@blueprint.route('/task', methods=['POST'], strict_slashes=False)
def post_task():
    data = request.json

    if data is None:
        abort(400)

    try:
        jsonschema.validate(data, POST_TASK_SCHEMA)
    except jsonschema.ValidationError:
        abort(400)

    task_uuid = str(data['task_id'])
    task_type = str(data['task_type'])
    task_test_id = (data['test_id'])
    task_data = ""

    task = Task(
        uuid=task_uuid,
        type=task_type,
        version=int(data['task_version']),
        test_id=task_test_id
    )

    if 'task_data' in data:
        task_data = data['task_data']
        task.data = task_data

    try:
        db.session.add(task)
    except IntegrityError:
        db.session.rollback()
        abort(400)

    try:
        db.session.commit()
    except (IntegrityError, ProgrammingError):
        db.session.rollback()
        current_app.logger.error("Failed to commit database changes for BPMS task POST")
        abort(400)

    current_app.logger.info("Task posted by BPMS - Task's type: {}, test process id: {}, uuid: {}, parameters: {}"
                            .format(task_type, task_test_id, task_uuid, task_data))

    return '', 200


@blueprint.route('/task/<uuid:task_uuid>', methods=['GET'], strict_slashes=False)
def get_task(task_uuid):
    """
    Gets information about single task with uuid task_uuid
    :param task_uuid: uuid of the task
    :return: dict in following format
    {
        'task_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',  # UUID of the task (str)
        'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',  # UUID of the test (str)
        'task_type': 'wait',                                # type of the task (str)
        'task_version': 1,                                  # Version number of the task
        'task_data': {},                                    # Dict containing data passed to the task (if any)
        'task_completed': '31-03-2015:12:12:12',            # Time when task was completed (if completed)
        'task_result': {},                                  # Dict containing task's results (if completed)
        'task_failed': '31-03-2015:12:12:12',               # Time when task failed (if failed)
        'task_error': 'Something went wrong'                # Error that caused task to fail (if failed)
    }
    """

    try:
        query = db.session.query(Task)
        task = query.filter(Task.uuid == str(task_uuid)).one()

        task_desc = {
            'task_id': task.uuid,
            'test_id': task.test_id,
            'task_type': task.type,
            'task_version': task.version
        }

        if task.data is not None:
            task_desc['task_data'] = task.data

        if task.failed:
            task_desc['task_failed'] = str(task.failed)
            task_desc['task_error'] = str(task.error)
        elif task.completed:
            task_desc['task_completed'] = str(task.completed)
            task_desc['task_result'] = task.result_data

        return jsonify(task_desc)

    except NoResultFound:
        abort(404)
