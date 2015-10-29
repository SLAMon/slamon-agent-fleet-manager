from datetime import datetime
from enum import Enum
import json

from flask import current_app
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, CHAR, DateTime, String, ForeignKey, PrimaryKeyConstraint, Unicode, and_, \
    TypeDecorator
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func, event, case, literal_column

db = SQLAlchemy()

from slamon_afm.stats import statsd


class TaskException(Exception):
    task = None

    def __init__(self, *args, task=None):
        super(TaskException, self).__init__(*args)
        self.task = task


class IllegalStateException(TaskException):
    pass


class Agent(db.Model):
    __tablename__ = 'agents'

    uuid = Column('uuid', CHAR(36), primary_key=True, nullable=False)
    name = Column('name', Unicode, nullable=False)
    last_seen = Column('last_seen', DateTime, default=datetime.utcnow)

    @staticmethod
    def get_agent(agent_uuid, agent_name):
        """
        Get existing Agent instance from DB or insert a new one if none exists.

        :param agent_uuid: Agent identifier
        :param agent_name: Agent name to use when creating new instance
        :return: Agent instance
        """
        try:
            agent = db.session.query(Agent).filter(Agent.uuid == agent_uuid).one()
        except NoResultFound:
            current_app.logger.debug('Registering new agent {0}'.format(agent_uuid))
            agent = Agent(uuid=agent_uuid, name=agent_name)
            db.session.add(agent)
        return agent

    def update_capabilities(self, agent_capabilities):
        """
        Update capabilities of the agent to match the new definitions in agent_capabilities

        :param agent_capabilities: A dict describing the new capability set
        """

        # format capabilities list as a dict of (name,version) pairs
        new_capabilities = {name: int(info['version']) for name, info in agent_capabilities.items()}

        # Update existing capabilities
        for capability in self.capabilities:
            if capability.type in new_capabilities:
                capability.version = new_capabilities[capability.type]
                del new_capabilities[capability.type]
            else:
                self.capabilities.remove(capability)

        # Add new capabilities
        for name, version in new_capabilities.items():
            self.capabilities.append(
                AgentCapability(
                    type=name,
                    version=version
                )
            )

    def tasks_summary(self):
        """
        Fetch summary of tasks assigned and handled by the agent.

        :return: A dict containing keys 'assigned', 'completed' and 'error'.
        """
        return dict(zip(
            ('assigned', 'completed', 'failed'),
            db.session.query(
                func.count(Task.uuid),
                func.count(Task.completed),
                func.count(Task.failed)
            ).filter(Task.assigned_agent_uuid == self.uuid).one()
        ))

    @staticmethod
    def drop_inactive(last_seen_threshold):
        """
        Drop all agents not seen after defined datetime. Relying on foreign key
        cascades to deassign all claimed tasks.

        :param last_seen_threshold: drop agents that have not been seen after this datetime
        """

        # delete agents
        db.session.query(Agent).filter(Agent.last_seen < last_seen_threshold).delete(synchronize_session=False)

        # mark deassigned tasks as failed. This would be bit more efficient with SQL triggers, but this would
        # require dialect specific triggers and still maintain this as a fallback when no triggers exists.
        db.session.query(Task).filter(and_(Task.assigned_agent_uuid == None,
                                           Task.claimed != None,
                                           Task.failed == None,
                                           Task.completed == None)).update(
            {
                'failed': datetime.utcnow(),
                'error': 'Assigned agent reached last seen threshold and is now considered as inactive.'
            },
            synchronize_session=False
        )


class AgentCapability(db.Model):
    __tablename__ = 'agent_capabilities'

    agent_uuid = Column('agent_uuid', CHAR(36), ForeignKey('agents.uuid', ondelete='CASCADE', onupdate='CASCADE'))
    agent = relationship(Agent, backref=backref("capabilities", cascade="all, delete-orphan"))

    type = Column('type', String)
    version = Column('version', Integer)

    __table_args__ = (PrimaryKeyConstraint(agent_uuid, type, version),)

    @classmethod
    def summary(cls, last_seen_threshold=None):
        """
        Summarize availability of each capability/version pair.

        :param last_seen_threshold: Optionally filter by only agents seen after datetime
        """
        query = db.session.query(cls.type, cls.version, func.count(cls.type)).group_by(cls.type, cls.version)
        if last_seen_threshold is not None:
            query = query.filter(cls.agent.has(Agent.last_seen >= last_seen_threshold))
        for row in query:
            yield dict(zip(('type', 'version', 'count'), row))

    @classmethod
    def update_gauges(cls):
        """ Publish capability availability gauges to StatsD """
        for capability in cls.summary():
            statsd.gauge('capability.{type}.{version}'.format(**capability), capability['count'])


