"""Production boundary: fixed house program, export controls only.

The legacy engine is retained for explicit historical commissioning and cleanup
of persisted old transactions. A new ordinary transaction cannot enter that path.
"""
from .battery_native import BatterySaleController as LegacyBatteryController

class ProductionBatteryController(LegacyBatteryController):
 async def start(self,power_w,duration_minutes,minimum_soc,quotes,valid_until=None,purpose='manual',window_end=None,maximum_power_w=None,business_block=None):
  if purpose not in ('automatic','manual'):raise ValueError('Commissioning není součást běžného provozu.')
  return await super().start(power_w,duration_minutes,minimum_soc,quotes,valid_until=valid_until,purpose=purpose,
    window_end=window_end,maximum_power_w=maximum_power_w,ha_controlled=True,business_block=business_block)
 async def _write(self,address,value,stage='prepare',protective=False):
  if self.record.get('ha_controlled') and address not in (142,143,145):
   raise ValueError('Běžný prodej smí měnit pouze pracovní režim a limit přetoků.')
  return await super()._write(address,value,stage=stage,protective=protective)
