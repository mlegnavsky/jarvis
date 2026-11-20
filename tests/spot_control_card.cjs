const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const registry=new Map();let html='';const root={set innerHTML(x){html=x},get innerHTML(){return html},querySelectorAll:()=>[]};
const ctx={HTMLElement:class{attachShadow(){return root}},customElements:{get:k=>registry.get(k),define:(k,v)=>registry.set(k,v)},setInterval:()=>0,clearInterval:()=>{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('managed_sources/spot_control/card.js','utf8'),ctx);
const c=new(registry.get('jarvis-spot-control-card'))();c.setConfig({});c.hass={states:{}};
assert(html.includes('Dobít baterii ze sítě'));assert(html.includes('data-action="start_test" disabled'));
c.hass={states:{'sensor.jarvis_spot_control':{state:'idle',attributes:{ready:true,telemetry_fresh:true,active:false}}}};
assert(!html.includes('data-action="start_test" disabled'));
let calls=[];c.h.callService=async(...a)=>calls.push(a);
(async()=>{await c.command('start_test');assert.equal(calls[0][0],'jarvis_spot_control');assert.equal(calls[0][1],'start_test');c.h.callService=async()=>{throw Error('test rejection')};await c.command('stop_restore');assert(html.includes('test rejection'));console.log('PASS: registration, unavailable/ready state, service route, surfaced errors')})();
