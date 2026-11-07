const assert=require('node:assert/strict');
const {dailyEvidenceView}=require('../managed_sources/spot_hub/hub.js');
assert.equal(typeof dailyEvidenceView,'function');
assert.match(dailyEvidenceView({latest:null}).summary,/nejsou/);
const result=dailyEvidenceView({date:'2026-11-07',snapshots:[{}],latest:{as_of:1794038400,energy_kwh:{production:0,house:null,export:1},finance:null,electrical:{loss_residual_w:140},operation:{reason:'Čekám na rezervu'},forecast:{forecast_day:'2026-11-08',forecast_pv_kwh:10}}});
assert.match(result.energy,/0,00/);assert.match(result.energy,/—/);
assert.match(result.money,/—/);assert.match(result.summary,/část/);
assert.match(result.operation,/Čekám na rezervu/);
console.log('Daily evidence UI: PASS');
