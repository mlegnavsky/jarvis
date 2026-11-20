// Browser acceptance against explicit synthetic ledger fixtures, never live revenue.
const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1200,height:900}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const root='managed_sources/',files={'jarvis-spot-hub.html':'spot_hub/index.html','jarvis-spot-hub.js':'spot_hub/hub.js','jarvis-accounting.js':'spot_hub/accounting.js','jarvis-spot-hub.css':'spot_hub/hub.css','jarvis-power-sun.js':'energy_weather/power-sun.js','jarvis-sale-messages.js':'spot_hub/messages.js'};
 await page.route('http://accounting.test/**',async route=>{
  const name=new URL(route.request().url()).pathname.split('/').pop();
  if(name==='jarvis-spot-hub-config.json')return route.fulfill({json:{house:{image:'',elements:[]},advanced:[]}});
  const path=root+files[name];if(!files[name]||!fs.existsSync(path))return route.fulfill({status:404,body:''});
  return route.fulfill({body:fs.readFileSync(path),contentType:name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'application/javascript'});
 });
 await page.addInitScript(()=>{
  const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(Date.now());
  const d=new Date(day+'T12:00Z');d.setUTCDate(d.getUTCDate()-1);const yesterday=d.toISOString().slice(0,10);
  const state=(value,attributes={})=>({state:String(value),attributes,last_updated:new Date().toISOString()});
  window.__JARVIS_HASS__={user:{id:'synthetic-test'},states:{'sensor.jarvis_energy_sales':state('idle',{settings:{},healthy:true}),'sensor.jarvis_energy_archive':state('ready',{server:{finance:{schema:2,days:[{date:yesterday,export_kwh:6.2,import_kwh:.23,priced_export_kwh:6.2,known_sale_czk:21.7,known_purchase_czk:1.15,quality:'estimate'}]}}})},callService:()=>{throw Error('Passive page must not write to devices')},callWS:async()=>({}),callApi:async()=>[]};
 });
 try{
  await page.goto('http://accounting.test/local/jarvis-spot-hub.html');
  await page.locator('#previous').click();
  await page.waitForFunction(()=>document.querySelector('#export-energy').textContent==='6,20 kWh');
  assert.equal(await page.locator('#sale-money').textContent(),'21,70 Kč');
  for(const period of ['week','month','year']){
   const begin=Date.now();await page.locator(`.trading-head [data-period="${period}"]`).click();
   await page.waitForFunction(p=>document.querySelector('#finance-plot').textContent.includes({week:'týden',month:'měsíc',year:'rok'}[p]),period);
   assert.ok(Date.now()-begin<2000,'Archive period totals must not wait for recorder history');
   await page.locator('jarvis-power-sun').locator('svg[aria-label="Energetická bilance v kWh"]').waitFor();
  }
  await page.setViewportSize({width:390,height:844});await page.locator('.trading-head [data-period="month"]').click();
  assert.ok(await page.locator('#finance-plot svg').isVisible());assert.deepEqual(errors,[]);
  console.log('Browser: yesterday meter-matched revenue, week/month/year money and energy charts, mobile layout, no device writes PASS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
