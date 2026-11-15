const assert=require('node:assert/strict'),fs=require('node:fs');
const A=require('../managed_sources/spot_hub/accounting.js');
assert.equal(A.groups([{date:'2026-11-14',known_sale_czk:null,known_purchase_czk:1}])[0].known_sale_czk,null,'Missing revenue must not become a zero-height measured bar');
const html=fs.readFileSync('managed_sources/spot_hub/index.html','utf8');
assert.ok(html.indexOf('jarvis-accounting.js')>=0&&html.indexOf('jarvis-accounting.js')<html.indexOf('jarvis-spot-hub.js'),'Load accounting before the UI; otherwise the old partial sensor path remains active');
const start=Date.parse('2026-11-13T23:00Z'),end=start+86400000;
const h={states:{'sensor.jarvis_energy_archive':{attributes:{server:{finance:{schema:2,days:[{date:'2026-11-14',export_kwh:6.2,import_kwh:.23,priced_export_kwh:6.2,known_sale_czk:21.7,known_purchase_czk:1.15,quality:'estimate'}]}}}}},callWS:()=>{throw Error('Must not fetch recorder for cached archive totals')}};
(async()=>{
 const r=await A.read(h,{start,end},end+3600000);assert.equal(r.export_kwh,6.2);assert.equal(r.sale_czk,21.7);assert.equal(r.available_days,1);
 const partial=await A.read(h,{start:start-86400000,end},end+3600000);assert.equal(partial.sale_czk,null);assert.equal(partial.quality,'partial');assert.equal(partial.expected_days,2);
 console.log('UI accounting load order, archive fast path and missing-day honesty PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
