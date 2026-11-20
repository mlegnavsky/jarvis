const assert = require('node:assert/strict');
const fs = require('node:fs');
for (const path of ['managed_sources/spot_control/card.js','managed_sources/spot_dashboard/card.js']) {
 const source=fs.readFileSync(path,'utf8');
 const fmt=(x,n=1)=>Number.isFinite(x)?x.toLocaleString('cs-CZ',{maximumFractionDigits:n}):'—';
 const expression=source.match(/const w=(.*);/)[1];
 const w=Function('fmt','return '+expression)(fmt);
 for (const [v,out] of [[0,'0 W'],[11,'11 W'],[390,'390 W'],[-20,'-20 W'],[999,'999 W'],[1000,'1 kW'],[5300,'5,3 kW'],[null,'—']]) assert.equal(w(v),out,path);
}
console.log('16 power formatting cases passed');
