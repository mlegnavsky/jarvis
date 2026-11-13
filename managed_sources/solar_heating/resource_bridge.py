"""Refresh only the existing home-status module using HA's resource collection."""
from urllib.parse import urlsplit
URL='/local/jarvis-home-status.js?v=heat130'
async def refresh_resource(hass):
 data=hass.data.get('lovelace')
 if data is None or getattr(data,'resource_mode',None)!='storage':return {'status':'unavailable'}
 resources=data.resources
 await resources.async_get_info()  # Official collection lazily loads its store.
 items=[i for i in resources.async_items() if isinstance(i.get('url'),str) and i['url'].startswith('/local/') and urlsplit(i['url']).path=='/local/jarvis-home-status.js']
 if len(items)!=1:return {'status':'unavailable'}
 item=items[0]
 if item['url']!=URL:
  result=await resources.async_update_item(item['id'],{'url':URL})
  if result.get('url')!=URL:raise RuntimeError('Resource URL not confirmed')
 return {'status':'ready','url':URL}
