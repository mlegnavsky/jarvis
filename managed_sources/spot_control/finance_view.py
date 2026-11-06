"""Daily cash cards shared by home and energy views; house artwork is preserved."""
import copy

def money_card(kind):
 buy=kind=='purchase';entity='sensor.jarvis_dnes_nakoupeno_za' if buy else 'sensor.jarvis_dnes_prodano_za'
 title='Dnes nakoupeno za' if buy else 'Dnes prodáno za'
 footer=("ČEZ · {{ ('%.2f'|format(state_attr('sensor.jarvis_dnes_nakoupeno_za','purchase_rate')|float(5)))|replace('.', ',') }} Kč/kWh" if buy else "OTE − {{ ('%.2f'|format(state_attr('sensor.jarvis_dnes_prodano_za','sale_fee')|float(0.30)))|replace('.', ',') }} Kč/kWh")
 fallback=''
 if not buy:
  fallback="{% set partial=false %}{% if not is_number(v) and state_attr('sensor.jarvis_dnes_prodano_za','archive_loaded') and state_attr('sensor.jarvis_dnes_prodano_za','quality')=='partial' %}{% set known=state_attr('sensor.jarvis_dnes_prodano_za','known_sale_czk') %}{% if is_number(known) %}{% set v=known %}{% set partial=true %}{% endif %}{% endif %}"
  footer="{% if partial %}Doložená část · celkový výnos zatím není úplný.\n{% endif %}"+footer
 return {'type':'markdown','content':f"### {title}\n{{% set v=states('{entity}') %}}{fallback}\n## {{{{ ('%.2f'|format(v|float))|replace('.', ',') if is_number(v) else '—' }}}} Kč\n{footer}"}

def status_card():
 return {'type':'markdown','content':"""Průběžný odhad · dnešní den
{% set t=state_attr('sensor.jarvis_dnes_prodano_za','as_of') %}{% if t %}Obnoveno {{ t | timestamp_custom('%H:%M:%S', true) }}{% endif %}
{% if not state_attr('sensor.jarvis_dnes_prodano_za','archive_loaded') %}Načítám starší dnešní záznamy.{% elif state_attr('sensor.jarvis_dnes_prodano_za','quality')=='partial' %}Část dne čeká na doplnění údajů.{% endif %}
{% if state_attr('sensor.jarvis_dnes_prodano_za','fx_provisional') %}Kurz ČNB je zatím předběžný.{% endif %}"""}

def energy_overview_card():
 return {'type':'markdown','content':"""### Dnešní tok a bilance
{% macro amount(v,unit) -%}{{ ('%.2f'|format(v|float))|replace('.', ',') if is_number(v) else '—' }} {{ unit }}{%- endmacro %}
**Odebráno:** {{ amount(state_attr('sensor.jarvis_dnes_prodano_za','import_kwh'),'kWh') }} · **Dodáno:** {{ amount(state_attr('sensor.jarvis_dnes_prodano_za','export_kwh'),'kWh') }}

**Prodej po poplatku minus nákup:** {{ amount(states('sensor.jarvis_dnes_bilance_site'),'Kč') }}
{% if state_attr('sensor.jarvis_dnes_prodano_za','quality')=='partial' %}Doložená část dne; úplná peněžní bilance zatím není dostupná.{% endif %}
{% set gaps=state_attr('sensor.jarvis_dnes_prodano_za','gap_seconds') %}{% if is_number(gaps) and gaps|float>30 %}V měření jsou mezery; energii doplňují dostupné čítače, časový průběh a výnos zůstávají odhadem.{% endif %}
Peněžní bilance není zisk celé elektrárny; nezahrnuje investici ani opotřebení baterie.
"""}

def cash_block():return {'type':'vertical-stack','cards':[{'type':'grid','columns':2,'square':False,'cards':[money_card('purchase'),money_card('sale')]},status_card(),energy_overview_card()]}

def offload_cash_blocks(text,expected=4):
 """Replace only known cash-card line spans; preserve all other root YAML bytes."""
 import yaml
 spans=[];seen=set()
 def visit(node):
  if id(node) in seen:return
  seen.add(id(node))
  if isinstance(node,yaml.MappingNode):
   pairs={k.value:v for k,v in node.value if isinstance(k,yaml.ScalarNode)}
   if pairs.get('type') and pairs['type'].value=='vertical-stack' and 'cards' in pairs:
    try:value=yaml.safe_load(yaml.serialize(node))
    except yaml.YAMLError:value={}
    cards=value.get('cards',[])
    first=cards[0].get('cards',[]) if cards and isinstance(cards[0],dict) else []
    if len(first)==2 and first[0].get('content','').startswith('### Dnes nakoupeno za') and first[1].get('content','').startswith('### Dnes prodáno za'):
     if set(value)-{'type','cards','grid_options','visibility'}:raise ValueError('Cash card has extra layout fields')
     if len(cards)!=2 or not cards[1].get('content','').startswith('Průběžný odhad · dnešní den'):raise ValueError('Cash-card layout differs')
     spans.append((node.start_mark.line,node.end_mark.line,node.start_mark.column-2,{k:v for k,v in value.items() if k not in ('type','cards')}));return
   for _,v in node.value:visit(v)
  elif isinstance(node,yaml.SequenceNode):
   for v in node.value:visit(v)
 visit(yaml.compose(text))
 if len(spans)!=expected:raise ValueError('Expected exact cash-card count; got '+str(len(spans)))
 lines=text.splitlines(keepends=True)
 for start,end,indent,extras in sorted(spans,reverse=True):
  if indent<0 or not lines[start].startswith(' '*indent+'- type:'):raise ValueError('Cash card is not a block sequence item')
  if extras:
   wrapper=yaml.safe_dump({'type':'vertical-stack',**extras},allow_unicode=True,sort_keys=False).splitlines()
   replacement=[' '*indent+'- '+wrapper[0]+'\n']+[' '*(indent+2)+l+'\n' for l in wrapper[1:]]
   replacement+=[' '*(indent+2)+'cards:\n',' '*(indent+2)+"- !include 'solar-cash-summary.yaml'\n"]
  else:replacement=[' '*indent+"- !include 'solar-cash-summary.yaml'\n"]
  lines[start:end]=replacement
 return ''.join(lines)

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
