import tempfile
import unittest
from pathlib import Path

from app.ha import HAClient, UpstreamError
from app.policy import APIError
from tests.ha_fixture import HomeFixture
from app.audit import Audit


class AutomationTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = HomeFixture()
        self.ha = HAClient('supervisor-test', await self.fixture.start())

    async def asyncTearDown(self):
        await self.ha.close()
        await self.fixture.close()

    async def test_missing_definition_is_distinct_from_missing_api(self):
        self.assertIsNone(await self.ha.automation('GET', 'jarvis_test'))
        self.fixture.automation_api_missing = True
        with self.assertRaises(UpstreamError):
            await self.ha.automation('GET', 'jarvis_test')

    async def test_write_read_and_rejected_config(self):
        config = {'alias': 'Test', 'initial_state': False, 'triggers': [], 'actions': []}
        await self.ha.automation('POST', 'jarvis_test', config)
        self.assertEqual((await self.ha.automation('GET', 'jarvis_test'))['alias'], 'Test')
        self.fixture.reject_automation = True
        with self.assertRaises(APIError) as error:
            await self.ha.automation('POST', 'jarvis_test', config)
        self.assertEqual(error.exception.code, 'automation_config_rejected')
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_transport_rejects_unbounded_target(self):
        for identifier in ('../config', 'x/y', '', 'x?y', 'a'*129):
            with self.assertRaises(APIError):
                await self.ha.automation('GET', identifier)
        with self.assertRaises(APIError):
            await self.ha.automation('PATCH', 'test')


