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
assert.equal(c.selectionTime(90001,100000),100000);

assert.equal(c.selectionTime(90001,90002),90002);
c.selectedDate='2026-10-25';assert.equal((c.selectedBounds().end-c.selectedBounds().start)/3600000,25);
assert.equal(c.shiftDay(1),'2026-10-26');assert.equal(c.shiftDay(-1),'2026-10-24');
c.h={states:{'sensor.jarvis_spot_ote':{attributes:{rows:[{time:'2026-10-30T12:00:00Z',price:-1.25}]}}}};
assert.equal(c.priceAt(Date.parse('2026-10-30T12:14:00Z'),[],0),-1.25);
assert.equal(c.priceAt(Date.parse('2026-10-30T12:15:00Z'),[],0),null);
assert.equal(c.priceAt(100,[{t:50,v:5}],200),5);
console.log('Expanded chart: day navigation, negative spot price, interval expiry passed');

(async()=>{
 const card=new Card(),requests=[];card.render=()=>{};card.h={callApi:()=>new Promise(resolve=>requests.push(resolve))};
 const first=card.chooseDay('2020-01-01'),second=card.chooseDay('2020-01-02');
 requests[1]([{entity_id:'unused'}].slice(0,0));await second;const wanted=card.historyDay;
 requests[0]([]);await first;assert.equal(card.historyDay,wanted);assert.equal(card.selectedDate,'2020-01-02');
 console.log('Out-of-order history response ignored');
})().catch(e=>{console.error(e);process.exitCode=1});

{
const card=new Card(),start=Date.parse('2026-10-30T12:00:00Z');
card.h={states:{'sensor.jarvis_spot_ote':{attributes:{rows:[{time:new Date(start).toISOString(),price:5},{time:new Date(start+900000).toISOString(),price:null}]}}}};
const seg=card.priceSegments(start,start+1800000,[{t:start,v:3}],start+1800000);
assert.equal(seg[0].v,5);assert.equal(seg[1].v,null);assert.equal(seg.length,2);
}

{
const card=new Card(),points=[{t:0,v:50},{t:10,v:null},{t:20,v:70}];
assert.equal(card.batteryAt(points,15,100).value,65);assert.equal(card.batteryAt(points,15,100).estimated,true);
assert.equal(card.batteryAt(points,5,100).value,55);assert.equal(card.batteryAt(points,0,100).estimated,false);
assert.equal(card.batteryAt(points,30,25).value,null);assert.equal(card.batteryAt(points.slice(0,2),15,100).value,null);
const dense=Array.from({length:1000},(_,i)=>({t:i*10,v:i===500?null:i===400?99999:i}));
const compact=card.plotPoints(dense);assert(compact.length<20);assert(compact.some(p=>p.v===99999));assert(compact.some(p=>p.v===null));
card.h={states:{'sensor.jarvis_pocasi_zitenice':{state:'ready',attributes:{rows:[{time:'2026-10-30T12:00:00Z',temperature_2m:5,weather_code:61}]}}}};
assert.equal(card.weatherAt(Date.parse('2026-10-30T12:30:00Z')).temperature_2m,5);
assert.equal(card.weatherAt(Date.parse('2026-10-29T12:30:00Z')),null);assert.equal(card.weatherInfo({weather_code:71}).label,'Sněžení');
}
(async()=>{
 const card=new Card();card.render=()=>{};card.historyCache=new Map();let calls=0;card.h={callApi:async()=>{calls++;return []}};
 await card.chooseDay('2020-02-01');await card.chooseDay('2020-02-02');await card.chooseDay('2020-02-01');assert.equal(calls,2);console.log('History cache reuses visited days');
})().catch(e=>{console.error(e);process.exitCode=1});

(async()=>{
 const card=new Card();card.render=()=>{};card.historyCache=new Map();const today=card.dayBounds(),yesterday=card.dayBounds(today.start-3600000);let calls=0;
 card.historyCache.set(yesterday.start,{rows:{},time:yesterday.end-60000});card.h={callApi:async()=>{calls++;return []}};
 await card.chooseDay(card.dateKey(yesterday.start+12*3600000));assert.equal(calls,1);console.log('Incomplete overnight cache refreshed');
})().catch(e=>{console.error(e);process.exitCode=1});

{
 const card=new Card();card.selectedDate='2026-10-30';card.period='week';let b=card.periodBounds();assert.equal(card.dateKey(b.start),'2026-10-26');assert.equal(card.dateKey(b.end),'2026-11-02');
 card.period='month';b=card.periodBounds();assert.equal(card.dateKey(b.start),'2026-10-01');assert.equal(card.dateKey(b.end),'2026-11-01');
 card.period='year';b=card.periodBounds();assert.equal(card.dateKey(b.start),'2026-01-01');assert.equal(card.dateKey(b.end),'2027-01-01');
 assert(card.moonInfo(Date.parse('2026-10-30T00:00:00Z')).lit>=0);
 card.selectedDate='2020-01-01';card.period='week';b=card.periodBounds();card.statsBounds=b;card.h={states:{}};card.stats=Object.fromEntries(card.energyIds().map(id=>[id,[{start:b.start,change:1},{start:b.start+86400000,change:2}]]));assert.equal(card.energyTotals()[0],3);card.stats={};assert.equal(card.energyTotals()[0],null);
}
