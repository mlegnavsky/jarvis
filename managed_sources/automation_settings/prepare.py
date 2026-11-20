"""Replace only the approved automation view; preserve unrelated dashboard bytes."""
import json,re,yaml

def prepare(text):
 match=re.search(r'^- title: Automatizace\n(?:(?!^- (?:title:|!include)).|\n)*',text,re.M)
 if not match:raise ValueError('Automation view not found')
 old=yaml.safe_load(match.group(0))[0]
 if old.get('path')!='automatizace':raise ValueError('Unexpected automation view')
 cards=[c for c in old.get('cards',[]) if c.get('type')=='entities' or c.get('type')=='markdown' and any(t in c.get('content','') for t in ('Hlas','Přepínače','hlasový'))]
 view='- title: Automatizace\n  path: automatizace\n  icon: mdi:robot\n  type: panel\n  cards:\n  - type: iframe\n    url: /local/jarvis-owner-settings.html?v=1.0.0\n    aspect_ratio: 100%\n'
 return text[:match.start()]+view+text[match.end():],json.dumps({'cards':cards},ensure_ascii=False)
