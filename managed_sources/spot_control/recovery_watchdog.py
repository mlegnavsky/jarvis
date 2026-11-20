"""Native HA recovery of completed transport/measurement pauses, never live writes."""
TEMPLATE="""{% set a = state_attr('sensor.jarvis_energy_sales','settings') or {} %}
{% set s = state_attr('sensor.jarvis_energy_sales','last_stop') or {} %}
{% set p = state_attr('sensor.jarvis_energy_sales','native_program') or {} %}
{% set r = p.get('registers_146_177',[]) %}
{% set c = s.get('context') or {} %}
{% set fresh = as_timestamp(now())-as_timestamp(states.sensor.jarvis_energy_sales.last_updated,0) %}
{% set native_age = as_timestamp(now())-as_timestamp(p.get('captured_at'),0) %}
{% set h = c.get('health') or {} %}
{% set issues = h.get('issues') or [] %}
{% set check = namespace(valid=issues|length>0) %}
{% for issue in issues %}{% if issue is not mapping or issue.get('code') not in ['missing','unavailable','stale'] %}{% set check.valid=false %}{% endif %}{% endfor %}
{% set recoverable = s.get('reason') in ['guard','stop_recovery'] and c.get('triggers')==['measurement_or_health'] and h.get('healthy')==false and h.get('transient_only')==true and check.valid %}
{{ a.get('requested_automatic',false) and not a.get('automatic',false) and a.get('inhibited',false)
 and state_attr('sensor.jarvis_energy_sales','ready')==true and state_attr('sensor.jarvis_energy_sales','active')==false
 and states('sensor.jarvis_energy_sales')=='idle' and state_attr('sensor.jarvis_energy_sales','healthy')==true
 and s.get('purpose')=='automatic' and s.get('mode') in ['pv','bias'] and s.get('stop_verified')==true
 and not s.get('conflicts') and a.get('handled_stop_id')==s.get('id') and recoverable
 and fresh>=0 and fresh<20 and native_age>=0 and native_age<90
 and r|length==32 and r[0]==255 and r[1]==1 and r[20:26]==[30]*6
 and r[26:32]==[0,0,0,0,0,0] and r[8:14]|min>=500
 and states('sensor.inverter_grid_power')|float(-99999)>=-100 }}"""

def automation():
 return {'id':'jarvis_sales_confirmed_recovery','alias':'Jarvis obnova prodeje','initial_state':True,
 'description':'Obnoví pouze vlastníkem zapnutou automatiku po fyzicky potvrzeném ukončení přechodné chyby. Nikdy během zastavování, při poruše, cizím zásahu nebo ručním vypnutí.',
 'triggers':[{'trigger':'time_pattern','seconds':'/15'}],
 'conditions':[{'condition':'template','value_template':TEMPLATE},{'condition':'template','value_template':"{{ as_timestamp(now())-as_timestamp(this.attributes.last_triggered,0)>60 }}"}],
 'actions':[{'delay':{'seconds':10}},{'condition':'template','value_template':TEMPLATE},{'action':'jarvis_spot_control.resume_confirmed_sale','data':{'stop_id':"{{ (state_attr('sensor.jarvis_energy_sales','last_stop') or {}).get('id','') }}"}}],
 'mode':'single','max_exceeded':'silent'}

def recoverable_stop(s):
 try:from .sales import measurement_guard
 except ImportError:from sales import measurement_guard
 return s.get('purpose')=='automatic' and s.get('mode') in ('pv','bias') and measurement_guard(s)
