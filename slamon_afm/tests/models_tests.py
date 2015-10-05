from datetime import datetime
from itertools import permutations
from uuid import UUID, uuid5
from unittest.mock import patch, ANY

from slamon_afm.models import db, Task, Agent, AgentCapability
from slamon_afm.tests.afm_test import AFMTest
from slamon_afm.stats import statsd


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
            data={},
            claimed=datetime.utcnow(),
            assigned_agent=self.agent
        )
        db.session.add(self.task)

        db.session.flush()
        self.assertEqual(self.agent.tasks.count(), 1)
        self.assertIsNotNone(self.task.assigned_agent_uuid)

    def testFailTasksFromInactiveAgents(self):
        Task.update_inactive(datetime.utcnow())
        db.session.flush()
        db.session.refresh(self.agent)
        db.session.refresh(self.task)

        self.assertEqual(self.agent.tasks.count(), 1)
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
            data={}
        )
        db.session.add(task)
        db.session.flush()

        claimed = list(Task.claim_tasks(self.agent, 1))
        self.assertEqual(len(claimed), 1)

    def testClaimTaskOrder(self):
        """
        Ensure the oldest task is always served first
        """
        times = list(permutations([
            datetime(2015, 10, 1, 10, 0, 0),
            datetime(2015, 10, 1, 11, 0, 0),
            datetime(2015, 10, 1, 12, 0, 0)
        ]))

        def create_uuid(*args):
            return str(uuid5(UUID('de305d54-75b4-431b-adb2-eb6b9e546013'), '.'.join(map(str, args))))

        for seq in range(len(times)):
            for time in times[seq]:
                db.session.add(Task(
                    created=time,
                    uuid=create_uuid(time, seq),
                    test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
                    type='task-type-1',
                    version=1,
                    data={}
                ))
                db.session.flush()

            # claim tasks one by one to figure the served order
            claimed = (
                list(Task.claim_tasks(self.agent, 1))[0],
                list(Task.claim_tasks(self.agent, 1))[0],
                list(Task.claim_tasks(self.agent, 1))[0]
            )

            self.assertLess(claimed[0].created, claimed[1].created)
            self.assertLess(claimed[1].created, claimed[2].created)

    def testDontClaimCompleteTasks(self):
        task = Task(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            test_id='de305d54-75b4-431b-adb2-eb6b9e546013',
            type='task-type-1',
            version=1,
            data={},
            completed=datetime.now(),
            result_data={}
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
            data={},
            failed=datetime.now(),
            error='some error'
        )
        db.session.add(task)
        db.session.flush()
        claimed = list(Task.claim_tasks(self.agent, 1))
        self.assertEqual(len(claimed), 0)


class TaskStatsTests(AFMTest):
    def setUp(self):
        super(TaskStatsTests, self).setUp()
        self.agent = Agent(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546013',
            name='test agent',
            last_seen=datetime.utcnow(),
            capabilities=[AgentCapability(type='task-type-1', version=1)]
        )
        db.session.add(self.agent)
        db.session.flush()
        self.assertEqual(db.session.query(Agent).count(), 1)

    def _addTask(self, **kwargs):
        default = {
            'uuid': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'test_id': 'de305d54-75b4-431b-adb2-eb6b9e546013',
            'type': 'task-type-1',
            'version': 1,
            'data': {}
        }
        default.update(kwargs)
        task = Task(**default)
        db.session.add(task)
        db.session.flush()
        return task

    @patch.object(statsd, 'incr', return_value=None)
    @patch.object(statsd, 'timing', return_value=None)
    def testIncPostedStats(self, timing_mock, incr_mock):
        self._addTask()

        incr_mock.assert_called_once_with('tasks.posted')
        timing_mock.assert_not_called()

    def testIncDeletedStats(self):
        task = self._addTask()
        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock:
            db.session.delete(task)
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.deleted')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.deleted', ANY)

    def testIncClaimedStats(self):
        self._addTask()

        # create list to iterate the generator returned by claim_tasks
        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock:
            _ = list(Task.claim_tasks(self.agent, 1))
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.claimed')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.claimed', ANY)

    def testIncCompletedStats(self):
        # create task with claimed status
        task = self._addTask(
            assigned_agent=self.agent,
            claimed=datetime.utcnow()
        )

        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock:
            # complete task
            task.complete(result_data={})
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.completed')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.completed', ANY)

    def testIncErrorStats(self):
        # create task with claimed status
        task = self._addTask(
            assigned_agent=self.agent,
            claimed=datetime.utcnow()
        )

        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock:
            # complete task
            task.complete(error='test')
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.error')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.error', ANY)