class ManagementTests(AutomationTransportTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        from app.management import Management
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.options = {'maintenance_enabled': True, 'writes_enabled': True}
        self.management = Management(self.ha, self.options, self.directory, Audit(self.directory))
        self.config = {'alias': 'Test', 'initial_state': False, 'triggers': [], 'actions': []}

    async def test_save_backup_delete_and_restore_with_restart_safe_replay(self):
        from app.management import Management
        status, saved = await self.management.change('save', 'jarvis_test', 'missing', self.config, 'save-1')
        self.assertEqual(status, 200)
        self.assertTrue(saved['verified'])
        revision = (await self.management.get('jarvis_test'))['revision']
        self.management = Management(self.ha, self.options, self.directory, Audit(self.directory))
        self.assertEqual(await self.management.change('save', 'jarvis_test', 'missing', self.config, 'save-1'), (status, saved))
        self.assertEqual(len(self.fixture.effects), 1)
        _, deleted = await self.management.change('delete', 'jarvis_test', revision, {}, 'delete-1')
        self.assertTrue(deleted['verified'])
        self.assertIsNone(self.fixture.automations.get('jarvis_test'))
        _, restored = await self.management.change('restore', 'jarvis_test', 'missing', {}, 'restore-1', 'delete-1')
        self.assertTrue(restored['verified'])
        self.assertFalse(self.fixture.automations['jarvis_test']['initial_state'])

    async def test_conflict_and_stale_revision_have_no_effect(self):
        await self.management.change('save', 'jarvis_test', 'missing', self.config, 'save-1')
        for key, revision, config in [('save-1', 'missing', {**self.config, 'alias': 'Changed'}),
                                      ('save-2', 'missing', self.config)]:
            with self.assertRaises(APIError) as error:
                await self.management.change('save', 'jarvis_test', revision, config, key)
            self.assertEqual(error.exception.status, 409)
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_disabled_draft_and_permissions_are_required(self):
        for config in ({**self.config, 'initial_state': True}, {**self.config, 'id': 'different'}, {}):
            with self.assertRaises(APIError):
                await self.management.change('save', 'jarvis_test', 'missing', config, 'bad')
        self.options['writes_enabled'] = False
        with self.assertRaises(APIError):
            await self.management.change('save', 'jarvis_test', 'missing', self.config, 'bad')
        self.assertEqual(self.fixture.effects, [])

    async def test_backup_exists_before_effect_and_uncertain_write_is_not_retried(self):
        original = self.ha.automation
        async def interrupted(method, identifier, config=None):
            if method == 'POST':
                with self.management.db() as db:
                    row = db.execute('SELECT before_config FROM changes WHERE key=?', ('uncertain',)).fetchone()
                self.assertIsNotNone(row)
                await original(method, identifier, config)
                raise UpstreamError('connection_lost_after_write')
            return await original(method, identifier, config)
        self.ha.automation = interrupted
        first = await self.management.change('save', 'jarvis_test', 'missing', self.config, 'uncertain')
        self.assertEqual(first[0], 502)
        self.assertFalse(first[1]['verified'])
        self.assertEqual(await self.management.change('save', 'jarvis_test', 'missing', self.config, 'uncertain'), first)
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_interrupted_reserved_request_never_replays(self):
        import asyncio
        original = self.ha.automation
        async def cancelled(method, identifier, config=None):
            if method == 'POST':
                raise asyncio.CancelledError
            return await original(method, identifier, config)
        self.ha.automation = cancelled
        with self.assertRaises(asyncio.CancelledError):
            await self.management.change('save', 'jarvis_test', 'missing', self.config, 'cancelled')
        with self.assertRaises(APIError) as error:
            await self.management.change('save', 'jarvis_test', 'missing', self.config, 'cancelled')
        self.assertEqual(error.exception.code, 'management_outcome_unknown')

    async def test_invalid_definition_rejected_by_ha_and_backup_kept(self):
        self.fixture.reject_automation = True
        status, response = await self.management.change('save', 'jarvis_test', 'missing', self.config, 'invalid')
        self.assertEqual(status, 400)
        self.assertFalse(response['verified'])
        self.assertEqual(self.fixture.effects, [])

    async def test_restore_preserves_old_fields_but_sets_initial_state_false(self):
        original = {**self.config, 'id': 'jarvis_test', 'initial_state': True, 'variables': {'old': 1}}
        self.fixture.automations['jarvis_test'] = original
        current = await self.management.get('jarvis_test')
        await self.management.change('save', 'jarvis_test', current['revision'], self.config, 'edit')
        self.assertNotIn('variables', self.fixture.automations['jarvis_test'])
        current = await self.management.get('jarvis_test')
        _, result = await self.management.change('restore', 'jarvis_test', current['revision'], {}, 'undo', 'edit')
        self.assertTrue(result['verified'])
        self.assertEqual(self.fixture.automations['jarvis_test'], {**original, 'initial_state': False})

    async def test_readback_failure_is_not_reported_as_success(self):
        original = self.ha.automation
        async def lost_readback(method, identifier, config=None):
            if method == 'GET' and self.fixture.effects:
                raise UpstreamError('lost_readback')
            return await original(method, identifier, config)
        self.ha.automation = lost_readback
        status, result = await self.management.change('save', 'jarvis_test', 'missing', self.config, 'readback')
        self.assertEqual(status, 502)
        self.assertFalse(result['verified'])
        self.assertEqual(len(self.fixture.effects), 1)

    async def test_maintenance_disabled_blocks_reads_and_writes(self):
        self.options['maintenance_enabled'] = False
        for operation in (self.management.get('test'), self.management.list(), self.management.diagnostics(),
                          self.management.change('save', 'test', 'missing', self.config, 'disabled')):
            with self.assertRaises(APIError) as error:
                await operation
            self.assertEqual(error.exception.code, 'maintenance_disabled')
        self.assertEqual(self.fixture.effects, [])

    async def test_full_journal_refuses_new_changes_but_keeps_read_and_replay(self):
        first = await self.management.change('save', 'jarvis_test', 'missing', self.config, 'first')
        with self.management.db() as db:
            db.executemany('INSERT INTO changes VALUES (?,?,?,?,?,?)',
                           [('fill-'+str(i), 'fingerprint', 'test', 'null', 200, '{}') for i in range(999)])
        diagnostics = await self.management.diagnostics()
        self.assertEqual(diagnostics['management_journal']['remaining'], 0)
        self.assertEqual(await self.management.change('save', 'jarvis_test', 'missing', self.config, 'first'), first)
        current = await self.management.get('jarvis_test')
        with self.assertRaises(APIError) as error:
            await self.management.change('delete', 'jarvis_test', current['revision'], {}, 'new')
        self.assertEqual(error.exception.code, 'management_journal_full')
        self.assertEqual(len(self.fixture.effects), 1)
