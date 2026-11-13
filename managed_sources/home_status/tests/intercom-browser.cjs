const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.setContent('<html lang="cs"><body style="background:#dce4eb;font:16px system-ui"><h2>Domácnost</h2><div id="floorplan" style="height:460px;background:#183348;border-radius:22px;padding:24px;color:white">Obývák</div></body></html>');
  await page.evaluate(()=>{
   window.uploads=[];window.calls=[];window.requests=0;
   Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{window.requests++;window.audioSource=new AudioContext();const oscillator=audioSource.createOscillator(),out=audioSource.createMediaStreamDestination();oscillator.connect(out);oscillator.start();return out.stream;}}});
  });
  await page.addScriptTag({path:__dirname+'/../intercom.js'});
  await page.evaluate(()=>{
   const c=document.createElement('jarvis-home-intercom');c.setConfig({entity:'media_player.homepod'});
   c.hass={states:{'media_player.homepod':{state:'off'}},fetchWithAuth:async(url,opts)=>{const f=opts.body.get('file');window.uploads.push({url,size:f.size,type:f.type,name:f.name});return {ok:true,json:async()=>({media_content_id:'media-source://media_source/local/jarvis_intercom/browser.wav'})};},callService:async(...args)=>calls.push(args),callWS:async()=>{}};
   document.getElementById('floorplan').append(c);
  });
  const url=page.url();await page.locator('#record').click();await page.waitForFunction(()=>document.querySelector('jarvis-home-intercom').phase==='recording');
  assert.equal(await page.evaluate(()=>requests),1);assert.equal(page.url(),url,'recording must stay on floorplan');
  await page.waitForTimeout(500);await page.screenshot({path:process.env.INTERCOM_SCREENSHOT||'/tmp/jarvis-intercom-mobile.png'});
  await page.locator('#stop').click();await page.waitForFunction(()=>document.querySelector('jarvis-home-intercom').phase==='done');
  const result=await page.evaluate(()=>({uploads,calls}));assert.equal(result.uploads.length,1);assert.ok(result.uploads[0].size>1000);assert.equal(result.uploads[0].type,'audio/wav');assert.equal(result.calls[0][1],'play_media');
  await page.locator('#cancel').click();await page.locator('#record').click();await page.waitForFunction(()=>document.querySelector('jarvis-home-intercom').phase==='recording');await page.locator('#cancel').click();assert.equal(await page.evaluate(()=>uploads.length),1);
  console.log('Mobile Chromium: single tap records actual audio, remains on floorplan, stop uploads WAV and plays, cancel does not send');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
