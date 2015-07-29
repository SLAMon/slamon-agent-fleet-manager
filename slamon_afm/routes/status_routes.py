from datetime import datetime, timedelta

from bottle import HTTPError

from slamon_afm.afm_app import app
from slamon_afm.database import create_session
from slamon_afm.tables import Agent, Task
from slamon_afm.settings import Settings


@app.get('/status')
@app.get('/status/')
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
    try:
        session = create_session()
    except:
        raise HTTPError(500, 'Something wen\'t wrong with database session')

    agent_time_threshold = datetime.utcnow() - timedelta(0, Settings.agent_active_threshold)

    try:
        num_agents = session.query(Agent).filter(Agent.last_seen > agent_time_threshold).count()
        tasks_waiting = session.query(Task).filter(Task.claimed is None).count()
    except Exception as e:
        raise HTTPError(500, 'Failed to query tasks and agents ' + str(e))
    finally:
        session.close()

    return {'agents': num_agents, 'tasks_waiting': tasks_waiting}
