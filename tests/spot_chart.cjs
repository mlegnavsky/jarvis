const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let Card,html='';const root={set innerHTML(v){html=v},querySelectorAll:()=>[]};
let now=Date.parse('2026-11-04T12:14:59Z');class Clock extends Date{constructor(...a){super(...(a.length?a:[now]))}static now(){return now}}
const ctx={Date:Clock,HTMLElement:class{attachShadow(){return root}},customElements:{get:()=>null,define:(n,c)=>Card=c},module:{exports:{}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('managed_sources/spot_control/card.js','utf8'),ctx);
const rows=[{time:'2026-11-04T12:15:00Z',price:4},{time:'2026-11-04T12:00:00Z',price:2},{time:'2026-11-04T12:30:00Z',price:-1}];const states={'sensor.jarvis_spot_ote':{attributes:{rows}},'input_number.jarvis_nakup_elektriny_cena':{state:'5'}};
const c=new Card();c.setConfig({});c.hass={states};assert(html.includes('data-price-slider'));assert(html.includes('5,000 Kč/kWh'));assert(html.includes('#13834c'));assert.equal(c.chartRows[0].price,2);
assert.equal(ctx.module.exports.price(states,now),2);now+=1000;assert.equal(ctx.module.exports.price(states,now),4);
c.selectedTime=rows[2].time;c.render();assert(html.includes('value="2"'));assert(html.includes('Prodej · test OTE<small>Teď 13:15 · 13:15–13:30</small><b>4,000'));
now+=3600000;assert.equal(ctx.module.exports.price(states,now),null);
c.day=1;c.render();assert(html.includes('Ceny pro tento den zatím nejsou dostupné.'));
console.log('PASS quarter boundary, independent selection, sorted chart, helper tariff, missing prices');
