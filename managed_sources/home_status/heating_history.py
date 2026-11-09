"""Add native, explicit heating controls to existing history views only."""
import re
import yaml

ROOMS={'switch.aqara_smart_plug_eu':('child','Dětský pokoj'),'switch.aqara_smart_plug_eu_2':('living','Obývák')}
MARKER='  # grid-heating-history-v1'

def controls(entity,room,name):
 status='sensor.jarvis_topeni_'+room
 return [
  {'type':'markdown','title':name+' · ruční topení ze sítě','content':
   "{% if is_state('"+entity+"','on') and state_attr('"+status+"','mode') == 'grid_manual' %}"
   '**Ruční topení ze sítě je zapnuté.**'
   '{% else %}**Stav:** {{ states(\''+status+"') }}{% endif %}\n\n"
   'Vypne se při **24 °C v dětském pokoji** nebo tlačítkem Vypnout. Rezerva baterie **30 % zůstává zachovaná**.\n\n'
   "{% if not state_attr('"+status+"','grid_ready') %}"
   "{{ state_attr('"+status+"','grid_reason') or 'Čeká na aktuální údaje měniče.' }}{% endif %}"},
  {'type':'grid','columns':2,'square':False,'cards':[
   {'type':'button','name':'Zapnout topení ze sítě','icon':'mdi:transmission-tower','show_state':False,'tap_action':{'action':'perform-action','perform_action':'jarvis_solar_heating.set_mode','data':{'room':room,'mode':'grid_manual'}},'hold_action':{'action':'none'}},
   {'type':'button','name':'Vypnout radiátor','icon':'mdi:radiator-off','show_state':False,'tap_action':{'action':'perform-action','perform_action':'jarvis_solar_heating.set_mode','data':{'room':room,'mode':'off'}},'hold_action':{'action':'none'}}]},
  {'type':'entities','title':'Aktuální stav','show_header_toggle':False,'entities':[
   {'entity':status,'name':'Řízení topení'},
   {'entity':'sensor.aqara_temp_humidity_sensor_t1_teplota','name':'Dětský pokoj · vypnutí při 24 °C'},
   {'entity':'sensor.inverter_battery','name':'Baterie · rezerva 30 %'}]}]

def patch(text):
 lines=text.splitlines(keepends=True)
 # Native state-icon honours the dashboard's existing hold navigation even if
 # the browser has a cached custom module with an older gesture implementation.
 i=0
 while i<len(lines):
  match=re.fullmatch(r'( *)- type: custom:jarvis-device-status\n?',lines[i])
  if not match:i+=1;continue
  indent=match[1];j=i+1
  while j<len(lines) and (not lines[j].strip() or len(lines[j])-len(lines[j].lstrip(' '))>len(indent)):j+=1
  block=lines[i:j]
  if any(indent+'  entity: '+entity+'\n' in block for entity in ROOMS):
   block[0]=indent+'- type: state-icon\n'
   block=[line for line in block if not line.startswith((indent+'  heating_entity:',indent+'  kind:'))]
   lines[i:j]=block;j=i+len(block)
  i=j
 for entity,(room,name) in ROOMS.items():
  matches=[i for i,line in enumerate(lines) if line.rstrip()=='  path: historie-'+entity.replace('.','-')]
  if len(matches)!=1:raise ValueError('Expected exactly one radiator history view: '+entity)
  start=matches[0];end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('- ')),len(lines))
  if any(line.rstrip()==MARKER for line in lines[start:end]):continue
  positions=[i for i in range(start,end) if lines[i].rstrip()=='  cards:']
  if len(positions)!=1:raise ValueError('Missing history cards: '+entity)
  generated=yaml.safe_dump(controls(entity,room,name),allow_unicode=True,sort_keys=False,width=140)
  addition=[MARKER+'\n']+['  '+line+'\n' if line else '\n' for line in generated.splitlines()]
  at=positions[0]+1;lines[at:at]=addition
 return ''.join(lines)
