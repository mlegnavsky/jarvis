const {chromium}=require('playwright');
const fs=require('fs'),os=require('os'),path=require('path');
(async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'jarvis-chart-'));
 for(const name of ['index.html','demo.js'])fs.copyFileSync(`testing/lab-public/energy/${name}`,path.join(root,name));
 fs.copyFileSync('managed_sources/energy_weather/power-sun.js',path.join(root,'power-sun.js'));
 const b=await chromium.launch({headless:true}),p=await b.newPage({viewport:{width:1100,height:800}}),errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 try{
  await p.goto('file://'+path.join(root,'index.html'));const c=p.locator('jarvis-power-sun');await c.locator('.scrub').waitFor();
  await c.locator('[data-line="0"]').click();if(await c.locator('[data-line="0"]').getAttribute('aria-pressed')!=='false')throw Error('toggle');
  await c.locator('[data-line="0"]').click();const hit=await c.locator('.hit').boundingBox();await p.mouse.move(hit.x+hit.width*.5,hit.y+50);
  if(!(await c.locator('.readout').textContent()).includes('12:00'))throw Error('midday hover: '+await c.locator('.readout').textContent());
  const slider=c.locator('.scrub');await slider.evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}));});
  if(!(await c.locator('.readout').textContent()).includes('24:00'))throw Error('end time');
  if(!(await c.locator('[data-value="0"]').textContent()).includes('—'))throw Error('future reading');
  await slider.focus();await p.evaluate(()=>{const c=document.querySelector('jarvis-power-sun');c.hass=c.h;});
  if(!await slider.evaluate(e=>e===e.getRootNode().activeElement))throw Error('slider focus after HA update');
  await c.locator('[data-line="1"]').focus();await p.keyboard.press('Enter');
  if(!await c.locator('[data-line="1"]').evaluate(e=>e===e.getRootNode().activeElement))throw Error('toggle focus');
  await p.setViewportSize({width:390,height:844});
  if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('mobile overflow');
  if(errors.length)throw Error(errors.join('\n'));console.log('Browser passed: hover, toggle, future, keyboard focus, mobile');
 }finally{await b.close();fs.rmSync(root,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
