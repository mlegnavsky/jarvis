const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let Card;
vm.runInNewContext(fs.readFileSync('managed_sources/energy_weather/power-sun.js','utf8'),{HTMLElement:class{},customElements:{get:()=>false,define:(_,c)=>Card=c},Intl,Date,Math,Set,Number});

// The DOM boundary records actual render output and touch listeners; all chart,
// time selection, history and gesture calculations run in the production class.
function fixture(width){
 const card=new Card(),root={activeElement:null,nodes:new Map(),buttons:[],values:[]};
 function node(key,dataset={}){return {key,dataset,attributes:{},listeners:{},value:'',textContent:'',setAttribute(k,v){this.attributes[k]=String(v);},addEventListener(k,fn){this.listeners[k]=fn;},getBoundingClientRect(){return {left:0,top:0,width:width-12,height:240};},matches(s){return s===key||key==='.date'&&s==='input[type=date]';},focus(){root.activeElement=this;}};}
 Object.defineProperty(root,'innerHTML',{get(){return this.html;},set(html){
  this.html=html;this.nodes=new Map();this.buttons=[];this.values=[];
  for(const key of ['svg','.hit','.cursor','.solar-peak','.solar-info','.scrub','.date','.readout','.chart-bands','.chart-curves','.time-ticks','.chart-weather','.chart-range'])this.nodes.set(key,node(key));
  this.nodes.set('input[type=date]',this.nodes.get('.date'));
  for(const match of html.matchAll(/<button[^>]*data-(day|period|line|zoom)="([^"]+)"/g)){const n=node(`[data-${match[1]}=${match[2]}]`,{[match[1]]:match[2]});this.buttons.push(n);this.nodes.set(n.key,n);}
  for(const match of html.matchAll(/data-value="(\d+)"/g))this.values.push(node('[data-value]',{value:match[1]}));
 }});
 root.querySelector=s=>root.nodes.get(s.replace(/"/g,''));
 root.querySelectorAll=s=>s==='[data-value]'?root.values:root.buttons.filter(n=>s===`[data-${Object.keys(n.dataset)[0]}]`);
 card.shadowRoot=root;card.clientWidth=width;card.hiddenLines=new Set();card.rows={};card.selectedDate='2026-11-05';
 const day=card.selectedBounds();card.historyDay=day.start;card.h={states:Object.fromEntries(card.ids().map((id,i)=>[id,{state:String([274,90,7,98,9][i])}]))};
 card.ids().forEach((id,i)=>card.rows[id]=[{t:day.start,v:[0,90,7,40,3][i]},{t:day.start+12*3600000,v:[7000,500,8,99,8][i]}]);
 card.render();return card;
}
const c=fixture(358),root=c.shadowRoot,day=c.selectedBounds(),svg=()=>root.querySelector('svg');
const viewBox=root.innerHTML.match(/<svg viewBox="0 0 ([\d.]+) ([\d.]+)"/).slice(1).map(Number),plotWidth=Number(root.innerHTML.match(/class="hit"[^>]*width="([\d.]+)"/)[1]);
assert(plotWidth/viewBox[0]>=.95,'mobile curves use the available width');assert(viewBox[1]<=260,'mobile graph avoids the old tall aspect ratio');
assert(!root.innerHTML.includes('min-height:280px'),'mobile CSS must not stretch the SVG');
const axisLabels=[...root.innerHTML.matchAll(/<text class="power-axis-label" x="([\d.]+)"[^>]*text-anchor="([^"]+)"/g)];assert(axisLabels.length>=3,'power axis remains readable');assert(axisLabels.every(m=>Number(m[1])>=6&&m[2]==='start'),'mobile labels are inside the plotting area');
let selected=day.start+12*3600000;c.inspecting=true;c.hoverTime=selected;c.render();
const touch=(type,points)=>{let prevented=false;svg().listeners[type]({type,touches:points.map(([x,y])=>({clientX:x,clientY:y})),preventDefault(){prevented=true;}});return prevented;};
const original=svg();assert(touch('touchstart',[[145,80],[215,80]]));touch('touchmove',[[70,80],[290,80]]);
const zoom=c.chartBounds(day);assert(zoom.end-zoom.start<10*3600000,'two fingers magnify the time axis');assert.equal(c.hoverTime,selected,'pinching must not inspect random times');
c.render();assert.equal(svg(),original,'live redraw waits until all touches lift');assert.equal(c.chartBounds(day).start,zoom.start);
touch('touchend',[]);assert.notEqual(svg(),original);assert.equal(c.chartBounds(day).start,zoom.start);assert.equal(c.hoverTime,selected);
touch('touchstart',[[180,80]]);assert(touch('touchmove',[[225,81]]),'horizontal detail pan consumes the gesture');touch('touchend',[]);
const pan=c.chartBounds(day);assert(pan.start<zoom.start);assert.equal(pan.end-pan.start,zoom.end-zoom.start);assert.equal(c.hoverTime,selected);
root.querySelector('[data-zoom=reset]').onclick();assert.equal(c.chartBounds(day).start,day.start);assert.equal(c.chartBounds(day).end,day.end);assert(root.querySelector('[data-zoom=out]').disabled);
touch('touchstart',[[180,150]]);assert.equal(touch('touchmove',[[181,60]]),false,'one vertical finger remains available for page scrolling');touch('touchend',[]);assert.equal(c.hoverTime,selected);
root.querySelector('[data-zoom=in]').focus();root.querySelector('[data-zoom=in]').onclick();assert.equal(c.chartBounds(day).end-c.chartBounds(day).start,12*3600000);assert.equal(root.activeElement.dataset.zoom,'in');
root.querySelector('.scrub').oninput({target:{value:0}});assert.equal(c.hoverTime,day.start);assert.equal(c.chartBounds(day).start,day.start,'full-day slider can move outside the detail window');
touch('touchstart',[[145,80],[215,80]]);const canceled=svg();touch('touchcancel',[[180,80]]);assert.equal(c.chartTouchActive,false,'browser cancellation releases refresh even with another finger outside the chart');assert.notEqual(svg(),canceled);
for(const date of ['2026-03-29','2026-10-25']){const d=c.dayBounds(Date.parse(date+'T12:00Z')),ticks=c.chartTimeTicks(d,{start:d.start,end:d.end},298);assert.equal(ticks[0].label,'00:00');assert.equal(ticks.at(-1).label,'24:00');for(let i=1;i<ticks.length;i++)assert((ticks[i].t-ticks[i-1].t)/(d.end-d.start)*298>=48,'DST labels remain separated');}
const desktop=fixture(1100);assert(desktop.shadowRoot.innerHTML.includes('Kč/kWh</text>'),'desktop retains the three vertical scales');
console.log('Chart gestures: mobile SVG width/height, pinch, pan, refresh, reset, keyboard, slider, vertical scrolling and DST ticks passed');

// A horizon crossing must share the visible zero line despite asymmetric W data.
{
 const card=fixture(390),bounds=card.selectedBounds();
 card.rows[card.ids()[2]]=[{t:bounds.start,v:-9000}];
 card.altitude=t=>-60+120*(t-bounds.start)/(bounds.end-bounds.start);
 card.render();
 const html=card.shadowRoot.innerHTML,zero=Number(html.match(/class="power-axis-label"[^>]* y="([\d.]+)"[^>]*>0<\/text>/)[1])-4;
 const points=html.match(/<polyline[^>]*stroke-dasharray="6 4" points="([^"]+)"/)[1].split(' ').map(p=>p.split(',').map(Number));
 assert(Math.abs(points[144][1]-zero)<1e-6,'solar horizon must align with power zero');
 const clip=html.match(/<clipPath[^>]*><rect x="[^"]+" y="([\d.]+)"[^>]*height="([\d.]+)"/).slice(1).map(Number);
 assert(points.every(p=>p[1]>=clip[0]&&p[1]<=clip[0]+clip[1]),'solar curve stays in the chart');
 const battery=html.match(/<path d="([^"]+)"[^>]*stroke="#23a57b"/)[1];
 const batteryYs=[...battery.matchAll(/[ML][\d.]+,([\d.]+)/g)].map(m=>Number(m[1]));
 assert(Math.min(...batteryYs)>=clip[0]+6,'full battery keeps visible top headroom');
 assert(html.indexOf('class="chart-tools"')<html.indexOf('class="chart-weather"'),'forecast follows zoom tools');
 assert(html.indexOf('class="chart-weather"')<html.indexOf('<svg viewBox='),'forecast remains directly above plot');
 console.log('Solar horizon, top headroom, fitted solar bounds and forecast adjacency passed');
}
