const vm=require('node:vm'),cp=require('node:child_process'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const code=cp.execFileSync('python',['-c','import sys;sys.path.insert(0,sys.argv[1]);from prepare_intercom import status_module;print(status_module())',root],{encoding:'utf8'});
const registered=new Map();
vm.runInNewContext(code,{HTMLElement:class{},customElements:{get:n=>registered.get(n),define:(n,c)=>registered.set(n,c)}});
for(const name of ['jarvis-device-status','jarvis-home-intercom','jarvis-room-panel'])assert.ok(registered.has(name),name+' available without old cached home-message module');
console.log('Floorplan bundle registers room, device and intercom elements independently');
