from datetime import datetime

from slamon_afm.models import db, Task, Agent, AgentCapability
from slamon_afm.tests.afm_test import AFMTest


class TaskUnassignTests(AFMTest):
    """
    These tests are not actually testing any code but continuing
    the tradition of using DB withing unittests by checking if the
    SQLAlchemy declarations work as intended.
    """

    def setUp(self):
        super(TaskUnassignTests, self).setUp()

        self.agent = Agent(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            name='test agent',
            last_seen=datetime.utcnow()
        )
        db.session.add(self.agent)

        self.task = Task(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
            type='task-type-1',
            version=1,
            data="{}",
            claimed=datetime.utcnow(),
            assigned_agent=self.agent
        )
        db.session.add(self.task)

        db.session.flush()
        self.assertEqual(len(self.agent.tasks), 1)
        self.assertIsNotNone(self.task.assigned_agent_uuid)

    def testFailTasksFromInactiveAgents(self):
        Task.update_inactive(datetime.utcnow())
        db.session.flush()
        db.session.refresh(self.agent)
        db.session.refresh(self.task)

        self.assertEqual(len(self.agent.tasks), 1)
        self.assertIsNotNone(self.task.failed)
        self.assertIsNotNone(self.task.error)

    def testDropAgents(self):
        Agent.drop_inactive(datetime.utcnow())
        db.session.flush()
        db.session.refresh(self.task)

        self.assertEqual(db.session.query(Agent).count(), 0)
        self.assertIsNone(self.task.assigned_agent_uuid)
        self.assertIsNotNone(self.task.failed)
        self.assertIsNotNone(self.task.error)

    def testDropAgentsWithCapabilities(self):
        self.agent.capabilities.append(AgentCapability(type='task-type-test', version=1))
        db.session.flush()

        Agent.drop_inactive(datetime.utcnow())

        db.session.flush()
        db.session.refresh(self.task)

        self.assertEqual(db.session.query(Agent).count(), 0)
        self.assertIsNone(self.task.assigned_agent_uuid)


class TaskClaimingTests(AFMTest):
    def setUp(self):
        super(TaskClaimingTests, self).setUp()
        self.agent = Agent(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            name='test agent',
            last_seen=datetime.utcnow(),
            capabilities=[AgentCapability(type='task-type-1', version=1)]
        )
        db.session.add(self.agent)
        db.session.flush()

    def testClaimUnassignedTask(self):
        task = Task(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
            type='task-type-1',
            version=1,
            data="{}"
        )
        db.session.add(task)
        db.session.flush()

        claimed = list(Task.claim_tasks(self.agent, 1))
        self.assertEqual(len(claimed), 1)

    def testDontClaimCompleteTasks(self):
        task = Task(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
            type='task-type-1',
            version=1,
            data="{}",
            completed=datetime.now(),
            result_data='{}'
        )
        db.session.add(task)
        db.session.flush()

        claimed = list(Task.claim_tasks(self.agent, 1))
        self.assertEqual(len(claimed), 0)

    def testDontClaimErrorTasks(self):
        task = Task(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
            type='task-type-1',
            version=1,
            data="{}",
            failed=datetime.now(),
            error='some error'
        )
        db.session.add(task)
        db.session.flush()

        claimed = list(Task.claim_tasks(self.agent, 1))
        self.assertEqual(len(claimed), 0)
