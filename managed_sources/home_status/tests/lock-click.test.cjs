const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const classes={};vm.runInNewContext(fs.readFileSync(__dirname+'/../card.js','utf8'),{HTMLElement:class{},CustomEvent:class{},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c}});
(async()=>{
 const C=classes['jarvis-device-status'],c=new C(),calls=[];
 c.cfg={entity:'lock.front',kind:'lock',tap_action:{action:'more-info'}};
 c.h={states:{'lock.front':{state:'unlocked'}},callService:async(...args)=>calls.push(args)};
 c.dispatchEvent=()=>{};
 await c.activate();assert.equal(calls.length,1,'tapping unlocked lock must lock');
 assert.equal(calls[0][0],'lock');assert.equal(calls[0][1],'lock');assert.equal(calls[0][2].entity_id,'lock.front');
 assert.equal(c.h.states['lock.front'].state,'unlocked','service acceptance must not forge locked state');
 c.h.states['lock.front'].state='locked';await c.activate();assert.equal(calls.length,1,'locked lock must never unlock on tap');
 c.h.states['lock.front'].state='unavailable';await c.activate();assert.equal(calls.length,1,'offline lock must not receive action');
 console.log('Lock tap: explicit lock only, no forged state, no unlock/offline writes passed');
})().catch(e=>{console.error(e);process.exit(1)});
