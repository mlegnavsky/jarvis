"""User-authorized local retention: preserve latest successful system backup."""
from datetime import datetime, timedelta, timezone

def retention_plan(backups):
 local={k:b for k,b in backups.items() if 'hassio.local' in b.agents}
 complete=[b for b in local.values() if b.homeassistant_included and b.database_included and b.addons and not (b.failed_addons or b.failed_folders or b.failed_agent_ids)]
 if not complete: return None,[]
 keep=max(complete,key=lambda b:datetime.fromisoformat(b.date)).backup_id
 return keep,[k for k,b in local.items() if k!=keep and datetime.fromisoformat(b.date)<datetime.fromisoformat(local[keep].date)]

async def setup_retention(hass):
 from homeassistant.components.backup import async_get_manager
 from homeassistant.helpers.event import async_track_time_interval
 from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
 import asyncio
 lock=asyncio.Lock()
 async def prune(_now=None):
  if lock.locked(): return
  async with lock:
   try:
    manager=async_get_manager(hass)
    if manager.state!='idle': return
    backups,errors=await manager.async_get_backups()
    if errors: raise RuntimeError('Seznam záloh nelze kompletně ověřit')
    keep,remove=retention_plan(backups)
    if keep is None: raise RuntimeError('Nenalezena úspěšná systémová záloha s aplikacemi')
    # Avoid racing a new backup's finalization or an ongoing administrative task.
    if (datetime.now(timezone.utc)-datetime.fromisoformat(backups[keep].date)).total_seconds()<300: return
    deleted=[]
    for backup_id in remove:
     if manager.state!='idle': break
     result=await manager.async_delete_backup(backup_id,agent_ids=['hassio.local'])
     if result: raise RuntimeError('Odstranění staré zálohy se nezdařilo')
     deleted.append(backup_id)
    remaining,errors=await manager.async_get_backups()
    hass.states.async_set('sensor.jarvis_zalohy_retence','ready' if not errors else 'error',{'friendly_name':'Zálohy · poslední systémová kopie','keep':keep,'local_count':sum('hassio.local' in b.agents for b in remaining.values()),'deleted':deleted,'checked_at':datetime.now(timezone.utc).isoformat(),'policy':'1 poslední úspěšná systémová záloha včetně aplikací; úklid po 15 minutách'})
   except Exception as exc:
    hass.states.async_set('sensor.jarvis_zalohy_retence','error',{'error':str(exc)})
 async_track_time_interval(hass,prune,timedelta(minutes=15))
 if hass.is_running: await prune()
 else: hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED,prune)
