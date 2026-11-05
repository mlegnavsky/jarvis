from homeassistant.core import callback
from homeassistant.components.select import SelectEntity
from .sale_setup import KEY

async def async_setup_platform(hass,config,async_add_entities,discovery_info=None):
 async_add_entities([SaleSource(hass)])

class SaleSource(SelectEntity):
 _attr_should_poll=False
 _attr_unique_id='jarvis_sale_source'
 _attr_name='Zdroj vlastního prodeje'
 _attr_options=['Přebytky panelů','Baterie nad rezervou']
 def __init__(self,hass):self.data=hass.data[KEY];self.entity_id='select.jarvis_sale_source'
 @property
 def current_option(self):return self.options[1 if self.data['settings']['source']=='battery' else 0]
 @callback
 def _settings_changed(self,_event):self.async_write_ha_state()
 async def async_added_to_hass(self):
  self.async_on_remove(self.hass.bus.async_listen('jarvis_sales_settings',self._settings_changed))
 async def async_select_option(self,option):
  if option not in self.options:raise ValueError('Neplatný zdroj prodeje.')
  await self.data['configure']({'source':'battery' if option==self.options[1] else 'pv'})
  self.async_write_ha_state();await self.data['report']()
