"""Offline, revision-checked migration of explicitly selected legacy automations."""
import copy
import yaml

GUARD={'condition':'template','value_template':"{{ state_attr('sensor.jarvis_hlasovy_vystup', 'adapter') != 'active' }}"}
TARGET='media_player.homepod_obyvak_homepod_obyvak'

def guard_automations(content,selected_ids):
 items=yaml.safe_load(content)
 if not isinstance(items,list):raise ValueError('automation_list_required')
 found=set()
 for item in items:
  if str(item.get('id')) not in selected_ids:continue
  found.add(str(item['id']))
  actions=item.get('actions')
  if not isinstance(actions,list):raise ValueError('unexpected_actions')
  volume=[a for a in actions if isinstance(a,dict) and a.get('action')=='media_player.volume_set']
  if not volume or any(a.get('target',{}).get('entity_id')!=TARGET for a in volume):raise ValueError('unexpected_volume_target')
  conditions=item.setdefault('conditions',[])
  if not isinstance(conditions,list):raise ValueError('unexpected_conditions')
  if GUARD not in conditions:conditions.insert(0,copy.deepcopy(GUARD))
  guarded=[]
  for action in actions:
   if action in volume and (not guarded or guarded[-1]!=GUARD):guarded.append(copy.deepcopy(GUARD))
   guarded.append(action)
  item['actions']=guarded
 if found!=set(selected_ids):raise ValueError('selected_automation_missing')
 return yaml.safe_dump(items,allow_unicode=True,sort_keys=False)
