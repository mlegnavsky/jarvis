"""Migrate only room subviews; preserve all other dashboard text and !includes."""
import copy
import re
import sys
from pathlib import Path
import yaml


def migrate(text):
    starts=list(re.finditer(r'^- title: .*\n  path: pokoj-[a-z]+\n',text,re.M))
    rooms=[]
    for match in starts:
        end=re.search(r'^- (?:title:|!include)',text[match.end():],re.M)
        finish=match.end()+end.start() if end else len(text)
        view=yaml.safe_load('views:\n'+text[match.start():finish])['views'][0]
        rooms.append((match.start(),finish,view))
    if len(rooms)!=6:raise ValueError('Expected six existing room views')
    navigation=[{'title':v['title'].split(' · ')[0],'path':'/hlavni-prehled/'+v['path']} for _,_,v in rooms]
    for index,(start,end,view) in reversed(list(enumerate(rooms))):
        cards=view['cards'];pictures=[c for c in cards if c.get('type')=='picture-elements']
        if len(pictures)!=1:raise ValueError('Expected one floorplan per room')
        picture=copy.deepcopy(pictures[0]);picture.pop('title',None)
        metrics=[];elements=[];status=None
        for element in picture['elements']:
            entity=element.get('entity','')
            if entity.startswith('sensor.') and ('teplota' in entity or 'vlhkost' in entity):
                metrics.append({'name':'Vlhkost' if 'vlhkost' in entity else 'Teplota','entity':entity})
            elif entity.startswith('sensor.jarvis_topeni_'):
                status=entity
            else:elements.append(element)
        picture['elements']=elements
        actions=[];extra=[]
        for card in cards:
            if card is pictures[0]:continue
            if card.get('type')=='grid':
                for button in card['cards']:
                    action=button['tap_action']
                    if action.get('perform_action')!='jarvis_solar_heating.set_mode':raise ValueError('Unexpected room action')
                    on=action['data']['mode']=='grid_manual'
                    actions.append({'label':'Zapnout topení' if on else 'Vypnout topení','subtitle':'+ dobíjení baterie 1 kW' if on else 'Zastavit radiátor','tap_action':action})
            else:extra.append(card)
        panel={'type':'custom:jarvis-room-panel','title':navigation[index]['title'],'room_index':index,'rooms':navigation,'picture':picture,'metrics':metrics,'actions':actions,'extra':extra}
        if status:panel['status_entity']=status
        view['cards']=[panel]
        view['title']=navigation[index]['title']
        view['type']='panel'
        replacement=yaml.safe_dump([view],allow_unicode=True,sort_keys=False,width=1000)
        text=text[:start]+replacement+text[end:]
    return text


if __name__=='__main__':
    Path(sys.argv[2]).write_text(migrate(Path(sys.argv[1]).read_text()))
