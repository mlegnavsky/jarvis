const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const classes={};vm.runInNewContext(fs.readFileSync('managed_sources/home_status/card.js','utf8'),{HTMLElement:class{},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c}});
const C=classes['jarvis-device-status'];
(async()=>{
 const calls=[],c=new C();c.cfg={entity:'switch.aqara_smart_plug_eu',heating_entity:'sensor.jarvis_topeni_child',tap_action:{action:'toggle'}};
 c.h={states:{'switch.aqara_smart_plug_eu':{state:'on'},'sensor.jarvis_topeni_child':{attributes:{mode:'auto'}}},callService:async(...a)=>calls.push(a)};
 assert.equal(typeof c.activate,'function');await c.activate();
 assert.equal(calls[0][0],'jarvis_solar_heating');assert.equal(calls[0][1],'set_mode');assert.equal(calls[0][2].room,'child');assert.equal(calls[0][2].mode,'off');
 calls.length=0;c.h.states['switch.aqara_smart_plug_eu'].state='off';await c.activate();assert.equal(calls[0][2].mode,'manual');
 calls.length=0;c.cfg={entity:'switch.other',tap_action:{action:'toggle'}};c.h.states['switch.other']={state:'on'};await c.activate();assert.equal(calls[0][0],'switch');assert.equal(calls[0][1],'turn_off');
 console.log('Heating click explicit owner intent: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