class JSONEncodedDict(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        del dialect  # unused argument provided by SQLAlchemy
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        del dialect  # unused argument provided by SQLAlchemy
        if value is not None:
            value = json.loads(value)
        return value

class TaskEvent(Enum):
    posted = 'posted'
    claimed = 'claimed'
    completed = 'completed'
    error = 'error'

    def __str__(self):
        return self.value


class Task(db.Model):
    __tablename__ = 'tasks'

    uuid = Column('uuid', CHAR(36), primary_key=True)
    test_id = Column('test_id', CHAR(36), nullable=False)
    type = Column('type', String)
    version = Column('version', Integer)

    # Data that goes to agent with the task
    data = Column('data', JSONEncodedDict)
    # Data that was returned from agent
    result_data = Column('result_data', JSONEncodedDict)

    # Agent that has been assigned to take care of the task - NULL if not claimed yet
    assigned_agent_uuid = Column('assigned_agent_uuid', ForeignKey('agents.uuid', ondelete='SET NULL'))
    assigned_agent = relationship(Agent, backref=backref("tasks", lazy='dynamic'))

    # When was the task added
    created = Column('created', DateTime, default=datetime.utcnow, nullable=False)
    # When was the task claimed by agent - NULL if not claimed yet
    claimed = Column('claimed', DateTime, nullable=True)
    # When was the task completed by agent - NULL if not completed yet
    completed = Column('completed', DateTime, nullable=True)
    # When did the task fail - NULL if hasn't failed yet, additional info in error-field
    failed = Column('started', DateTime, nullable=True)
    # Error message that should only be present if failed is set
    error = Column('error', Unicode, nullable=True)

    def send_stats(self, task_event):
        """Increase stats counters/timers for both total and per task type"""
        statsd.incr("tasks.{}".format(task_event))
        if task_event is not TaskEvent.posted:
            statsd.timing(
                "tasks.{}.{}.{}".format(self.type, self.version, task_event),
                int((datetime.now() - self.created).total_seconds() * 1000)
            )
        else:
            statsd.incr("tasks.{}.{}.{}".format(self.type, self.version, task_event))
        # update gauge values for task type/version
        Task.update_gauges(filter_criteria=and_(Task.type == self.type, Task.version == self.version))

    def claim(self, agent):
        """
        Mark task as claimed and post stats to statsd.
        Note that to prevent tasks being assigned to multiple agent, the task
        should be selected with *FOR UPDATE* statement.

        :param agent: The agent the task is being assigned to
        """
        current_app.logger.info("Claiming task {} for agent {}".format(self.uuid, agent.uuid))
        self.assigned_agent_uuid = agent.uuid
        self.claimed = datetime.utcnow()
        self.send_stats(TaskEvent.claimed)

    def complete(self, result_data=None, error=None):
        """
        Mark task as completed, save results and send stats to statsd.

        :param result_data: Task result data when successfully completed
        :param error: Task error when completed with an error
        """
        if self.completed or self.failed:
            raise IllegalStateException("Cannot complete a tasks that is already completed!", task=self)
        elif not self.claimed:
            raise IllegalStateException("Cannot complete a task that was never claimed!", task=self)
        elif result_data is not None:
            self.completed = datetime.utcnow()
            self.result_data = result_data
            current_app.logger.info("Task {} completed".format(self.uuid))
            self.send_stats(TaskEvent.completed)
        elif error is not None:
            self.failed = datetime.utcnow()
            self.error = error
            current_app.logger.warn("Task {} completed with error".format(self.uuid))
            self.send_stats(TaskEvent.error)
        else:
            raise TaskException("Attempt to complete task neither with results nor errors", task=self)

    @classmethod
    def task_summary(cls, filter_criteria=None):
        """ Summarize task counts in database by task type """
        queued_criteria = and_(cls.claimed == None, cls.completed == None, cls.failed == None)
        processing_criteria = and_(cls.claimed != None, cls.completed == None, cls.failed == None)
        query = db.session.query(cls.type, cls.version,
                                 func.count(case([(queued_criteria, cls.uuid)], else_=literal_column("NULL"))),
                                 func.count(case([(processing_criteria, cls.uuid)], else_=literal_column("NULL")))) \
            .group_by(cls.type, cls.version)
        if filter_criteria is not None:
            query = query.filter(filter_criteria)
        for row in query:
            yield dict(zip(('type', 'version', 'queued', 'processing'), row))

    @classmethod
    def update_gauges(cls, filter_criteria=None):
        """ Publish active task counts to StatsD """
        for task_type in cls.task_summary(filter_criteria=filter_criteria):
            statsd.gauge('tasks.{type}.{version}.queue'.format(**task_type), task_type['queued'])
            statsd.gauge('tasks.{type}.{version}.processing'.format(**task_type), task_type['processing'])

    @staticmethod
    def claim_tasks(agent, max_tasks):
        """
        Claim tasks to be handled by an agent.

        :param agent: The agent to assign tasks to
        :param max_tasks: Maximum number of tasks to assign
        :return: A generator enumerating assigned tasks
        """
        query = db.session.query(AgentCapability, Task). \
            filter(and_(Task.assigned_agent_uuid.is_(None), Task.completed.is_(None), Task.error.is_(None))). \
            filter(AgentCapability.agent_uuid == agent.uuid). \
            filter(and_(AgentCapability.type == Task.type, AgentCapability.version == Task.version)). \
            order_by(Task.created). \
            with_for_update()

        # Assign available tasks to the agent and mark them as being in process
        for _, task in query[0:max_tasks]:
            task.claim(agent)
            yield task

    @staticmethod
    def update_inactive(last_seen_threshold):
        """
        Mark all tasks claimed by agents that have not been seen after defined datetime as failed

        :param last_seen_threshold: select tasks claimed by agents not seen after this datetime
        """

        db.session.query(Task).filter(Task.assigned_agent.has(Agent.last_seen < last_seen_threshold)).update(
            {
                'failed': datetime.utcnow(),
                'error': 'Assigned agent reached last seen threshold and is now considered as inactive.'
            },
            synchronize_session=False
        )


@event.listens_for(Task, 'after_insert')
def receive_after_insert(mapper, connection, task):
    del mapper, connection  # unused
    task.send_stats('posted')


@event.listens_for(Task, 'after_delete')
def receive_after_delete(mapper, connection, task):
    del mapper, connection  # unused
    task.send_stats('deleted')
