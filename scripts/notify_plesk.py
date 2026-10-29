"""Notify the known Plesk panel without logging its secret query or disabling TLS."""
import os
from urllib.parse import urlsplit,urlunsplit,parse_qs
import urllib.request

def canonical_url(value):
 u=urlsplit(value)
 if u.scheme!='https' or u.username or u.password or u.fragment:raise ValueError('invalid webhook address')
 if (u.hostname,u.port) not in (('give-get.com',8443),('lister.thajsky-raj.cz',None),('lister.thajsky-raj.cz',443)):raise ValueError('unexpected Plesk host')
 if u.path!='/modules/git/public/web-hook.php' or not parse_qs(u.query).get('uuid'):raise ValueError('invalid webhook path or identifier')
 return urlunsplit(('https','lister.thajsky-raj.cz',u.path,u.query,''))

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def main():
 value=os.environ.get('LAB_WEBHOOK','')
 if not value:
  print('::warning::Plesk notification not configured. Live deployment unverified.');return 0
 try:
  url=canonical_url(value)
  with urllib.request.build_opener(NoRedirect).open(url,timeout=30) as response:
   if response.status!=200:raise ValueError('unexpected response')
  print('Plesk notification accepted; HTTP content still requires verification.');return 0
 except Exception as e:
  # Exception text can contain the private URL. Never print it.
  print('::error::Plesk notification failed ('+type(e).__name__+'); secret URL omitted.');return 1
if __name__=='__main__':raise SystemExit(main())
