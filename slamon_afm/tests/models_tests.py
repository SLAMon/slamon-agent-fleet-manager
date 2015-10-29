from datetime import datetime, timedelta
from itertools import permutations
from uuid import UUID, uuid5, uuid4
from unittest.mock import patch, ANY, call

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
    @patch.object(statsd, 'gauge', return_value=None)
    def testIncPostedStats(self, gauge_mock, timing_mock, incr_mock):
        self._addTask()

        incr_mock.assert_called_once_with('tasks.posted')
        timing_mock.assert_not_called()
        gauge_mock.assert_has_calls([
            call('tasks.task-type-1.1.queue', 1),
            call('tasks.task-type-1.1.processing', 0)
        ], any_order=True)

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
                patch.object(statsd, 'timing') as timing_mock,\
                patch.object(statsd, 'gauge') as gauge_mock:
            _ = list(Task.claim_tasks(self.agent, 1))
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.claimed')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.claimed', ANY)
            gauge_mock.assert_has_calls([
                call('tasks.task-type-1.1.queue', 0),
                call('tasks.task-type-1.1.processing', 1)
            ], any_order=True)

    def testIncCompletedStats(self):
        # create task with claimed status
        task = self._addTask(
            assigned_agent=self.agent,
            claimed=datetime.utcnow()
        )

        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock,\
                patch.object(statsd, 'gauge') as gauge_mock:
            # complete task
            task.complete(result_data={})
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.completed')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.completed', ANY)
            gauge_mock.assert_has_calls([
                call('tasks.task-type-1.1.queue', 0),
                call('tasks.task-type-1.1.processing', 0)
            ], any_order=True)

    def testIncErrorStats(self):
        # create task with claimed status
        task = self._addTask(
            assigned_agent=self.agent,
            claimed=datetime.utcnow()
        )

        with patch.object(statsd, 'incr', return_value=None) as incr_mock, \
                patch.object(statsd, 'timing') as timing_mock,\
                patch.object(statsd, 'gauge') as gauge_mock:
            # complete task
            task.complete(error='test')
            db.session.flush()

            incr_mock.assert_called_once_with('tasks.error')
            timing_mock.assert_called_once_with('tasks.task-type-1.1.error', ANY)
            gauge_mock.assert_has_calls([
                call('tasks.task-type-1.1.queue', 0),
                call('tasks.task-type-1.1.processing', 0)
            ], any_order=True)

    def testCapabilitySummary(self):
        # add three more agents, with different last seen values
        for agent in range(3):
            db.session.add(Agent(
                uuid=str(uuid4()),
                name='test agent 2',
                last_seen=datetime.utcnow() - timedelta(seconds=agent * 1200),  # 0, 1200, 2400
                capabilities=[
                    AgentCapability(type='task-type-1', version=1),
                    AgentCapability(type='task-type-1', version=2),
                    AgentCapability(type='task-type-2', version=3)
                ]
            ))
        db.session.flush()

        summary = list(AgentCapability.summary())
        self.assertEqual(len(summary), 3, "there should be three entries of different capabilities")
        self.assertEqual(len(set(t['type'] for t in summary)), 2, "there should two kinds of capabilities")
        self.assertEqual(len(set((t['type'], t['version']) for t in summary)), 3,
                         "there should be three distinct capability,version pairs")
        self.assertEqual(sum(t['count'] for t in summary), 10, "there should be four capabilities total available.")
        counts = {(t['type'], t['version']): t['count'] for t in summary}
        self.assertEqual(counts[('task-type-1', 1)], 4)
        self.assertEqual(counts[('task-type-1', 2)], 3)
        self.assertEqual(counts[('task-type-2', 3)], 3)

        summary = list(AgentCapability.summary(last_seen_threshold=datetime.utcnow() - timedelta(seconds=2000)))
        counts = {(t['type'], t['version']): t['count'] for t in summary}
        self.assertEqual(counts[('task-type-1', 1)], 3)
        self.assertEqual(counts[('task-type-1', 2)], 2)
        self.assertEqual(counts[('task-type-2', 3)], 2)

    def testIncCapabilityGauges(self):
        with patch.object(statsd, 'gauge', return_value=None) as mock_method:
            AgentCapability.update_gauges()
            mock_method.assert_called_once_with('capability.task-type-1.1', 1)

        self.agent = Agent(
            uuid='de305d54-75b4-431b-adb2-eb6b9e546014',
            name='test agent 2',
            last_seen=datetime.utcnow(),
            capabilities=[
                AgentCapability(type='task-type-1', version=1),
                AgentCapability(type='task-type-1', version=2),
                AgentCapability(type='task-type-2', version=3)
            ]
        )
        db.session.add(self.agent)
        db.session.flush()

        with patch.object(statsd, 'gauge', return_value=None) as mock_method:
            AgentCapability.update_gauges()
            self.assertEqual(mock_method.call_count, 3)
            mock_method.assert_has_calls([
                call('capability.task-type-1.1', 2),
                call('capability.task-type-1.2', 1),
                call('capability.task-type-2.3', 1)
            ], any_order=True)

    def testTaskSummary(self):
        # put some tasks in the queue
        for task_type, version in (('type1', 1), ('type2', 1), ('type1', 1), ('type2', 2)):
            self._addTask(
                uuid=str(uuid4()),
                type=task_type,
                version=version
            )
        # add already completed tasks and claimed tasks, should be included in queue stats with zero value
        self._addTask(uuid=str(uuid4()), completed=datetime.utcnow(), result_data={})
        self._addTask(uuid=str(uuid4()), failed=datetime.utcnow(), error='test')
        self._addTask(uuid=str(uuid4()), claimed=datetime.utcnow(), assigned_agent=self.agent)

        # check queue summary data
        summary = list(Task.task_summary())
        self.assertEqual(len(summary), 4, "there should be four entries of different types!")
        self.assertEqual(len(set(t['type'] for t in summary)), 3, "there should three kinds of types")
        self.assertEqual(len(set((t['type'], t['version']) for t in summary)), 4,
                         "there should be four distinct capability,version pairs")

        # publish queue & processing gauges with statsd
        with patch.object(statsd, 'gauge', return_value=None) as mock_method:
            Task.update_gauges()
            self.assertEqual(mock_method.call_count, 8)
            mock_method.assert_has_calls([
                call('tasks.type1.1.queue', 2),
                call('tasks.type2.1.queue', 1),
                call('tasks.type2.2.queue', 1),
                call('tasks.task-type-1.1.queue', 0),
                call('tasks.type1.1.processing', 0),
                call('tasks.type2.1.processing', 0),
                call('tasks.type2.2.processing', 0),
                call('tasks.task-type-1.1.processing', 1)
            ], any_order=True)
