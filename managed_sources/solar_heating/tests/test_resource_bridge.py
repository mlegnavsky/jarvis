import unittest
from types import SimpleNamespace as NS

class ResourceTests(unittest.IsolatedAsyncioTestCase):
 async def test_only_owned_resource_url_is_updated_and_repeat_is_idempotent(self):
  from resource_bridge import refresh_resource
  rows=[{'id':'ours','url':'/local/jarvis-home-status.js?v=old','type':'module'}, {'id':'other','url':'/local/other.js','type':'module'}];calls=[]
  async def info():return {'resources':len(rows)}
  async def update(id,data):
   calls.append((id,data));item=next(r for r in rows if r['id']==id);item.update(data);return dict(item)
  collection=NS(async_get_info=info,async_items=lambda:rows,async_update_item=update)
  hass=NS(data={'lovelace':NS(resource_mode='storage',resources=collection)})
  result=await refresh_resource(hass);self.assertEqual(result['status'],'ready')
  self.assertEqual(calls,[('ours',{'url':'/local/jarvis-home-status.js?v=heat123'})]);self.assertEqual(rows[1]['url'],'/local/other.js')
  await refresh_resource(hass);self.assertEqual(len(calls),1)
 async def test_missing_or_yaml_resources_are_never_blindly_written(self):
  from resource_bridge import refresh_resource
  self.assertEqual((await refresh_resource(NS(data={})))['status'],'unavailable')
