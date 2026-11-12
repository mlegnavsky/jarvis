"""Connect existing room panels by their positions in the owner's floorplan."""
import re
import sys
from pathlib import Path
import yaml

NEIGHBORS={
 'obyvak':{'left':'detsky','right':'loznice','up':'chodba'},
 'detsky':{'right':'obyvak','up':'kuchyne'},
 'kuchyne':{'right':'chodba','down':'detsky'},
 'chodba':{'left':'kuchyne','right':'koupelna','down':'obyvak'},
 'koupelna':{'left':'chodba','down':'loznice'},
 'loznice':{'left':'obyvak','up':'koupelna'},
}

def refine(text):
    starts=list(re.finditer(r'^- title: .*\n  path: pokoj-([a-z]+)\n',text,re.M))
    if len(starts)!=6:raise ValueError('Expected six room subviews')
    for match in reversed(starts):
        next_view=re.search(r'^- (?:title:|!include)',text[match.end():],re.M)
        end=match.end()+next_view.start() if next_view else len(text)
        view=yaml.safe_load(text[match.start():end])[0]
        panel=view['cards'][0]
        if panel.get('type')!='custom:jarvis-room-panel':raise ValueError('Room panel expected')
        panel['neighbors']={d:'/hlavni-prehled/pokoj-'+r for d,r in NEIGHBORS[match[1]].items()}
        text=text[:match.start()]+yaml.safe_dump([view],allow_unicode=True,sort_keys=False,width=1000)+text[end:]
    return text

if __name__=='__main__':
    Path(sys.argv[2]).write_text(refine(Path(sys.argv[1]).read_text()))
