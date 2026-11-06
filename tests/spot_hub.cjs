const assert=require('node:assert/strict');const m=require('../managed_sources/spot_hub/hub.js');
assert.equal(m.money(null),'— Kč');assert.equal(m.money(0),'0,00 Kč');assert.equal(m.money(1.2),'1,20 Kč');
const now=Date.now()/1000;assert.equal(m.currentNet({price:{start:now-20,end:now+20,net:5.43}},now),5.43);assert.equal(m.currentNet({price:{start:now-40,end:now-1,net:5.43}},now),null);
assert.equal(m.shiftDate('2024-01-31','month',1),'2024-02-29');assert.equal(m.shiftDate('2024-02-29','year',1),'2025-02-28');
assert.equal(m.moneyChoice({sale_czk:null,known_sale_czk:5},'sale_czk','known_sale_czk'),5);assert.equal(m.moneyChoice({sale_czk:0,known_sale_czk:5},'sale_czk','known_sale_czk'),0);
console.log('Spot hub pure checks PASS');
const source=require('node:fs').readFileSync('managed_sources/spot_hub/hub.js','utf8');assert.ok(source.includes("document.addEventListener('hass-more-info'"),'Embedded native sensor dialogs need parent event bridge');
assert.ok(require('node:fs').readFileSync('managed_sources/spot_hub/index.html','utf8').includes('/local/jarvis-power-sun.js'),'Graph must load in the iframe realm');
assert.ok(source.includes('async mountHouse()'),'House must load independently from graph');
