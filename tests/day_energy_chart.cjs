const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
let Card;const ctx={HTMLElement:class{},customElements:{get:()=>false,define:(n,c)=>Card=c},Intl,Date,Math,Set,Number};
vm.runInNewContext(fs.readFileSync('managed_sources/energy_weather/power-sun.js','utf8'),ctx);
const c=new Card();
for(const [now,hours,start] of [['2026-10-30T12:00:00Z',24,'2026-10-29T23:00:00.000Z'],['2026-03-29T12:00:00Z',23,'2026-03-28T23:00:00.000Z'],['2026-10-25T12:00:00Z',25,'2026-10-24T22:00:00.000Z']]){
 const day=c.dayBounds(Date.parse(now));assert.equal(new Date(day.start).toISOString(),start);assert.equal((day.end-day.start)/3600000,hours);
}
for(const value of ['unknown','unavailable','',null,undefined])assert.equal(c.value(value),null);
assert.equal(c.value('0'),0);assert.equal(c.value('-120'),-120);
console.log('Daily chart: Prague/DST and missing readings passed');

assert.equal(c.reading([{t:0,v:50},{t:10,v:null},{t:20,v:0}],15,100),null);
assert.equal(c.reading([{t:0,v:50}],101,100),null);
assert.equal(c.reading([{t:0,v:50},{t:20,v:0}],25,100),0);

assert.equal(c.selectionTime(90001,90001),90001);
assert.equal(c.selectionTime(89999,100000),60000);
assert.equal(c.selectionTime(90001,100000),120000);
