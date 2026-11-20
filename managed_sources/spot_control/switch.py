from homeassistant.core import callback
from homeassistant.components.switch import SwitchEntity
from .sale_setup import KEY

async def async_setup_platform(hass,config,async_add_entities,discovery_info=None):async_add_entities([SaleAutomatic(hass)])

class SaleAutomatic(SwitchEntity):
 _attr_should_poll=False
 _attr_unique_id='jarvis_sale_automatic'
 _attr_name='Automatický prodej'
 _attr_icon='mdi:solar-power'
 def __init__(self,hass):self.data=hass.data[KEY];self.entity_id='switch.jarvis_sale_automatic'
 @property
 def is_on(self):return bool(self.data['settings'].get('requested_automatic'))
 @callback
 def _settings_changed(self,_event):self.async_write_ha_state()
 async def async_added_to_hass(self):
  self.async_on_remove(self.hass.bus.async_listen('jarvis_sales_settings',self._settings_changed))
 async def async_turn_on(self,**kwargs):
  prefs=self.data['settings']
  await self.data['configure']({'automatic':True,'auto_verification_enabled':False,'inhibited':False,'commission_cancelled':False,'commission_attempted':False if not prefs['pv_verified'] else True});self.async_write_ha_state();await self.data['report']()
 async def async_turn_off(self,**kwargs):
  await self.data['stop']();self.async_write_ha_state();await self.data['report']()
