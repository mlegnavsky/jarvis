from homeassistant.core import callback
from homeassistant.components.number import NumberEntity,NumberMode
from .sale_setup import KEY

async def async_setup_platform(hass,config,async_add_entities,discovery_info=None):
 async_add_entities([SaleNumber(hass,'power_w','Výkon vlastního prodeje',100,9300,100,'W'),SaleNumber(hass,'minutes','Délka vlastního prodeje',1,60,1,'min')])

class SaleNumber(NumberEntity):
 _attr_should_poll=False
 _attr_mode=NumberMode.BOX
 def __init__(self,hass,key,name,minimum,maximum,step,unit):
  self.data=hass.data[KEY];self.key=key
  self.entity_id='number.jarvis_sale_'+key
  self._attr_unique_id='jarvis_sale_'+key;self._attr_name=name
  self._attr_native_min_value=minimum;self._attr_native_max_value=maximum;self._attr_native_step=step;self._attr_native_unit_of_measurement=unit
 @property
 def native_min_value(self):return 5 if self.key=='minutes' and self.data['settings']['source']=='battery' else self._attr_native_min_value
 @property
 def native_value(self):return self.data['settings'][self.key]
 @callback
 def _settings_changed(self,_event):self.async_write_ha_state()
 async def async_added_to_hass(self):
  self.async_on_remove(self.hass.bus.async_listen('jarvis_sales_settings',self._settings_changed))
 async def async_set_native_value(self,value):
  if not self.native_min_value<=value<=self.native_max_value:raise ValueError('Hodnota je mimo povolený rozsah.')
  await self.data['configure']({self.key:float(value)})
  self.async_write_ha_state();await self.data['report']()
