"""Archive numeric summaries before asking Recorder to purge old detail."""
import asyncio
from datetime import timedelta
from pathlib import Path
import shutil
import time
import voluptuous as vol
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from .archive import capture

DOMAIN = 'jarvis_recorder_retention'
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    if config.get('recorder', {}).get('db_url'):
        raise ValueError('Summary retention requires the verified default SQLite database')
    source = Path(hass.config.path('home-assistant_v2.db'))
    target = Path(hass.config.path('jarvis_workspace', 'measurement-summaries.sqlite'))
    store = Store(hass, 1, DOMAIN)
    saved = await store.async_load() or {}
    lock = asyncio.Lock()

    async def maintain(_now=None):
        if lock.locked():
            return
        async with lock:
            try:
                if shutil.disk_usage(source.parent).free < 256 * 1024**2:
                    raise RuntimeError('Not enough space for a verified statistics snapshot')
                report = await hass.async_add_executor_job(capture, source, target)
                now = time.time()
                if now - saved.get('last_purge_requested', 0) >= 86400:
                    # Durable marker first: never repeatedly enqueue a heavy purge
                    # after restart or an unknown service outcome.
                    saved['last_purge_requested'] = now
                    await store.async_save(saved)
                    await hass.services.async_call('recorder', 'purge',
                        {'keep_days': 7, 'repack': False, 'apply_filter': False}, blocking=True)
                report.update(version='0.1.0', friendly_name='Archiv souhrnů a údržba historie',
                    detail_keep_days=7, purge_requested_at=saved.get('last_purge_requested'),
                    purge_completion_verified=False, automatic_repack=False,
                    repack_minimum_free_bytes=report['source_bytes'],
                    notice='Souhrny ověřeny. Pročištění je požadavek, ne důkaz dokončení. Zmenšení souboru potřebuje samostatný prostorový preflight.')
                hass.states.async_set('sensor.jarvis_recorder_retention', 'ready', report)
            except Exception as exc:
                # In particular, never purge after a failed archive/checksum/readback.
                hass.states.async_set('sensor.jarvis_recorder_retention', 'error',
                    {'friendly_name': 'Archiv souhrnů a údržba historie', 'version': '0.1.0', 'error': str(exc)})

    async_track_time_interval(hass, maintain, timedelta(hours=1))
    if hass.is_running:
        hass.async_create_task(maintain())
    else:
        hass.bus.async_listen_once('homeassistant_started', maintain)
    return True

