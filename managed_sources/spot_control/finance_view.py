"""Daily cash cards shared by home and energy views; house artwork is preserved."""
import copy

def money_card(kind):
 buy=kind=='purchase';entity='sensor.jarvis_dnes_nakoupeno_za' if buy else 'sensor.jarvis_dnes_prodano_za'
 title='Dnes nakoupeno za' if buy else 'Dnes prodáno za'
 footer='ČEZ · 5 Kč/kWh' if buy else 'OTE − 0,30 Kč/kWh'
 fallback="{% if not is_number(v) and is_number(states('sensor.inverter_today_energy_import')) %}{% set v=(states('sensor.inverter_today_energy_import')|float)*5 %}{% endif %}" if buy else ''
 return {'type':'markdown','content':f"### {title}\n{{% set v=states('{entity}') %}}{fallback}\n## {{{{ ('%.2f'|format(v|float))|replace('.', ',') if is_number(v) else '—' }}}} Kč\n{footer}"}

def status_card():
 return {'type':'markdown','content':"""Průběžný odhad · dnešní den
{% set t=state_attr('sensor.jarvis_dnes_prodano_za','as_of') %}{% if t %}Obnoveno {{ t | timestamp_custom('%H:%M:%S', true) }}{% endif %}
{% if not state_attr('sensor.jarvis_dnes_prodano_za','archive_loaded') %}Načítám starší dnešní záznamy.{% elif state_attr('sensor.jarvis_dnes_prodano_za','quality')=='partial' %}Část dne čeká na doplnění údajů.{% endif %}
{% if state_attr('sensor.jarvis_dnes_prodano_za','fx_provisional') %}Kurz ČNB je zatím předběžný.{% endif %}"""}

def cash_block():return {'type':'vertical-stack','cards':[{'type':'grid','columns':2,'square':False,'cards':[money_card('purchase'),money_card('sale')]},status_card()]}

def upgrade_dashboard(document):
 result=copy.deepcopy(document);changed={'home':0,'purchase':0,'sale':0,'price_note':0}
 def walk(obj,path):
  if isinstance(obj,dict):
   content=obj.get('content')
   if isinstance(content,str):
    if path=='domov' and 'Síť → dům' in content:
     options=obj.get('grid_options');obj.clear();obj.update(cash_block())
     if options:obj['grid_options']=options
     changed['home']+=1;return
    if content.startswith('### Náklady na odběr'):
     obj.update(money_card('purchase'));changed['purchase']+=1
    elif content.startswith('### Výnos z prodeje'):
     obj.update(money_card('sale'));changed['sale']+=1
    elif 'spot čeká na nastavení' in content:
     obj['content']=status_card()['content']+'\n\nNákup: **5 Kč/kWh** · Výkup: **OTE − 0,30 Kč/kWh**';changed['price_note']+=1
   for value in obj.values():walk(value,path)
  elif isinstance(obj,list):
   for value in obj:walk(value,path)
 for view in result.get('views',[]):
  if isinstance(view,dict):walk(view,view.get('path'))
 if changed!={'home':2,'purchase':2,'sale':2,'price_note':2}:raise ValueError('Dashboard layout differs; refusing a blind edit: '+str(changed))
 return result,changed
