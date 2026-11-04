"""Refine the current dashboard; preserve every other view verbatim."""
import base64, re, sys, copy
import yaml
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!include', lambda l,n:l.construct_scalar(n))
def refine(source):
    root=yaml.compose(source,Loader=Loader)
    views=next(v for k,v in root.value if k.value=='views')
    home_node=views.value[0]
    home=yaml.load(source,Loader=Loader)['views'][0]
    # Keep the original solid room shading, with a 5px extension and 7px feather.
    def shade(m):
        svg=base64.b64decode(m[1]).decode()
        if 'room-shade' not in svg: return m[0]
        svg=re.sub(r'<defs>.*?</defs>','',svg)
        # The two rooms without switches originally had the darker overlay.
        dark=any(p in svg for p in ['250,195 682,195','974,422 1240,422'])
        alpha='b3' if dark else '66'
        defs='<defs><filter id="roomFeather" x="-15%" y="-15%" width="130%" height="130%" color-interpolation-filters="sRGB"><feMorphology in="SourceGraphic" operator="dilate" radius="5"/><feGaussianBlur stdDeviation="7"/></filter></defs>'
        svg=svg.replace('<polygon',defs+'<polygon',1)
        svg=re.sub(r'fill="url\(#[^)]+\)"',f'fill="#00152b{alpha}" filter="url(#roomFeather)"',svg)
        return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
    # Operate on all home SVGs including its mobile floorplan.
    home=yaml.load(re.sub(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)',shade,yaml.safe_dump(home,allow_unicode=True,sort_keys=False)),Loader=Loader)
    left,right=home['sections']
    mobile=left['cards'][2]
    assert mobile['type']=='vertical-stack' and mobile['cards'][0]['type']=='picture-elements'
    energy=next(c for c in right['cards'] if c['type']=='picture-elements')
    weather=copy.deepcopy(right['cards'][0]);weather['show_forecast']=False
    weather.pop('grid_options',None)
    descriptions=next(c for c in right['cards'] if c['type']=='markdown')
    details=copy.deepcopy(descriptions)
    details['content']='<details>\n<summary>Podrobnosti energie</summary>\n\n'+details['content']+'\n\n</details>'
    details.pop('grid_options',None)
    mobile['cards']=[mobile['cards'][0],copy.deepcopy(energy),weather,details,
        {'type':'markdown','content':'<details>\n<summary>Další přehledy a ovládání</summary>\n\n[Zařízení](/hlavni-prehled/zarizeni) · [Automatizace](/hlavni-prehled/automatizace) · [Počasí](/hlavni-prehled/pocasi)\n\n</details>'}]
    mobile['cards'].extend(copy.deepcopy(c) for c in right['cards'] if c['type'] in ('custom:jarvis-battery-overview', 'picture-entity'))
    # Desktop side column remains intact; on mobile its compact counterparts are above.
    right['visibility']=[{'condition':'screen','media_query':'(min-width: 768px)'}]
    rendered=yaml.safe_dump(home,allow_unicode=True,sort_keys=False,width=140)
    # List item's first dash is outside the node range; indent following lines accordingly.
    rendered=rendered.rstrip().replace('\n','\n  ')+'\n'
    return source[:home_node.start_mark.index]+rendered+source[home_node.end_mark.index:]
if __name__=='__main__':
    source=open(sys.argv[1]).read(); result=refine(source)
    before=yaml.load(source,Loader=Loader);after=yaml.load(result,Loader=Loader)
    assert before['views'][1:]==after['views'][1:]
    cards=after['views'][0]['sections'][0]['cards'][2]['cards']
    assert [c['type'] for c in cards[:3]]==['picture-elements','picture-elements','weather-forecast']
    assert sum(e['type']=='state-label' for e in cards[1]['elements'])==6
    assert cards[2]['show_forecast'] is False
    assert 'room-shade' not in str(after)
    open(sys.argv[2],'w').write(result)
    print('PASS: other views unchanged; mobile image order, six values, compact weather')
