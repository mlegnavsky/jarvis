"""Serialized native battery-sale I/O, without any production-unlock policy.

HA production leaves the ordinary house program unchanged and writes only export
controls. Explicit native maintenance and saved legacy transactions retain their
separate bounded schedule and cleanup path. A weekly mask is not a one-shot timer.
"""
import asyncio
import copy
from datetime import datetime
import math
import time

try:
    from .native_plan import battery_window_plan,native_clock_acceptable
except ImportError:
    from native_plan import battery_window_plan,native_clock_acceptable

WRITABLE = {109, 142, 143, 145, 146, *range(148, 160), *range(166, 178)}
PROFILE = {0, 98, 111, 130, 213, 219}
PROTECTIVE = [(142, 2), (143, 0), (145, 0), *((172 + i, 0) for i in range(6))]


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _bms_limit(registers):
    dynamic, maximum = registers.get(213), registers.get(219)
    if any(type(v) is not int or not 1 <= v < 65535 for v in (dynamic, maximum)):
        raise ValueError(f'Unknown native BMS limits:213={dynamic},219={maximum}')
    return min(200, dynamic, maximum)


class _Guard(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class BatterySaleController:
    """Callbacks are awaited; callers must provide durable save/event sinks.

    Telemetry uses signed grid W (+import), battery W/A (+discharge), PV W,
    voltage_v, SOC, healthy and reported_at. Optional voltage_reported_at and
    current_reported_at otherwise inherit reported_at. Samples must be younger
    than 30 seconds. Every persisted active record is cleanup-only after restart.
    """

    def __init__(self, native_read, native_write, telemetry, save, event,
                 clock=time.time, saved=None):
        self.native_read, self.native_write = native_read, native_write
        self.telemetry, self.save, self.event = telemetry, save, event
        self.clock = clock
        self.record = copy.deepcopy(saved or {})
        self.error = ''
        self.last_stop = None
        self._lock = asyncio.Lock()
        if self.active:
            self.record['phase'] = 'stopping'
            self.record.setdefault('stop_reason', 'recovery')
            self.record.setdefault('pending', {})
            self.record.setdefault('conflicts', {})

    @property
    def active(self):
        return bool(self.record.get('before'))

    @property
    def observed(self):
        return bool(self.record.get('observed'))

    async def _persist(self):
        await self.save(copy.deepcopy(self.record))

    async def _best_persist(self):
        try:
            await self._persist()
        except Exception:
            pass

    def _fresh(self, stamp):
        value = _number(stamp)
        return value is not None and 0 <= self.clock() - value < 30

    def _sample(self, plan=None):
        s = dict(self.telemetry())
        self._last_sample = copy.deepcopy(s)
        if not s.get('healthy'):
            raise _Guard('health')
        if not self._fresh(s.get('reported_at')):
            raise _Guard('stale')
        for field in ('soc', 'grid_w', 'battery_w', 'pv_w', 'net_price', 'voltage_v', 'current_a'):
            s[field] = _number(s.get(field))
            if s[field] is None:
                raise _Guard('electrical' if field in ('voltage_v', 'current_a') else 'measurement')
        for field in ('voltage_reported_at', 'current_reported_at'):
            if not self._fresh(s.get(field, s['reported_at'])):
                raise _Guard('electrical_stale')
        plan = plan or self.record.get('plan', {})
        if not 44.8 <= s['voltage_v'] <= 57.6:
            raise _Guard('voltage')
        if abs(s['current_a']) > min(175, plan.get('current_limit_a', 175)) + 5:
            raise _Guard('current_limit')
        if abs(s['battery_w']) > min(10000, plan.get('battery_power_w', 10000)) + 250:
            raise _Guard('battery_limit')
        if not plan.get('minimum_soc', 60) < s['soc'] <= 100:
            raise _Guard('reserve')
        if s['net_price'] <= 0:
            raise _Guard('price')
        if -s['grid_w'] > min(9500, plan.get('power_w', 9300) + 300):
            raise _Guard('export_limit')
        return s

    async def _read(self):
        data = await self.native_read()
        r = data.get('registers', {})
        if any(type(r.get(a)) is not int or not 0 <= r[a] <= 65535 for a in WRITABLE | PROFILE):
            raise ValueError('Full native register snapshot is required')
        native = data.get('clock')
        if not isinstance(native, datetime) or native.tzinfo is None or native.utcoffset() is None:
            raise ValueError('Native clock must be timezone aware')
        return data

    @staticmethod
    def _profile_ok(r):
        return r[0] in (5, 1280) and r[98] == 1 and r[111] == 1 and r[130] == 0

    def _capture_conflicts(self, r, resolve_pending=True):
        """Unconfirmed own writes may still show their prior physical value."""
        changed = False
        for address in WRITABLE:
            key = str(address)
            expected = self.record['expected'][key]
            pending = self.record['pending'].get(key, {})
            possible = {expected, *pending.get('previous', [])}
            known = self.record['conflicts'].get(key)
            if known:
                possible.add(known['value'])
            if 'value' in pending:
                possible.add(pending['value'])
            if r[address] not in possible:
                self.record['conflicts'][key] = {'expected': expected, 'value': r[address]}
                changed = True
            elif resolve_pending and r[address] == expected:
                self.record['pending'].pop(key, None)
        return changed

    async def _audit_native(self, resolve_pending=True):
        data = await self._read()
        r = data['registers']
        self._native_mismatches = [{'field':f'register_{a}','expected':self.record['expected'][str(a)],'actual':r[a]} for a in sorted(WRITABLE) if r[a]!=self.record['expected'][str(a)]]
        if self._capture_conflicts(r, resolve_pending=resolve_pending):
            raise _Guard('native_conflict')
        if not self._profile_ok(r):
            raise _Guard('profile_changed')
        if not self.record.get('ha_controlled') and not native_clock_acceptable(data['clock'], self.clock()):
            raise _Guard('native_clock')
        if r[109] > _bms_limit(r):
            raise _Guard('current_limit')
        if any(r[a] != self.record['expected'][str(a)] for a in WRITABLE):
            raise _Guard('native_mismatch')
        self.record['last_native_check'] = self.clock()
        self.record['bms_discharge_a'] = _bms_limit(r)
        self.record['bms_reported_limit_a'] = r[213]
        self.record['bms_maximum_limit_a'] = r[219]
        return data

    def _stopped(self):
        s = dict(self.telemetry())
        stamp = _number(s.get('reported_at'))
        grid = _number(s.get('grid_w'))
        return (self._fresh(stamp) and stamp > self.record['stop_issued']
                and grid is not None and grid >= -100)

    async def _write(self, address, value, stage='prepare', protective=False):
        if self.record.get('ha_controlled') and address not in (142,143,145):
            raise ValueError('HA sale may change export controls only')
        if address not in WRITABLE or type(value) is not int or not 0 <= value <= 65535:
            raise ValueError('Invalid native battery-sale write')
        key = str(address)
        previous = self.record['pending'].get(key, {}).get('previous', [])
        previous = sorted({*previous, self.record['expected'][key]})
        self.record['pending'][key] = {'previous': previous, 'value': value}
        if protective:
            await self._best_persist()
        else:
            await self._persist()
        payload = {'id': self.record['id'], 'address': address, 'value': value, 'protective': protective}
        try:
            await self.event('battery_native_write_intent', payload)
        except Exception:
            if not protective:
                raise
        # Every ordinary write is guarded after the awaited durable audit.
        if not protective:
            if stage == 'restore' or address == 109:
                # Owner controls can change while the durable audit is awaited.
                # Compare a fresh physical image before writing the old program.
                current = (await self._read())['registers']
                if self._capture_conflicts(current, resolve_pending=False):
                    raise _Guard('native_conflict')
                if not self._profile_ok(current):
                    raise _Guard('profile_changed')
                if address == 109 and value > min(175, _bms_limit(current), self.record['before']['109']):
                    raise _Guard('current_limit')
            if stage == 'restore':
                if not self._stopped():
                    raise _Guard('cleanup_measurement')
            else:
                if stage in ('enable', 'adjust'):
                    await self._audit_native(resolve_pending=False)
                self._sample()
                now = self.clock()
                if stage == 'prepare' and now >= self.record['arm_until']:
                    raise _Guard('arming_expired')
                if stage == 'enable' and not self.record['start'] <= now < self.record['end'] - 10:
                    raise _Guard('enable_expired')
                if stage == 'adjust' and now >= self.record['end']:
                    raise _Guard('deadline')
        await self.native_write(address, value)
        self.record['expected'][key] = value
        try:
            await self.event('battery_native_write_confirmed', payload)
            await self._persist()
        except Exception:
            if not protective:
                raise

    async def start(self, power_w, duration_minutes, minimum_soc, quotes,
                    valid_until=None, purpose='manual', window_end=None, maximum_power_w=None, ha_controlled=None, business_block=None):
        async with self._lock:
            if self.active:
                raise ValueError('A native battery sale or cleanup is already active')
            if purpose not in ('manual', 'automatic', 'commission'):
                raise ValueError('Unknown battery-sale purpose')
            if purpose == 'commission' and (_number(power_w) not in (500,2000)
                    or _number(duration_minutes) != 5 or _number(minimum_soc) not in (60,90)
                    or maximum_power_w is not None and _number(maximum_power_w) != _number(power_w)):
                raise ValueError('Commissioning is fixed at an explicit500 or2000 W,5 minutes and60 or90 percent SOC')
            if ha_controlled is not None and type(ha_controlled) is not bool:
                raise ValueError('HA control must be explicitly boolean')
            if purpose=='commission' and ha_controlled:
                raise ValueError('Commissioning must retain its native proof path')
            uses_ha = purpose=='automatic' or purpose=='manual' and ha_controlled is True
            self._sample()
            data = await self._read()
            s = self._sample()
            r = data['registers']
            if not self._profile_ok(r) or (r[142], r[145], r[146]) != (2, 0, 255):
                raise ValueError('Requires ordinary LV lithium Capacity mode without grid charging')
            socs = [r[166 + i] for i in range(6)]
            powers = [r[154 + i] for i in range(6)]
            if (len(set(socs)) != 1 or not 1 <= socs[0] <= 59
                    or len(set(powers)) != 1 or powers[0] < 500
                    or any(r[172 + i] != 0 for i in range(6))):
                raise ValueError('Requires a uniform ordinary house program without charge/sell flags')
            if uses_ha and socs != [30]*6:
                raise ValueError('HA production requires the unchanged native reserve30 in every slot')
            current = min(60, r[109]) if purpose == 'commission' else r[109]
            house_power = min(3000, powers[0]) if purpose == 'commission' else powers[0]
            plan = battery_window_plan(data['clock'], self.clock(), power_w, duration_minutes,
                                       minimum_soc, s['voltage_v'], _bms_limit(r), current, house_power,
                                       quotes, valid_until=valid_until, window_end=window_end,
                                       ha_controlled=uses_ha)
            if uses_ha:
                # Owner policy: SOC60 is an HA stop threshold. The inverter's
                # ordinary SOC30 schedule remains the independent fallback.
                plan.update(ha_controlled=True, native_power_fence=False,
                            current_limit_a=min(175, r[109], _bms_limit(r)),
                            notice='HA stops at the sale reserve or deadline; the inverter house schedule is unchanged.')
            maximum = plan['power_w'] if maximum_power_w is None else _number(maximum_power_w)
            if maximum is None or maximum < 100:
                raise ValueError('Maximum approved power must be a finite value of at least 100 W')
            maximum = min(9300, math.floor(maximum))
            if plan['power_w'] > maximum:
                raise ValueError('Initial power exceeds the maximum approved power')
            self._sample(plan)
            before = {str(a): r[a] for a in WRITABLE}
            self.record = {
                **copy.deepcopy(plan), 'plan': copy.deepcopy(plan), 'id': str(time.time_ns()),
                'purpose': purpose, 'business_block':copy.deepcopy(business_block), 'phase': 'preparing', 'before': before,
                'expected': dict(before), 'pending': {}, 'conflicts': {},
                'observed': False, 'native_expiry_observed': False,
                'maximum_power_w': maximum,
            }
            try:
                await self._persist()
            except Exception:
                self.record = {}
                raise
            self.last_stop = None
            self.error = ''
            try:
                await self.event('battery_native_start', copy.deepcopy(self.record))
                await self._write(143, plan['power_w'])
                if not plan.get('ha_controlled'):
                    await self._write(109, plan['current_limit_a'])
                    for i in range(6):
                        await self._write(148 + i, plan['times_hhmm'][i])
                        await self._write(154 + i, plan['powers'][i])
                        await self._write(166 + i, plan['socs'][i])
                        await self._write(172 + i, 0)
                    await self._audit_native()
                    await self._write(146, plan['week_mask'])
                await self._audit_native()
                self._sample()
                if self.clock() >= self.record['arm_until']:
                    raise _Guard('arming_expired')
                self.record['phase'] = 'armed'
                await self._persist()
            except Exception as exc:
                self.error = type(exc).__name__+': '+str(exc)
                if exc.__cause__ is not None:
                    self.error += ' ('+type(exc.__cause__).__name__+': '+str(exc.__cause__)+')'
                self.record['failure_detail'] = self.error
                self.record['failure_context'] = self._failure_context()
                await self._stop('start_failed')
                raise

    def _failure_context(self):
        """Keep the failed sample, including individual electrical timestamps."""
        sample = getattr(self, '_last_sample', {})
        context = {key:copy.deepcopy(sample.get(key)) for key in (
            'health','healthy','reported_at','soc','grid_w','battery_w','pv_w',
            'voltage_v','current_a','voltage_reported_at','current_reported_at','net_price')}
        context['captured_at'] = self.clock()
        context['native_mismatches'] = copy.deepcopy(getattr(self,'_native_mismatches',[]))
        health = context.get('health')
        if isinstance(health,dict):
            issues = health.setdefault('issues',[])
            if self.record.get('native_read_failure'):
                issues.append(copy.deepcopy(self.record['native_read_failure']))
            for field,entity in (('voltage_reported_at','sensor.inverter_battery_voltage'),
                                 ('current_reported_at','sensor.inverter_battery_current')):
                stamp = _number(sample.get(field,sample.get('reported_at')))
                age = self.clock()-stamp if stamp is not None else None
                if age is None or age<0 or age>=30:
                    issues.append({'code':'stale' if age is not None and age>=30 else 'timestamp',
                                   'entity_id':entity,'age_seconds':age,'reported_at':stamp})
            health['healthy'] = bool(health.get('healthy')) and not issues
            health['transient_only'] = (bool(issues) and all(
                i.get('code') in ('missing','unavailable','stale') for i in issues))
        return context

    async def raise_reserve(self, minimum_soc):
        """Raise only the HA threshold; never write native SOC/program registers."""
        value = _number(minimum_soc)
        if value is None or not 60 <= value <= 100:
            raise ValueError('Invalid weather reserve')
        async with self._lock:
            if (not self.active or self.record.get('purpose') != 'automatic'
                    or self.record.get('phase') == 'stopping'):
                return
            old = max(self.record.get('minimum_soc',60),self.record.get('plan',{}).get('minimum_soc',60))
            if value <= old:
                return
            self.record['minimum_soc'] = value
            self.record.setdefault('plan',{})['minimum_soc'] = value
            self.record['weather_reserve_updated_at'] = self.clock()
            await self._persist()

    async def tick(self):
        async with self._lock:
            if not self.active:
                return
            if self.record.get('phase') == 'stopping':
                await self._stop('retry')
                return
            try:
                if self.record.get('ha_controlled') and self.clock() >= self.record['end']:
                    await self._stop('deadline')
                    return
                s = self._sample()
                if self.clock() - self.record.get('last_native_check', 0) >= 30:
                    try:
                        await self._audit_native()
                    except TimeoutError as exc:
                        self.record['native_read_failure'] = {
                            'code':'unavailable','entity_id':'native_controls',
                            'source':'battery_native_audit','error':type(exc).__name__+': '+str(exc)[:160],
                            'captured_at':self.clock(),'expected':'fresh physical register snapshot'}
                        # A timeout may overlap a real protection. Re-read telemetry
                        # and run every electrical/market guard before classifying it.
                        self._sample()
                        if self.record.get('ha_controlled') and self.clock() >= self.record['end']:
                            raise _Guard('deadline') from exc
                        raise _Guard('measurement') from exc
                    s = self._sample()
                now = self.clock()
                if now < self.record['start']:
                    if s['grid_w'] < -100:
                        raise _Guard('early_export')
                    return
                if 'sell_enabled_at' not in self.record:
                    if now >= self.record['end'] - 10:
                        raise _Guard('enable_expired')
                    await self._write(142, 0, stage='enable')
                    self.record['sell_enabled_at'] = self.clock()
                    self.record['phase'] = 'measuring'
                    await self._persist()
                    return
                stamp = float(s['reported_at'])
                if (now < self.record['end'] and self.record['start'] <= stamp < self.record['end']
                        and stamp > max(self.record.get('last_export', 0), self.record['sell_enabled_at'])
                        and s['grid_w'] < -100 and s['battery_w'] > 100
                        and -s['grid_w'] > max(0, s['pv_w']) + 100):
                    self.record.setdefault('first_export', stamp)
                    self.record['last_export'] = stamp
                    self.record['export_count'] = self.record.get('export_count', 0) + 1
                    self.record['observed'] = (self.record['export_count'] >= 3
                                               and stamp - self.record['first_export'] >= 20)
                await self.event('battery_native_measurement', {
                    'id': self.record['id'], 't': stamp, 'grid_w': s['grid_w'],
                    'battery_w': s['battery_w'], 'pv_w': s['pv_w'], 'soc': s['soc'],
                })
                if (now >= self.record['end'] and stamp >= self.record['end'] and self.observed
                        and self.record.get('last_export', 0) >= self.record['end'] - 15
                        and not self.record['native_expiry_observed'] and s['battery_w'] <= 100
                        and (s['grid_w'] >= -100 or -s['grid_w'] <= max(0, s['pv_w']) + 100)):
                    data = await self._audit_native()
                    s = self._sample()
                    r = data['registers']
                    if (data['clock'].timestamp() >= self.record['end'] and r[142] == 0
                            and r[145] == 0 and r[168] == 100 and r[174] == 0
                            and r[156] == 0 and self.record.get('native_power_fence') is True
                            and float(s['reported_at']) >= self.record['end'] and s['battery_w'] <= 100
                            and (s['grid_w'] >= -100 or -s['grid_w'] <= max(0, s['pv_w']) + 100)):
                        self.record['native_expiry_observed'] = True
                        self.record['phase'] = 'expiry_observed'
                        await self.event('battery_native_expiry', {
                            'id': self.record['id'], 'clock': data['clock'].isoformat(),
                            'grid_w': s['grid_w'], 'battery_w': s['battery_w'], 'next_soc': r[168],
                        })
                if self.clock() >= self.record['observer_deadline']:
                    await self._stop('deadline')
                    return
                await self._persist()
            except Exception as exc:
                self.error = type(exc).__name__+': '+str(exc)
                if exc.__cause__ is not None:
                    self.error += ' ('+type(exc.__cause__).__name__+': '+str(exc.__cause__)+')'
                self.record['failure_detail'] = self.error
                self.record['failure_context'] = self._failure_context()
                await self._stop(exc.reason if isinstance(exc, _Guard) else 'controller_error')

    async def adjust_power(self, power_w):
        """Change only MaxSell, within the original approval and battery limits."""
        async with self._lock:
            if not self.active or self.record.get('phase') == 'stopping':
                raise ValueError('No adjustable native battery sale is active')
            power = _number(power_w)
            if power is None or power < 0:
                raise ValueError('Adjusted power must be finite and nonnegative')
            if power < 100:
                await self._stop('budget')
                return
            if power > self.record['maximum_power_w']:
                raise ValueError('Adjusted power exceeds the original approval')
            power = math.floor(power)
            try:
                await self._write(143, power, stage='adjust')
                self.record['power_w'] = power
                self.record['plan']['power_w'] = power
                await self._persist()
            except Exception as exc:
                self.error = type(exc).__name__+': '+str(exc)
                if exc.__cause__ is not None:
                    self.error += ' ('+type(exc.__cause__).__name__+': '+str(exc.__cause__)+')'
                self.record['failure_detail'] = self.error
                await self._stop(exc.reason if isinstance(exc, _Guard) else 'controller_error')

    async def stop(self, reason='manual'):
        async with self._lock:
            await self._stop(reason)

    def _restore_targets(self, r):
        targets = {int(a): value for a, value in self.record['before'].items()}
        for key, conflict in self.record['conflicts'].items():
            targets[int(key)] = conflict['value']
        targets.update({142: 2, 145: 0, **{172 + i: 0 for i in range(6)}})
        targets[143] = min(9300, self.record['before']['143'], targets[143])
        targets[109] = min(175, self.record['before']['109'], targets[109], _bms_limit(r))
        return targets

    async def _stop(self, reason):
        if not self.active:
            return
        self.record['phase'] = 'stopping'
        self.record.setdefault('stop_reason', reason)
        self.record.setdefault('stop_issued', self.clock())
        await self._best_persist()
        read_error = None
        try:
            self._capture_conflicts((await self._read())['registers'])
        except Exception as exc:
            read_error = exc
        # Independent protections run even when persistence/audit/readback fails.
        failures = []
        protective = PROTECTIVE[:3] if self.record.get('ha_controlled') else PROTECTIVE
        for address, value in protective:
            try:
                await self._write(address, value, protective=True)
            except Exception as exc:
                failures.append(f'{address}: {type(exc).__name__}')
        if read_error or failures or not self._stopped():
            self.error = 'Native cleanup awaits fresh stopped grid and protective readback'
            if failures:
                self.error += ': ' + ', '.join(failures)
            await self._best_persist()
            return
        try:
            data = await self._read()
            r = data['registers']
            self._capture_conflicts(r)
            if any(r[a] != value for a, value in protective):
                raise ValueError('Protective register values are not physically confirmed')
            if not self._profile_ok(r):
                raise ValueError('Native profile changed; ordinary restoration needs review')
            targets = self._restore_targets(r)
            for address in sorted(WRITABLE - {142, 143, 145, 109}):
                if self.record.get('ha_controlled'):
                    targets[address] = r[address]
                    continue
                if r[address] != targets[address]:
                    await self._write(address, targets[address], stage='restore')
                else:
                    self.record['expected'][str(address)] = targets[address]
            for address in (109, 143):
                if self.record.get('ha_controlled') and address == 109:
                    targets[address] = r[address]
                    continue
                if r[address] != targets[address]:
                    await self._write(address, targets[address], stage='restore')
                else:
                    self.record['expected'][str(address)] = targets[address]
            final = (await self._read())['registers']
            if any(final[a] != targets[a] for a in WRITABLE) or final[109] > _bms_limit(final):
                raise ValueError('Whole native snapshot does not confirm restoration')
            if not self._stopped():
                raise ValueError('Fresh stopped grid is required after restoration')
            proof = {k: copy.deepcopy(self.record.get(k)) for k in (
                'id', 'purpose', 'power_w', 'minimum_soc', 'observed', 'native_expiry_observed',
                'start', 'end', 'business_block', 'conflicts', 'notice', 'native_power_fence', 'failure_detail', 'failure_context')}
            proof.update(reason=self.record['stop_reason'], stop_verified=True,
                         phase='complete', production_verified=False,
                         restored_current_a=targets[109], restored_cap_w=targets[143])
            await self.event('battery_native_stop', proof)
            await self.save({})
            self.last_stop = proof
            self.record = {}
            self.error = ''
        except Exception as exc:
            self.error = 'Native restoration awaits retry: ' + str(exc)
            await self._best_persist()
