'use strict';
const card=document.querySelector('jarvis-power-sun');card.setConfig({});
const now=Date.now(),day=card.dayBounds(now),ids=card.ids();
function samples(start,end){const rows=Object.fromEntries(ids.map(id=>[id,[]]));for(let t=start;t<=Math.min(end,Date.now());t+=60000){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',hourCycle:'h23',hour:'2-digit',minute:'2-digit'}).format(t).split(':').map(Number),hour=parts[0]+parts[1]/60;const pv=Math.max(0,Math.sin((hour-7)/10*Math.PI))*3500*(.75+.2*Math.sin(t/270000)),load=420+140*Math.sin(t/1100000)+(hour>7&&hour<8?1200:0)+(hour>17&&hour<19?900:0);[pv,load,load-pv,Math.max(10,Math.min(100,40+hour*2)),3+Math.sin(hour/4)*2].forEach((v,i)=>rows[ids[i]].push({t,v:Math.round(v*100)/100}));}return rows;}
const rows=samples(day.start,now),prices=[];for(let t=day.start;t<day.end+86400000;t+=900000)prices.push({time:new Date(t).toISOString(),price:3+2*Math.sin(t/6000000)});
const weather=[];for(let t=day.start;t<day.end+6*86400000;t+=3600000)weather.push({time:new Date(t).toISOString(),weather_code:[0,1,3,61,3,2][Math.floor(t/10800000)%6],temperature_2m:8+5*Math.sin(t/17000000)});
card.rows=rows;card.historyDay=day.start;card.updated=now;
card.hass={states:{...Object.fromEntries(ids.map(id=>[id,{state:String(rows[id].at(-1)?.v??'unavailable'),attributes:id==='sensor.jarvis_spot_ote'?{rows:prices}:{}}])),'sensor.jarvis_pocasi_zitenice':{state:'ready',attributes:{rows:weather}}},callApi:async(_method,url)=>{const start=Date.parse(url.split('history/period/')[1].split('?')[0]);const end=Date.parse(new URL('http://demo/'+url).searchParams.get('end_time'));const data=samples(start,end);return ids.map(id=>data[id].map(p=>({entity_id:id,last_changed:new Date(p.t).toISOString(),state:String(p.v)})));}};

const energyIds=card.energyIds(),todayIds=card.todayIds();
energyIds.forEach((id,i)=>card.h.states[id]={state:String(1000+i*100),attributes:{unit_of_measurement:'kWh'}});
todayIds.forEach((id,i)=>card.h.states[id]={state:String([14,8,1.5,0][i]),attributes:{unit_of_measurement:'kWh'}});
card.h.callWS=async query=>{const start=Date.parse(query.start_time),end=Date.parse(query.end_time),result=Object.fromEntries(energyIds.map(id=>[id,[]]));for(let t=start;t<end;t+=query.period==='hour'?3600000:86400000)energyIds.forEach((id,i)=>result[id].push({start:t,end:t+(query.period==='hour'?3600000:86400000),change:[12,8,2,0][i]*(query.period==='hour'?1/24:1)}));return result;};
card.statsKey=null;card.fetchStats();
