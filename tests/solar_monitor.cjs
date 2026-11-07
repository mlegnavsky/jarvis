const assert=require('node:assert/strict');
const {monitorView}=require('../managed_sources/spot_hub/hub.js');
let v=monitorView({checked_at:1000,status:'ready',operation:{label:'Malý trvalý přetok',result:'measured_export'},measurements:{}},true,1001);
assert.match(v.summary,/Malý trvalý přetok/);assert.match(v.result,/měnič/);
v=monitorView({checked_at:900,status:'ready',operation:{result:'measured_export'}},true,1001);
assert.match(v.summary,/čerstv/);assert.doesNotMatch(v.result,/Potvrzen/);
v=monitorView({checked_at:1000,status:'warning',alerts:[{message:'Chybí data'}]},true,1001);
assert.equal(v.alerts[0],'Chybí data');
console.log('solar monitor view PASS');
