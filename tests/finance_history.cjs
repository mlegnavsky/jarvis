const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('managed_sources/spot_hub/hub.js','utf8');
// Exercise the real reader without mounting a UI or calling device services.
const methods=source.slice(source.indexOf(' async readFinances(){'),source.indexOf(' async finance(){'));
const context={Intl,Date,Map,Promise,shiftDate:require('../managed_sources/spot_hub/hub.js').shiftDate,numeric:v=>v!==null&&v!==undefined&&v!==''&&!['unknown','unavailable'].includes(v)&&Number.isFinite(Number(v))?Number(v):null,today:()=> '2026-11-15'};
vm.createContext(context);vm.runInContext('class Reader{'+methods+'};this.Reader=Reader',context);
(async()=>{const r=new context.Reader();r.period='day';r.date='2026-11-14';const calls=[];
const row=(id,amount,energy,time)=>({entity_id:id,state:'unknown',last_updated:time,attributes:{date:'2026-11-14',known_sale_czk:amount,known_purchase_czk:amount,export_kwh:energy,import_kwh:.23,quality:'partial',as_of:Date.parse(time)/1000}});
r.h={states:{},callApi:async(method,path)=>{calls.push(path);const all=new URL('http://ha/'+path).searchParams.get('significant_changes_only')==='0';return [[row('sensor.jarvis_dnes_prodano_za',2.35,.65,'2026-11-14T06:00:00Z'),...(all?[row('sensor.jarvis_dnes_prodano_za',22.1,6.1,'2026-11-14T22:59:40Z')]:[])],[row('sensor.jarvis_dnes_nakoupeno_za',1.15,0,'2026-11-14T22:59:40Z')]];}};
let out=await r.readFinances();assert.equal(out.known_sale_czk,22.1,'Attribute-only increases must survive unknown monetary state');assert.equal(out.export_kwh,6.1);assert.equal(out.sale_czk,null,'Partial estimate must stay partial');
const url=new URL('http://ha/'+calls[0]);assert.ok(Date.parse(url.searchParams.get('end_time'))-Date.parse(url.pathname.split('/').pop())<=900000,'Read only closing cumulative snapshots');
await r.readFinances();assert.equal(calls.length,1,'Revisit must reuse the closed-day result');
r.h.callApi=async()=>{throw Error('offline')};r.date='2026-11-13';await assert.rejects(r.readFinances());await assert.rejects(r.readFinances(),'Failed reads must not become cached empty days');
r.financeDays.clear();r.period='week';r.date='2026-11-14';let active=0,peak=0;r.h.callApi=async(method,path)=>{active++;peak=Math.max(peak,active);await new Promise(resolve=>setTimeout(resolve,2));active--;const date=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(Date.parse(new URL('http://ha/'+path).searchParams.get('end_time'))-1);const sample=row('sensor.jarvis_dnes_prodano_za',20,5,date+'T12:00:00Z');sample.attributes.date=date;return [[sample]];};
out=await r.readFinances();assert.equal(out.known_sale_czk,120);assert.equal(out.export_kwh,30);assert.equal(out.quality,'partial');assert.ok(peak<=4);assert.equal(out.available_days,6,'Initial snapshot retains a day even if last update was at noon');
console.log('Finance unknown-state attributes, final-day window, cache and partial-data honesty PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
