const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH});try{
const page=await browser.newPage({viewport:{width:1100,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.setContent('<style>body{margin:0}jarvis-power-sun{display:block;width:100%}</style><jarvis-power-sun></jarvis-power-sun>');
await page.addScriptTag({content:fs.readFileSync('managed_sources/energy_weather/power-sun.js','utf8')});
await page.evaluate(()=>{const card=document.querySelector('jarvis-power-sun');card.setConfig({});card.selectedDate='2026-11-16';const day=card.selectedBounds(),rows=Array.from({length:24},(_,i)=>({time:new Date(day.start+(i+1)*3600000).toISOString(),global_tilted_irradiance:i>=8&&i<=14?300:0,shortwave_radiation:i>=8&&i<=14?200:0,temperature_2m:7,cloud_cover:98,weather_code:3}));card.h={states:{'sensor.jarvis_pocasi_zitenice':{state:'ready',attributes:{fetched_at:new Date().toISOString(),rows}}}};card.render(true);});
const card=page.locator('jarvis-power-sun');await card.locator('.pv-forecast').waitFor();
if(!await card.locator('.solar-forecast').innerText().then(t=>t.includes('kWh')&&t.includes('W/m²')))throw Error('Forecast summary missing units');
if(await card.locator('svg').getAttribute('viewBox').then(v=>v.includes('NaN')))throw Error('Invalid chart geometry');
await page.setViewportSize({width:390,height:900});await page.evaluate(()=>document.querySelector('jarvis-power-sun').render(true));
if(!await card.locator('.pv-forecast').isVisible())throw Error('Mobile forecast missing');
if(errors.length)throw Error(errors.join('\n'));
console.log('Desktop/mobile future-day forecast renders without prices or measurements PASS');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
