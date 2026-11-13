const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const classes={};vm.runInNewContext(fs.readFileSync(__dirname+'/../card.js','utf8'),{HTMLElement:class{},CustomEvent:class{},setTimeout,clearTimeout,customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c}});
(async()=>{
 const C=classes['jarvis-device-status'],c=new C(),calls=[];
 c.cfg={entity:'lock.front',kind:'lock',tap_action:{action:'more-info'}};
 c.h={states:{'lock.front':{state:'unlocked'}},callService:async(...args)=>calls.push(args)};
 c.dispatchEvent=()=>{};
 await c.activate();assert.equal(calls.length,1,'tapping unlocked lock must lock');
 assert.equal(calls[0][0],'lock');assert.equal(calls[0][1],'lock');assert.equal(calls[0][2].entity_id,'lock.front');
 assert.equal(c.h.states['lock.front'].state,'unlocked','service acceptance must not forge locked state');
 c.h.states['lock.front'].state='locked';await c.activate();assert.equal(calls.length,2,'locked lock must unlock on explicit tap');assert.equal(calls[1][1],'unlock');
 c.h.states['lock.front'].state='unavailable';await c.activate();assert.equal(calls.length,2,'offline lock must not receive action');
 const button={};c.shadowRoot={innerHTML:'',querySelector:()=>button};c.style={setProperty(){}};c.h.states['lock.front'].state='unlocked';c.setConfig(c.cfg);c.render();
 c.onpointerdown({button:0,clientX:10,clientY:10});c.onpointerup();c.onpointerleave();assert.equal(c.held,false,'touch pointerleave after release must not swallow click');
 await button.onclick({stopPropagation(){},preventDefault(){}});await Promise.resolve();assert.equal(calls.length,3,'real button click must reach lock service');
 console.log('Lock tap: toggle, touch release, no forged state and offline guard passed');
})().catch(e=>{console.error(e);process.exit(1)});
