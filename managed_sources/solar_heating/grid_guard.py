"""Manual override admission with connected grid and native minimum reserve."""
import math
ENTITIES=('binary_sensor.inverter_grid','select.inverter_work_mode','select.inverter_time_of_use','switch.inverter_export_surplus','sensor.inverter_battery','sensor.inverter_battery_power','sensor.inverter_grid_power','binary_sensor.inverter_battery_alarm','binary_sensor.inverter_battery_fault',*(f'number.inverter_program_{i}_soc' for i in range(1,7)))

def check(get,now):
 values={}
 for entity in ENTITIES:
  state=get(entity)
  stamp=(getattr(state,'last_reported',None) or getattr(state,'last_updated',None)) if state else None
  if state is None or stamp is None or not 0<=now-stamp.timestamp()<=60:
   return False,'Čeká na aktuální měření sítě a baterie'
  values[entity]=state.state
 if values['binary_sensor.inverter_grid']!='on':return False,'Síť není dostupná'
 if values['select.inverter_work_mode']!='Zero Export To CT' or values['switch.inverter_export_surplus']!='off' or values['select.inverter_time_of_use']!='Week':return False,'Měnič není v ověřeném domácím režimu'
 if any(values[e]!='off' for e in ('binary_sensor.inverter_battery_alarm','binary_sensor.inverter_battery_fault')):return False,'Baterie hlásí poruchu'
 try:
  soc=float(values['sensor.inverter_battery']);power=float(values['sensor.inverter_battery_power']);grid=float(values['sensor.inverter_grid_power'])
  floors=[float(values[f'number.inverter_program_{i}_soc']) for i in range(1,7)]
  if not all(math.isfinite(v) for v in [soc,power,grid,*floors]) or not 0<=soc<=100 or any(not 0<=v<=100 for v in floors):raise ValueError()
 except (ValueError,TypeError):return False,'Chybí stav baterie nebo rezervy měniče'
 # Explicit manual heat bypasses the heating-only 50% admission, not the
 # inverter's independent reserve. SOC may rise or be above30% legitimately.
 # Instant power is not a mode switch: transfer transients are handled over
 # time by the policy, while the inverter continues to enforce its reserve.
 if min(floors)<30:return False,'Nativní rezerva měniče je nižší než 30 %'
 return True,'Síť připravena'
