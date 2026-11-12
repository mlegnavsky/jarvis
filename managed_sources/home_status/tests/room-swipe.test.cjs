const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const registered=new Map(),visited=[],events=[];
vm.runInNewContext(fs.existsSync(__dirname+'/../room-panel.js')?fs.readFileSync(__dirname+'/../room-panel.js','utf8'):'',{
 HTMLElement:class{},customElements:{get:n=>registered.get(n),define:(n,c)=>registered.set(n,c)},window:{dispatchEvent:e=>events.push(e.type)},history:{pushState:(_a,_b,path)=>visited.push(path)},CustomEvent:class{},Event:class{constructor(type){this.type=type;}}
});
assert.ok(registered.has('jarvis-room-panel'),'room panel must be registered');
const C=registered.get('jarvis-room-panel');
const p=new C();p.cfg={room_index:0,rooms:[{path:'one'},{path:'two'},{path:'three'}]};
assert.equal(p.swipeDirection(120,12,220),-1);
assert.equal(p.swipeDirection(-120,12,220),1);
assert.equal(p.swipeDirection(20,0,100),0,'tap must not navigate');
assert.equal(p.swipeDirection(70,120,200),0,'vertical scroll must not navigate');
assert.equal(p.swipeDirection(100,0,1500),0,'long hold must not navigate');
assert.equal(p.neighbor(-1).path,'three','previous room wraps');
assert.equal(p.neighbor(1).path,'two');
p.navigate({path:'/hlavni-prehled/pokoj-detsky'});
assert.deepEqual(visited,['/hlavni-prehled/pokoj-detsky']);
assert.deepEqual(events,['location-changed']);
p.navigate({path:'https://untrusted.example'});assert.equal(visited.length,1);
console.log('Room swipe: direction, threshold, scroll, hold and wrap passed');
