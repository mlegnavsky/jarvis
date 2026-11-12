const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const registered=new Map(),visited=[],events=[];
vm.runInNewContext(fs.existsSync(__dirname+'/../room-panel.js')?fs.readFileSync(__dirname+'/../room-panel.js','utf8'):'',{
 HTMLElement:class{},customElements:{get:n=>registered.get(n),define:(n,c)=>registered.set(n,c)},window:{dispatchEvent:e=>events.push(e.type),loadCardHelpers:async()=>({createCardElement:()=>({})})},history:{pushState:(_a,_b,path)=>visited.push(path)},CustomEvent:class{},Event:class{constructor(type){this.type=type;}}
});
assert.ok(registered.has('jarvis-room-panel'),'room panel must be registered');
const C=registered.get('jarvis-room-panel');
const p=new C();p.cfg={room_index:0,rooms:[{path:'/hlavni-prehled/pokoj-obyvak'},{path:'/hlavni-prehled/pokoj-detsky'},{path:'/hlavni-prehled/pokoj-chodba'}],neighbors:{left:'/hlavni-prehled/pokoj-detsky',up:'/hlavni-prehled/pokoj-chodba'}};
assert.equal(p.swipeDirection(120,12,220),'left');
assert.equal(p.swipeDirection(-120,12,220),'right');
assert.equal(p.swipeDirection(10,120,220),'up');
assert.equal(p.swipeDirection(10,-120,220),'down');
assert.equal(p.swipeDirection(20,0,100),null,'tap must not navigate');
assert.equal(p.swipeDirection(75,80,200),null,'ambiguous diagonal must not navigate');
assert.equal(p.swipeDirection(100,0,1500),null,'long hold must not navigate');
assert.equal(p.neighbor('left').path,'/hlavni-prehled/pokoj-detsky');
assert.equal(p.neighbor('up').path,'/hlavni-prehled/pokoj-chodba');
assert.equal(p.neighbor('right'),undefined,'a wall must not wrap to another room');
p.navigate({path:'/hlavni-prehled/pokoj-detsky'});
assert.deepEqual(visited,['/hlavni-prehled/pokoj-detsky']);
assert.deepEqual(events,['location-changed']);
p.navigate({path:'https://untrusted.example'});assert.equal(visited.length,1);
console.log('Room swipe: four directions, threshold, diagonal, hold and spatial boundaries passed');
(async()=>{
 const nodes=new Map();p.shadowRoot={innerHTML:'',querySelector:s=>{if(!nodes.has(s))nodes.set(s,{appendChild(){}});return nodes.get(s)},querySelectorAll:()=>[]};p.childrenCards=[];p.addEventListener=()=>{};
 p.cfg.title='Obývák';p.cfg.picture={type:'picture-elements'};
 await p.build();
 const html=p.shadowRoot.innerHTML;
 assert.ok(html.indexOf('<div class="actions">')<html.indexOf('<div id="stage"'),'controls above room picture');
 assert.ok(html.indexOf('<div class="metrics">')>html.indexOf('<div id="picture">'),'readings at bottom of picture');
 assert.ok(html.includes('touch-action:none'),'four-direction swipe surface must not be cancelled by browser vertical panning');
 const event=(x,y,time,path=[{id:'picture'}])=>({clientX:x,clientY:y,timeStamp:time,pointerId:1,composedPath:()=>path,preventDefault(){},stopPropagation(){}});
 p.onpointerdown(event(50,50,0));p.onpointerup(event(160,50,200));assert.equal(visited.at(-1),'/hlavni-prehled/pokoj-detsky');
 p.onpointerdown(event(50,50,300));p.onpointerup(event(50,160,500));assert.equal(visited.at(-1),'/hlavni-prehled/pokoj-chodba');
 const count=visited.length;p.onpointerdown(event(50,50,600,[{tagName:'BUTTON'},{id:'picture'}]));p.onpointerup(event(160,50,800));assert.equal(visited.length,count,'gesture on controls must not navigate');
 p.onpointerdown(event(50,50,900));p.onpointercancel();p.onpointerup(event(160,50,1100));assert.equal(visited.length,count,'cancelled gesture must not navigate');
 console.log('Room layout ordering, four-way surface, pointer navigation and control/cancel guards passed');
})().catch(e=>{console.error(e);process.exitCode=1});
