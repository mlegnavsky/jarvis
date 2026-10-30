'use strict';
const card=document.querySelector('jarvis-power-sun');card.setConfig({});
const now=Date.now(),day=card.dayBounds(now),ids=card.ids(),rows={};
ids.forEach(id=>rows[id]=[]);
for(let t=day.start;t<=now;t+=60000){
 const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',hourCycle:'h23',hour:'2-digit',minute:'2-digit'}).format(t).split(':').map(Number),hour=parts[0]+parts[1]/60;
 const pv=Math.max(0,Math.sin((hour-7)/10*Math.PI))*3500*(.75+.2*Math.sin(t/270000));
 const load=420+140*Math.sin(t/1100000)+(hour>7&&hour<8?1200:0)+(hour>17&&hour<19?900:0);
 [pv,load,load-pv].forEach((v,i)=>rows[ids[i]].push({t,v:Math.round(v)}));
}
card.rows=rows;card.historyDay=day.start;card.updated=now;
card.hass={states:Object.fromEntries(ids.map(id=>[id,{state:String(rows[id].at(-1)?.v??'unavailable')}])),callApi:async()=>ids.map(id=>rows[id].map(p=>({entity_id:id,last_changed:new Date(p.t).toISOString(),state:String(p.v)})))};
