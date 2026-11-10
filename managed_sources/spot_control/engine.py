"""Durable, scoped manual charge transaction; never touches export controls."""
import asyncio
import time
import math
try:
    from .heating_charge import HeatingChargeMixin
except ImportError:
    from heating_charge import HeatingChargeMixin
TEST_CURRENT_LIMIT=175
CURRENT='number.inverter_battery_grid_charging_current'
SWITCH='switch.inverter_battery_grid_charging'
def finite(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None

def charge_limits_ok(states):
    temp=finite(states.get('sensor.inverter_battery_temperature'))
    cap=finite(states.get('number.inverter_battery_max_charging_current'))
    # Conservative test cutoff, not the manufacturer's absolute temperature limit.
    return temp is not None and 0<=temp<45 and cap is not None and cap>0

def plan(states,minute):
    if not charge_limits_ok(states):raise ValueError('Test vyžaduje teplotu baterie 0 až méně než 45 °C a známý nabíjecí limit.')
    if states.get('select.inverter_work_mode')!='Zero Export To CT' or states.get('switch.inverter_export_surplus')!='off':
        raise ValueError('Nejdřív musí být aktivní režim bez přetoků.')
    if states.get('select.inverter_time_of_use') not in ('Week','Enabled'):
        raise ValueError('Časový program není aktivní pro celý týden.')
    soc=finite(states.get('sensor.inverter_battery'))
    if soc is None or not 0<=soc<90: raise ValueError('Nabití baterie musí být známé a pod 90 %.')
    starts=[]
    for i in range(1,7):
        t=states.get(f'time.inverter_program_{i}_time','')
        try: h,m=map(int,t.split(':')[:2]); v=h*60+m
        except Exception: raise ValueError('Chybí časový program měniče.')
        if not 0<=h<=23 or not 0<=m<=59: raise ValueError('Neplatný čas programu.')
        starts.append(v)
    if starts!=sorted(set(starts)): raise ValueError('Časový program není vzestupný.')
    slot=max((i+1 for i,t in enumerate(starts) if t<=minute),default=6)
    charge=f'select.inverter_program_{slot}_charging'; target=f'number.inverter_program_{slot}_soc'
    if states.get(charge)!='Disabled': raise ValueError('V tomto intervalu už je nastavené nabíjení.')
    amps=finite(states.get(CURRENT)); oldsoc=finite(states.get(target))
    if amps is None or amps<=0 or oldsoc is None or states.get(SWITCH) not in ('on','off'):
        raise ValueError('Nastavení nabíjení není dostupné.')
    goal=min(90,math.floor(soc+5))
    return [(CURRENT,str(min(TEST_CURRENT_LIMIT,float(states['number.inverter_battery_max_charging_current'])))),(target,str(goal)),(SWITCH,'on'),(charge,'Grid')],goal,slot

def equal(a,b):
    x,y=finite(a),finite(b)
    return x==y if x is not None and y is not None else a==b

class Controller(HeatingChargeMixin):
    def __init__(self,read,write,save,saved=None,clock=time.time,healthy=lambda:True,communication_ok=lambda:True,permitted=lambda:True):
        self.read,self.write,self.save,self.clock=read,write,save,clock
        self.healthy=healthy;self.communication_ok=communication_ok;self.permitted=permitted;self.offline_since=None
        self.record=saved or {}; self.lock=asyncio.Lock(); self.error='';self.observed=False
    def connection_grace(self):
        """Only an already running session may bridge missing telemetry."""
        if not self.active or self.record.get('phase')!='running' or not self.permitted():return False
        s=self.read()
        temp=finite(s.get('sensor.inverter_battery_temperature'))
        cap=finite(s.get('number.inverter_battery_max_charging_current'))
        if temp is not None and not 0<=temp<45 or cap is not None and cap<=0:return False
        for e,allowed in [('select.inverter_work_mode',('Zero Export To CT',)),('switch.inverter_export_surplus',('off',)),('select.inverter_time_of_use',('Week','Enabled')),('binary_sensor.inverter_grid',('on',)),('binary_sensor.inverter_battery_alarm',('off',)),('binary_sensor.inverter_battery_fault',('off',))]:
            v=s.get(e)
            if v not in (None,'unknown','unavailable') and v not in allowed:return False
        for i in range(1,7):
            floor=finite(s.get(f'number.inverter_program_{i}_soc'))
            if floor is not None and floor<30:return False
        if self.record.get('purpose')=='heating':
            for e,v in self.record.get('applied',{}).items():
                if s.get(e) not in (None,'unknown','unavailable') and not equal(s[e],v):return False
        soc=finite(s.get('sensor.inverter_battery'))
        if self.record.get('purpose')!='heating' and soc is not None and soc>=self.record.get('target',100):return False
        if self.communication_ok():self.offline_since=None;return False
        if self.offline_since is None:self.offline_since=self.clock()
        return 0<=self.clock()-self.offline_since<180
    @property
    def active(self): return bool(self.record.get('before'))
    async def start(self,minute):
        async with self.lock:
            if self.active: raise ValueError('Nejprve zastav předchozí test a obnov nastavení.')
            self.offline_since=None
            states=self.read(); steps,goal,slot=plan(states,minute)
            self.record={'before':{e:states[e] for e,v in steps},'steps':steps,'deadline':self.clock()+600,'target':goal,'slot':slot,'phase':'starting'}
            await self.save(self.record) # durable before any inverter write
            try:
                for e,v in steps:
                    live=self.read()
                    if not self.healthy() or not charge_limits_ok(live) or live.get('select.inverter_work_mode')!='Zero Export To CT' or live.get('switch.inverter_export_surplus')!='off':
                        raise ValueError('Měření nebo režim bez přetoků se změnil; test ukončuji.')
                    await self.write(e,v)
                self.record['phase']='running';await self.save(self.record)
                self.error='';self.observed=False
            except Exception as exc:
                self.error=str(exc)
                await self._restore()
                raise
    async def stop(self):
        async with self.lock: await self._restore()
    async def _restore(self):
        if self.record.get('purpose')=='heating':return await self._restore_heating()
        if not self.active: return
        self.record['phase']='restoring'
        try:await self.save(self.record)
        except Exception:self.error='Zápis průběhu obnovy selhal; původní záznam zůstává pro opakování.'
        failures=[]
        # Grid permission first, target second, then current; preserve original switch.
        order=[e for e,v in reversed(self.record['steps'])]
        for e in order:
            v=self.record['before'][e]
            try:
                await self.write(e,v)
            except Exception as exc:
                failures.append(f'{e}: {exc}')
                # Never restore a larger current/target before Grid is disabled.
                if e.startswith('select.'):
                    self.error='Obnova nabíjení nepotvrzena: '+str(exc)
                    return
        if failures:
            self.error='Obnova nedokončena: '+'; '.join(failures)
            await self.save(self.record)
            return
        try:await self.save({})
        except Exception:
            self.error='Hodnoty vráceny, ale záznam obnovy se nepodařilo uzavřít.'
            return
        self.record={};self.offline_since=None
    async def tick(self,healthy=True):
        if self.record.get('purpose')=='heating':return await self.tick_heating(healthy)
        if not self.active:return
        if self.connection_grace() and self.clock()<self.record.get('deadline',0):return
        s=self.read();soc=finite(s.get('sensor.inverter_battery'))
        grid=finite(s.get('sensor.inverter_grid_power'));batt=finite(s.get('sensor.inverter_battery_power'))
        if grid is not None and batt is not None and grid>100 and batt < -100:self.observed=True
        guard=s.get('select.inverter_work_mode')=='Zero Export To CT' and s.get('switch.inverter_export_surplus')=='off'
        if not healthy or not charge_limits_ok(s) or not guard or soc is None or soc>=self.record['target'] or self.clock()>=self.record['deadline'] or self.record['phase']=='restoring':
            await self.stop()
