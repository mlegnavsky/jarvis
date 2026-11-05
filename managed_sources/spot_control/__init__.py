"""Scoped charging and sales controllers with mutual exclusion and durable recovery."""
import asyncio
from datetime import timedelta
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError
from .engine import Controller,equal,finite,charge_limits_ok,TEST_CURRENT_LIMIT
DOMAIN='jarvis_spot_control'
CONFIG_SCHEMA=vol.Schema({vol.Optional(DOMAIN):vol.Schema({vol.Optional('commission_pv_test',default=False):bool})},extra=vol.ALLOW_EXTRA)
async def async_setup(hass,config):
    store=Store(hass,1,DOMAIN+'.transaction')
    saved=await store.async_load() or {}
    def read():return {s.entity_id:s.state for s in hass.states.async_all() if '.inverter_' in s.entity_id}
    def healthy():
        sales=hass.data.get(DOMAIN+'_sales',{})
        controllers=list(sales.get('controllers') or [])
        controllers.extend(sales.get(key) for key in ('controller','window','battery_controller','battery_sale'))
        if any(getattr(controller,'active',False) for controller in controllers):return False
        if sales.get('clock_sync_active'):return False
        busy=sales.get('busy')
        if callable(busy) and busy():return False
        now=dt_util.utcnow()
        for e in ('sensor.inverter_battery','sensor.inverter_battery_power','sensor.inverter_grid_power','sensor.inverter_battery_temperature','number.inverter_battery_max_charging_current'):
            s=hass.states.get(e)
            t=getattr(s,'last_reported',None) or getattr(s,'last_updated',None)
            if s is None or finite(s.state) is None or t is None or (now-t).total_seconds()>120:return False
        return charge_limits_ok(read())
    async def write(entity,value):
        domain=entity.split('.')[0]
        if domain=='number':service='set_value';data={'value':float(value)}
        elif domain=='select':service='select_option';data={'option':value}
        else:service='turn_on' if value=='on' else 'turn_off';data={}
        issued=dt_util.utcnow()
        async with asyncio.timeout(40):
            await hass.services.async_call(domain,service,{'entity_id':entity,**data},blocking=True)
        # Readback is a setting acknowledgement, not proof of physical power flow.
        for _ in range(35):
            await asyncio.sleep(1)
            s=hass.states.get(entity)
            reported=(getattr(s,'last_reported',None) or getattr(s,'last_updated',None)) if s else None
            if s and reported and reported>issued and equal(s.state,value):return
        raise HomeAssistantError('Měnič nepotvrdil nastavení '+entity)
    c=Controller(read,write,store.async_save,saved,healthy=healthy)
    ready=False
    def telemetry():
        result={}
        for name in ('pv_power','load_power','grid_power','battery_power','battery','battery_temperature','battery_current','battery_voltage','temperature'):
            state=hass.states.get('sensor.inverter_'+name)
            if state is not None:
                t=getattr(state,'last_reported',None) or state.last_updated
                result['sensor.inverter_'+name]={'state':state.state,'last_reported':t.isoformat()}
        return result
    def report():
        phase=c.record.get('phase','idle')
        hass.states.async_set('sensor.jarvis_spot_control',phase,{'friendly_name':'Spoty – ruční nabíjení','version':'0.6.3','test_current_limit':TEST_CURRENT_LIMIT,'telemetry':telemetry(),'ready':ready,'active':c.active,'target_soc':c.record.get('target'),'deadline':c.record.get('deadline'),'slot':c.record.get('slot'),'charging_observed':c.observed,'error':c.error,'telemetry_fresh':healthy(),'icon':'mdi:battery-charging'})
    async def start(call):
        if not ready or not healthy():raise HomeAssistantError('Čekám na aktuální měření měniče.')
        now=dt_util.now()
        try:await c.start(now.hour*60+now.minute)
        except Exception as exc:raise HomeAssistantError(str(exc)) from exc
        finally:report()
    async def stop(call):
        try:await c.stop()
        finally:report()
        if c.active:raise HomeAssistantError(c.error or 'Obnova zatím není potvrzená.')
    async def tick(now):
        nonlocal ready
        try:
            if not ready:
                if c.active:await c.stop()
                ready=not c.active
            else:await c.tick(healthy())
        except Exception as exc:c.error=str(exc)
        finally:report()
    async def started(event):
        await tick(None)
    async_register_admin_service(hass,DOMAIN,'start_test',start,vol.Schema({}))
    async_register_admin_service(hass,DOMAIN,'stop_restore',stop,vol.Schema({}))
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,started)
    async_track_time_interval(hass,tick,timedelta(seconds=15))
    hass.data[DOMAIN]=c
    from .sale_setup import async_setup_sales
    await async_setup_sales(hass,config,c)
    from .finance_setup import async_setup_finance
    try:await async_setup_finance(hass)
    except Exception as exc:
        for entity in ('sensor.jarvis_dnes_nakoupeno_za','sensor.jarvis_dnes_prodano_za'):
            hass.states.async_set(entity,'unavailable',{'error':type(exc).__name__})
    report()
    return True
