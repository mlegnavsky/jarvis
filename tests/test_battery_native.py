"""Offline native battery-sale boundaries; acknowledgements are never proof."""
import copy
from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from battery_native import BatterySaleController

TZ = ZoneInfo('Europe/Prague')


class BatteryNativeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 11, 5, 15, 40, tzinfo=TZ).timestamp()
        self.reg = {0: 1280, 98: 1, 109: 175, 111: 1, 130: 0,
                    142: 2, 143: 9300, 145: 0, 146: 255, 213: 200, 219: 200}
        for i, time in enumerate([0, 400, 800, 1200, 1600, 2000]):
            self.reg.update({148 + i: time, 154 + i: 12000, 166 + i: 30, 172 + i: 0})
        self.original = dict(self.reg)
        self.states = dict(healthy=True, reported_at=self.now, soc=90, grid_w=20,
                           battery_w=0, pv_w=0, net_price=7, voltage_v=55, current_a=0)
        first = datetime(2026, 11, 5, 15, 30, tzinfo=TZ).timestamp()
        self.quotes = [dict(start=first + 900 * i, end=first + 900 * (i + 1), net=7)
                       for i in range(8)]
        self.writes, self.events, self.saves = [], [], []
        self.saved = {}
        self.fail_addresses = set()
        self.audit_hook = None
        self.fail_save = False
        self.fail_event = False

        async def read():
            return {'clock': datetime.fromtimestamp(self.now, TZ), 'registers': dict(self.reg)}

        async def write(address, value):
            self.writes.append((address, value))
            if address in self.fail_addresses:
                raise OSError('simulated native write failure')
            self.reg[address] = value

        async def save(record):
            if self.fail_save:
                raise OSError('simulated persistence failure')
            self.saved = copy.deepcopy(record)
            self.saves.append(copy.deepcopy(record))

        async def event(kind, payload):
            self.events.append((kind, copy.deepcopy(payload)))
            if self.audit_hook:
                await self.audit_hook(kind, payload)
            if self.fail_event:
                raise OSError('simulated audit failure')

        self.read, self.write, self.save, self.event = read, write, save, event
        self.controller = self.make_controller()

    def make_controller(self, saved=None):
        return BatterySaleController(self.read, self.write, lambda: dict(self.states),
                                     self.save, self.event, clock=lambda: self.now, saved=saved)

    async def start(self, **changes):
        params = dict(power_w=5000, duration_minutes=5, minimum_soc=60,
                      quotes=self.quotes, purpose='manual')
        params.update(changes)
        await self.controller.start(**params)

    async def advance(self, seconds=1, **values):
        self.now += seconds
        self.states.update(reported_at=self.now, **values)
        await self.controller.tick()

    async def enable(self):
        self.now = self.controller.record['start']
        self.states['reported_at'] = self.now
        await self.controller.tick()

    async def finish_stop(self):
        await self.advance(grid_w=20, battery_w=0, current_a=0)
        self.assertFalse(self.controller.active)
        self.assertTrue(self.controller.last_stop['stop_verified'])

    async def observe_export(self):
        await self.advance(1, grid_w=-4000, battery_w=4500, current_a=82)
        await self.advance(10)
        await self.advance(10)
        self.assertTrue(self.controller.observed)

    async def test_automatic_native_read_timeout_produces_recoverable_confirmed_stop(self):
        from telemetry_health import recoverable_battery_stop
        await self.start(purpose='automatic');await self.enable()
        self.states['health']={'healthy':True,'transient_only':False,'issues':[]}
        real=self.controller.native_read;failed=False
        async def timeout_once():
            nonlocal failed
            if not failed:
                failed=True;raise TimeoutError('Native snapshot timeout at142/36')
            return await real()
        self.controller.native_read=timeout_once
        await self.advance(31)
        await self.finish_stop()
        proof=self.controller.last_stop
        self.assertTrue(recoverable_battery_stop(proof),str(proof))
        self.assertEqual(proof['failure_context']['health']['issues'][-1]['source'],'battery_native_audit')
        self.assertEqual([self.reg[166+i] for i in range(6)],[30]*6)

    async def test_native_read_timeout_crossing_plan_end_still_completes_deadline(self):
        await self.start(purpose='automatic');await self.enable()
        self.states['health']={'healthy':True,'transient_only':False,'issues':[]}
        self.now=self.controller.record['end']-1;self.states['reported_at']=self.now
        real=self.controller.native_read;failed=False
        async def timeout_once():
            nonlocal failed
            if not failed:
                failed=True;self.now+=2;self.states['reported_at']=self.now
                raise TimeoutError('snapshot crossed deadline')
            return await real()
        self.controller.native_read=timeout_once
        await self.controller.tick();await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'],'deadline')

    async def test_native_timeout_cannot_mask_new_export_limit_violation(self):
        from telemetry_health import recoverable_battery_stop
        await self.start(purpose='automatic');await self.enable()
        self.states['health']={'healthy':True,'transient_only':False,'issues':[]}
        real=self.controller.native_read;failed=False
        async def timeout_once():
            nonlocal failed
            if not failed:
                failed=True;self.states['grid_w']=-9600;raise TimeoutError('snapshot')
            return await real()
        self.controller.native_read=timeout_once
        await self.advance(31)
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'],'export_limit')
        self.assertFalse(recoverable_battery_stop(self.controller.last_stop))

    async def test_ha_sale_rejects_actual_native_reserve_below_fixed_thirty_without_writes(self):
        for i in range(6):self.reg[166+i]=10
        for purpose in ('automatic','manual'):
            with self.subTest(purpose=purpose),self.assertRaises(ValueError):
                await self.start(purpose=purpose,ha_controlled=True)
        self.assertFalse(self.writes);self.assertFalse(self.controller.active)

    async def test_automatic_sale_preserves_inverter_schedule_and_soc(self):
        await self.start(purpose='automatic')
        await self.enable()
        self.assertEqual([self.reg[166+i] for i in range(6)], [30]*6)
        self.assertFalse(any(a in range(148,178) or a in (109,146) for a,v in self.writes))
        await self.advance(soc=60)
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'], 'reserve')
        self.assertFalse(any(a in range(148,178) or a in (109,146) for a,v in self.writes))

    async def test_automatic_sale_stops_at_ha_deadline(self):
        await self.start(purpose='automatic')
        await self.enable()
        self.now = self.controller.record['end']
        self.states['reported_at'] = self.now
        await self.controller.tick()
        self.assertEqual(self.reg[142], 2)
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'], 'deadline')

    async def test_ha_automatic_starts_without_five_minute_native_delay(self):
        await self.start(purpose='automatic')
        self.assertEqual(self.controller.record['start'],self.now)
        await self.controller.tick()
        self.assertEqual(self.reg[142],0)
        self.assertEqual([self.reg[166+i] for i in range(6)],[30]*6)

    async def test_explicit_manual_ha_control_never_reprograms_inverter(self):
        await self.start(purpose='manual',ha_controlled=True)
        await self.controller.tick()
        self.assertEqual(self.controller.record['start'],self.now)
        self.assertFalse(any(address in range(148,178) or address in (109,146) for address,value in self.writes))

    async def test_ha_transaction_rejects_a_program_write_even_if_called_accidentally(self):
        await self.start(purpose='automatic')
        before=list(self.writes)
        with self.assertRaises(ValueError):await self.controller._write(166,60)
        self.assertEqual(self.reg[166],30);self.assertEqual(before,self.writes)

    async def test_ha_automatic_can_use_last_three_minutes_of_business_block(self):
        await self.start(purpose='automatic',duration_minutes=3,window_end=self.now+180)
        self.assertEqual(self.controller.record['end'],self.now+180)

    async def test_ha_deadline_needs_no_positive_price_after_its_end(self):
        end=self.now+300
        self.quotes=[q for q in self.quotes if q['start']<end]
        await self.start(purpose='automatic',window_end=end)
        self.assertEqual(self.controller.record['end'],end)

    async def test_health_failure_proof_preserves_exact_measurement_cause(self):
        await self.start(purpose='automatic')
        await self.enable()
        self.states.update(healthy=False,health={'healthy':False,'transient_only':True,
            'issues':[{'code':'stale','entity_id':'sensor.inverter_battery','age_seconds':31}]})
        await self.advance()
        self.states['healthy']=True
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['failure_context']['health']['issues'][0]['code'],'stale')

    async def test_electrical_stale_proof_retains_original_channel_timestamp_and_price(self):
        await self.start(purpose='automatic')
        await self.enable()
        self.states.update(health={'healthy':True,'transient_only':False,'issues':[]},
                           voltage_reported_at=self.now-31,current_reported_at=self.now)
        failed_stamp=self.states['voltage_reported_at']
        await self.advance()
        self.states.update(voltage_reported_at=self.now,current_reported_at=self.now)
        await self.finish_stop()
        proof=self.controller.last_stop
        self.assertEqual(proof['reason'],'electrical_stale')
        self.assertEqual(proof['failure_context']['voltage_reported_at'],failed_stamp)
        self.assertEqual(proof['failure_context']['net_price'],7)
        self.assertEqual(proof['failure_context']['health']['issues'][0]['entity_id'],'sensor.inverter_battery_voltage')

    async def test_plan_and_before_image_are_durable_before_any_device_write(self):
        async def write(address, value):
            self.assertEqual(self.saved['before']['166'], 30)
            self.assertEqual(self.saved['plan']['week_mask'], 255)
            self.assertIn(str(address), self.saved['pending'])
            self.assertEqual(self.events[-1][0], 'battery_native_write_intent')
            await self.write(address, value)
        self.controller.native_write = write
        await self.start()
        self.assertEqual(self.writes[:2], [(143, 5000), (109, 175)])
        self.assertEqual(self.writes[-1], (146, 255))
        self.assertEqual([self.reg[166 + i] for i in range(6)], [100, 60, 100, 100, 100, 100])
        self.assertEqual([self.reg[172 + i] for i in range(6)], [0] * 6)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.reg[145], 0)
        await self.enable()
        self.assertEqual(self.writes[-1], (142, 0))
        self.assertFalse(self.controller.observed)
        self.assertFalse(self.controller.record['production_verified'])

    async def test_invalid_profile_or_ordinary_schedule_has_no_write(self):
        for address, value in [(0, 1), (98, 0), (111, 0), (130, 1), (142, 0),
                               (145, 1), (146, 17), (166, 60), (155, 999), (173, 32)]:
            self.reg = dict(self.original)
            self.reg[address] = value
            with self.subTest(address=address), self.assertRaises(ValueError):
                await self.start()
            self.assertEqual(self.writes, [])

    async def test_grid_bms_limit_is_required_and_high_maximum_is_not_the_pack_cap(self):
        self.reg[213]=50;self.reg[219]=300
        await self.start()
        self.assertEqual(self.reg[109],50)
        self.assertEqual(self.controller.record['plan']['current_limit_a'],50)

    async def test_unknown_dynamic_or_maximum_bms_limit_cannot_start(self):
        for address in (213,219):
            for value in (0,65535):
                self.reg=dict(self.original);self.reg[address]=value
                with self.assertRaises(ValueError):await self.start()
                self.assertEqual(self.writes,[])

    async def test_low_bms_limits_current_and_total_battery_dc_power(self):
        self.reg[219] = 10
        await self.start()
        self.assertEqual(self.reg[109], 10)
        self.assertEqual(self.reg[155], 550)
        self.assertEqual(self.reg[143], 5000)

    async def test_zero_bms_or_missing_full_before_image_cannot_start(self):
        self.reg[219] = 0
        with self.assertRaises(ValueError):
            await self.start()
        self.assertEqual(self.writes, [])
        self.reg[219] = 200
        del self.reg[148]
        with self.assertRaises(ValueError):
            await self.start()
        self.assertEqual(self.writes, [])

    async def test_initial_persistence_failure_cannot_touch_inverter(self):
        self.fail_save = True
        with self.assertRaises(OSError):
            await self.start()
        self.assertEqual(self.writes, [])
        self.assertFalse(self.controller.active)

    async def test_health_change_during_audit_prevents_cap_write(self):
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 143 and payload['value'] == 5000:
                self.states['healthy'] = False
        self.audit_hook = hook
        with self.assertRaises(ValueError):
            await self.start()
        self.assertNotIn((143, 5000), self.writes)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.reg[143], 0)

    async def test_expired_arm_deadline_during_audit_cannot_arm_week_mask(self):
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 146:
                self.now = self.controller.record['arm_until']
                self.states['reported_at'] = self.now
        self.audit_hook = hook
        with self.assertRaises(ValueError):
            await self.start()
        self.assertNotIn((146, 17), self.writes)

    async def test_stale_electrical_sample_during_enable_audit_cannot_enable(self):
        await self.start()
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 142 and payload['value'] == 0:
                self.states['voltage_reported_at'] = self.now - 30
        self.audit_hook = hook
        await self.enable()
        self.assertNotIn((142, 0), self.writes)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.controller.record['stop_reason'], 'electrical_stale')

    async def test_late_enable_audit_cannot_enable_after_native_end(self):
        await self.start()
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 142 and payload['value'] == 0:
                self.now = self.controller.record['end']
                self.states['reported_at'] = self.now
        self.audit_hook = hook
        await self.enable()
        self.assertNotIn((142, 0), self.writes)

    async def test_current_price_reserve_health_and_export_caps_each_force_stop(self):
        for values, expected in [(dict(net_price=0), 'price'), (dict(soc=60), 'reserve'),
                                 (dict(healthy=False), 'health'), (dict(current_a=181), 'current_limit'),
                                 (dict(battery_w=10251), 'battery_limit'),
                                 (dict(grid_w=-5301), 'export_limit')]:
            with self.subTest(values=values):
                await self.asyncSetUp()
                await self.start()
                await self.enable()
                await self.advance(**values)
                self.assertEqual(self.reg[142], 2)
                self.assertEqual(self.controller.record['stop_reason'], expected)

    async def test_replayed_measurement_or_pv_only_export_is_not_battery_sale_proof(self):
        await self.start()
        await self.enable()
        await self.advance(1, grid_w=-4000, battery_w=50, pv_w=4000)
        await self.advance(25)
        self.assertFalse(self.controller.observed)
        self.states.update(grid_w=-4000, battery_w=4500, pv_w=0, current_a=82)
        stamp = self.now
        for _ in range(3):
            self.now += 5
            self.states['reported_at'] = stamp
            await self.controller.tick()
        self.assertFalse(self.controller.observed)

    async def test_native_end_is_observed_without_any_boundary_stop_write(self):
        await self.start()
        await self.enable()
        await self.observe_export()
        self.now = self.controller.record['end'] - 10
        self.states['reported_at'] = self.now
        await self.controller.tick()
        count = len(self.writes)
        await self.advance(11, grid_w=20, battery_w=0, current_a=0)
        self.assertEqual(len(self.writes), count)
        self.assertTrue(self.controller.record['native_expiry_observed'])
        self.assertFalse(self.controller.record['production_verified'])
        await self.advance(59)
        self.assertEqual(self.reg[142], 2)
        await self.finish_stop()
        self.assertTrue(self.controller.last_stop['native_expiry_observed'])
        self.assertEqual(self.controller.last_stop['purpose'], 'manual')
        self.assertEqual(self.controller.last_stop['reason'], 'deadline')

    async def test_pv_explained_export_after_end_can_prove_battery_expiry(self):
        await self.start()
        await self.enable()
        await self.observe_export()
        self.now = self.controller.record['end'] - 10
        self.states['reported_at'] = self.now
        await self.controller.tick()
        await self.advance(11, grid_w=-2000, pv_w=2000, battery_w=0, current_a=0)
        self.assertTrue(self.controller.record['native_expiry_observed'])

    async def test_early_export_end_or_house_masked_discharge_cannot_prove_expiry(self):
        for early, battery in [(True, 0), (False, 500)]:
            with self.subTest(early=early, battery=battery):
                await self.asyncSetUp()
                await self.start()
                await self.enable()
                await self.observe_export()
                if not early:
                    self.now = self.controller.record['end'] - 10
                    self.states['reported_at'] = self.now
                    await self.controller.tick()
                self.now = self.controller.record['end'] + 1
                self.states.update(reported_at=self.now, grid_w=500, battery_w=battery, current_a=0)
                await self.controller.tick()
                self.assertFalse(self.controller.record['native_expiry_observed'])

    async def test_cap_failure_still_attempts_mode_en_and_all_flags(self):
        await self.start()
        await self.enable()
        self.writes.clear()
        self.fail_addresses.add(143)
        await self.controller.stop('manual')
        self.assertEqual(self.writes[0], (142, 2))
        self.assertEqual(self.reg[142], 2)
        self.assertIn((145, 0), self.writes)
        self.assertTrue(all((172 + i, 0) in self.writes for i in range(6)))
        self.assertTrue(self.controller.active)
        self.fail_addresses.clear()
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'], 'manual')

    async def test_audit_and_save_failures_cannot_prevent_protective_stop(self):
        await self.start()
        await self.enable()
        self.fail_save = self.fail_event = True
        await self.controller.stop('manual')
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.reg[143], 0)
        self.assertEqual(self.reg[145], 0)
        self.assertEqual([self.reg[172 + i] for i in range(6)], [0] * 6)
        self.fail_save = self.fail_event = False
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'], 'manual')

    async def test_stop_waits_for_new_stopped_grid_measurement_before_restoring(self):
        await self.start()
        await self.enable()
        self.states.update(grid_w=-4000, battery_w=4500, current_a=82)
        await self.controller.stop('manual')
        self.assertEqual(self.reg[166], 100)
        await self.advance(grid_w=-2000)
        self.assertEqual(self.reg[166], 100)
        await self.finish_stop()
        self.assertEqual(self.reg, self.original)
        self.assertEqual(self.saved, {})

    async def test_restart_never_resumes_an_armed_or_selling_program(self):
        await self.start()
        await self.enable()
        saved = copy.deepcopy(self.saved)
        self.controller = self.make_controller(saved)
        self.writes.clear()
        await self.advance()
        self.assertEqual(self.writes[0], (142, 2))
        self.assertNotIn((142, 0), self.writes)
        await self.finish_stop()
        self.assertEqual(self.controller.last_stop['reason'], 'recovery')

    async def test_partial_preparation_failure_retains_original_before_image(self):
        self.fail_addresses.add(168)
        with self.assertRaises(OSError):
            await self.start()
        self.assertEqual(self.controller.record['before']['166'], 30)
        self.assertEqual(self.reg[142], 2)
        self.fail_addresses.clear()
        await self.finish_stop()
        self.assertEqual(self.reg, self.original)
        self.assertEqual(self.controller.last_stop['reason'], 'start_failed')

    async def test_owner_soc_time_and_lower_current_and_cap_survive_stop(self):
        await self.start()
        await self.enable()
        self.reg.update({166: 45, 148: 100, 109: 40, 143: 1000})
        await self.controller.stop('manual')
        await self.finish_stop()
        for address, expected in [(166, 45), (148, 100), (109, 40), (143, 1000)]:
            self.assertEqual(self.reg[address], expected)
            self.assertIn(str(address), self.controller.last_stop['conflicts'])
        self.assertEqual(self.controller.last_stop['reason'], 'manual')

    async def test_periodic_native_change_stops_and_does_not_overwrite_owner_soc(self):
        await self.start()
        await self.enable()
        self.reg[166] = 42
        await self.advance(31)
        self.assertEqual(self.controller.record['stop_reason'], 'native_conflict')
        await self.finish_stop()
        self.assertEqual(self.reg[166], 42)
        self.assertIn('166', self.controller.last_stop['conflicts'])

    async def test_lower_bms_during_run_stops_and_limits_restored_current(self):
        await self.start()
        await self.enable()
        self.reg[219] = 35
        await self.advance(31)
        self.assertEqual(self.controller.record['stop_reason'], 'current_limit')
        await self.finish_stop()
        self.assertEqual(self.reg[109], 35)

    async def test_native_write_ack_without_matching_snapshot_cannot_clear_record(self):
        await self.start()
        await self.enable()
        await self.controller.stop('manual')
        async def ignore_restore(address, value):
            if address == 166 and value == 30:
                return
            await self.write(address, value)
        self.controller.native_write = ignore_restore
        await self.advance()
        self.assertTrue(self.controller.active)
        self.assertIsNone(self.controller.last_stop)
        self.controller.native_write = self.write
        await self.finish_stop()

    async def test_business_end_and_initial_approved_power_are_enforced(self):
        end = datetime(2026, 11, 5, 16, 2, tzinfo=TZ).timestamp()
        await self.start(duration_minutes=60, window_end=end, maximum_power_w=9300)
        self.assertEqual(self.controller.record['end'], datetime(2026, 11, 5, 16, 0, tzinfo=TZ).timestamp())
        self.assertEqual(self.controller.record['maximum_power_w'], 9300)

    async def test_adjustment_changes_only_grid_cap_and_never_battery_limits(self):
        await self.start(maximum_power_w=9300)
        await self.enable()
        previous = {a: self.reg[a] for a in self.reg if a != 143}
        self.writes.clear()
        await self.controller.adjust_power(7500)
        self.assertEqual(self.writes, [(143, 7500)])
        self.assertEqual(self.controller.record['power_w'], 7500)
        self.assertEqual(self.controller.record['expected']['143'], 7500)
        self.assertEqual({a: self.reg[a] for a in previous}, previous)
        await self.advance(31)
        self.assertEqual(self.reg[142], 0)
        with self.assertRaises(ValueError):
            await self.controller.adjust_power(9301)

    async def test_adjustment_is_guarded_after_audit_and_zero_uses_safe_stop(self):
        await self.start()
        await self.enable()
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 143 and payload['value'] == 4000:
                self.states['net_price'] = -1
        self.audit_hook = hook
        await self.controller.adjust_power(4000)
        self.assertNotIn((143, 4000), self.writes)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.controller.record['stop_reason'], 'price')
        self.audit_hook = None
        self.states['net_price'] = 7
        await self.finish_stop()
        await self.start()
        await self.enable()
        self.writes.clear()
        await self.controller.adjust_power(0)
        self.assertEqual(self.writes[0], (142, 2))
        self.assertEqual(self.controller.record['stop_reason'], 'budget')

    async def test_owner_change_during_restore_audit_is_preserved(self):
        await self.start()
        await self.enable()
        await self.controller.stop('manual')
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 166 and payload['value'] == 30:
                self.reg[166] = 45
        self.audit_hook = hook
        await self.advance()
        self.assertEqual(self.reg[166], 45)
        self.assertTrue(self.controller.active)
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[166], 45)
        self.assertIn('166', self.controller.last_stop['conflicts'])

    async def test_owner_lower_cap_during_adjust_audit_is_not_overwritten(self):
        await self.start()
        await self.enable()
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 143 and payload['value'] == 4000:
                self.reg[143] = 100
        self.audit_hook = hook
        await self.controller.adjust_power(4000)
        self.assertNotIn((143, 4000), self.writes)
        self.assertEqual(self.controller.record['stop_reason'], 'native_conflict')
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[143], 100)

    async def test_bms_lowered_during_current_restore_audit_prevents_high_write(self):
        self.reg[219] = 100
        await self.start()
        await self.enable()
        await self.controller.stop('manual')
        self.reg[219] = 200
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 109 and payload['value'] == 175:
                self.reg[219] = 50
        self.audit_hook = hook
        self.writes.clear()
        await self.advance()
        self.assertNotIn((109, 175), self.writes)
        self.assertTrue(self.controller.active)
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[109], 50)

    async def test_bms_lowered_during_current_prepare_audit_prevents_high_write(self):
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 109 and payload['value'] == 175:
                self.reg[219] = 50
        self.audit_hook = hook
        with self.assertRaises(ValueError):
            await self.start()
        self.assertNotIn((109, 175), self.writes)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.controller.record['stop_reason'], 'start_failed')
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[109], 50)

    async def test_dynamic_bms_lowered_during_current_restore_audit_prevents_high_write(self):
        self.reg[213] = 100
        await self.start()
        await self.enable()
        await self.controller.stop('manual')
        self.reg[213] = 200
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 109 and payload['value'] == 175:
                self.reg[213] = 50
        self.audit_hook = hook
        self.writes.clear()
        await self.advance()
        self.assertNotIn((109, 175), self.writes)
        self.assertTrue(self.controller.active)
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[109], 50)

    async def test_dynamic_bms_lowered_during_current_prepare_audit_prevents_high_write(self):
        async def hook(kind, payload):
            if kind == 'battery_native_write_intent' and payload['address'] == 109 and payload['value'] == 175:
                self.reg[213] = 50
        self.audit_hook = hook
        with self.assertRaises(ValueError):
            await self.start()
        self.assertNotIn((109, 175), self.writes)
        self.assertEqual(self.reg[142], 2)
        self.assertEqual(self.controller.record['stop_reason'], 'start_failed')
        self.audit_hook = None
        await self.finish_stop()
        self.assertEqual(self.reg[109], 50)

    async def test_measured_eleven_second_clock_lag_does_not_abort_before_export_enable(self):
        from datetime import timedelta
        self.states['soc']=94
        await self.start(power_w=500, minimum_soc=90, purpose='commission', maximum_power_w=500)
        read=self.controller.native_read
        async def delayed_clock():
            result=await read();result['clock']-=timedelta(seconds=11);return result
        self.controller.native_read=delayed_clock
        await self.enable()
        self.assertEqual(self.reg[142],0)
        self.assertEqual(self.controller.record['phase'],'measuring')

    async def test_commission_allows_the_normal_house_load_under_three_kw(self):
        self.states.update(soc=94,battery_w=1923,current_a=36.12)
        await self.start(power_w=500, minimum_soc=90, purpose='commission', maximum_power_w=500)
        self.assertEqual(self.reg[109],60)
        self.assertEqual(self.reg[155],3000)
        self.assertEqual(self.reg[143],500)
        self.assertEqual(self.reg[167],90)

    async def test_commission_respects_lower_bms_current_and_rejects_excess_house_load(self):
        self.reg[213]=35;self.states['soc']=94
        await self.start(power_w=500, minimum_soc=90, purpose='commission', maximum_power_w=500)
        self.assertEqual(self.reg[109],35)
        self.assertLessEqual(self.reg[155],35*55)
        await self.controller.stop('manual');await self.finish_stop()
        self.reg[213]=200;self.states.update(battery_w=4000,current_a=75)
        with self.assertRaises(ValueError):
            await self.start(power_w=500, minimum_soc=90, purpose='commission', maximum_power_w=500)

    async def test_commission_is_fixed_bounded_and_proof_identifies_actual_limits(self):
        self.states['soc'] = 96
        await self.start(power_w=500, minimum_soc=90, purpose='commission', maximum_power_w=500)
        self.assertEqual(self.reg[109], 60)
        self.assertEqual(self.reg[155], 3000)
        await self.enable()
        await self.controller.stop('manual')
        await self.finish_stop()
        proof = self.controller.last_stop
        self.assertEqual(proof['power_w'], 500)
        self.assertEqual(proof['minimum_soc'], 90)
        self.assertEqual(proof['phase'], 'complete')
        self.assertIs(proof['observed'], False)
        self.assertIs(proof['native_expiry_observed'], False)
        self.assertIs(proof['stop_verified'], True)

    async def test_explicit_60_commission_programs_zero_power_outside_slot_and_keeps_bounds(self):
        self.states['soc']=63
        await self.start(power_w=500,minimum_soc=60,purpose='commission',maximum_power_w=500)
        self.assertEqual([self.reg[154+i] for i in range(6)],[0,3000,0,0,0,0])
        self.assertEqual(self.reg[109],60)
        self.assertEqual(self.reg[143],500)
        self.assertEqual(self.reg[167],60)
        await self.controller.stop('manual');await self.finish_stop()
        self.assertIs(self.controller.last_stop['native_power_fence'],True)
        self.assertEqual(self.reg,self.original)

    async def test_explicit_two_kw_commission_is_bounded_for_daylight_battery_proof(self):
        self.states['soc']=64
        await self.start(power_w=2000,minimum_soc=60,purpose='commission',maximum_power_w=2000)
        self.assertEqual(self.reg[143],2000)
        self.assertEqual(self.reg[109],60)
        self.assertEqual([self.reg[154+i] for i in range(6)],[0,3000,0,0,0,0])
        await self.controller.stop('manual');await self.finish_stop()
        self.assertEqual(self.reg,self.original)

    async def test_empty_timeout_keeps_diagnostic_type_through_protective_restoration(self):
        await self.start();await self.enable()
        read=self.controller.native_read
        async def once():
            self.controller.native_read=read
            raise TimeoutError()
        self.controller.native_read=once
        await self.advance(31)
        self.assertIn('TimeoutError',self.controller.record.get('failure_detail',''))
        await self.finish_stop()
        self.assertIn('TimeoutError',self.controller.last_stop['failure_detail'])

    async def test_commission_rejects_any_broader_scope(self):
        self.states['soc'] = 96
        for changes in [dict(power_w=501), dict(duration_minutes=10), dict(minimum_soc=59), dict(minimum_soc=61),
                        dict(maximum_power_w=9300)]:
            params = dict(power_w=500, duration_minutes=5, minimum_soc=90,
                          purpose='commission', maximum_power_w=500)
            params.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                await self.start(**params)
            self.assertEqual(self.writes, [])


if __name__ == '__main__':
    unittest.main()
