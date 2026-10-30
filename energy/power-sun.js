/* SunCalc v1.9.0 · MIT License · Copyright (c) 2011-2015 Vladimir Agafonkin.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE. */
/*
 (c) 2011-2015, Vladimir Agafonkin
 SunCalc is a JavaScript library for calculating sun/moon position and light phases.
 https://github.com/mourner/suncalc
*/

const JarvisSolarMath = (function () { 'use strict';

// shortcuts for easier to read formulas

var PI   = Math.PI,
    sin  = Math.sin,
    cos  = Math.cos,
    tan  = Math.tan,
    asin = Math.asin,
    atan = Math.atan2,
    acos = Math.acos,
    rad  = PI / 180;

// sun calculations are based on http://aa.quae.nl/en/reken/zonpositie.html formulas


// date/time constants and conversions

var dayMs = 1000 * 60 * 60 * 24,
    J1970 = 2440588,
    J2000 = 2451545;

function toJulian(date) { return date.valueOf() / dayMs - 0.5 + J1970; }
function fromJulian(j)  { return new Date((j + 0.5 - J1970) * dayMs); }
function toDays(date)   { return toJulian(date) - J2000; }


// general calculations for position

var e = rad * 23.4397; // obliquity of the Earth

function rightAscension(l, b) { return atan(sin(l) * cos(e) - tan(b) * sin(e), cos(l)); }
function declination(l, b)    { return asin(sin(b) * cos(e) + cos(b) * sin(e) * sin(l)); }

function azimuth(H, phi, dec)  { return atan(sin(H), cos(H) * sin(phi) - tan(dec) * cos(phi)); }
function altitude(H, phi, dec) { return asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(H)); }

function siderealTime(d, lw) { return rad * (280.16 + 360.9856235 * d) - lw; }

function astroRefraction(h) {
    if (h < 0) // the following formula works for positive altitudes only.
        h = 0; // if h = -0.08901179 a div/0 would occur.

    // formula 16.4 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.
    // 1.02 / tan(h + 10.26 / (h + 5.10)) h in degrees, result in arc minutes -> converted to rad:
    return 0.0002967 / Math.tan(h + 0.00312536 / (h + 0.08901179));
}

// general sun calculations

function solarMeanAnomaly(d) { return rad * (357.5291 + 0.98560028 * d); }

function eclipticLongitude(M) {

    var C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M)), // equation of center
        P = rad * 102.9372; // perihelion of the Earth

    return M + C + P + PI;
}

function sunCoords(d) {

    var M = solarMeanAnomaly(d),
        L = eclipticLongitude(M);

    return {
        dec: declination(L, 0),
        ra: rightAscension(L, 0)
    };
}


var SunCalc = {};


// calculates sun position for a given date and latitude/longitude

SunCalc.getPosition = function (date, lat, lng) {

    var lw  = rad * -lng,
        phi = rad * lat,
        d   = toDays(date),

        c  = sunCoords(d),
        H  = siderealTime(d, lw) - c.ra;

    return {
        azimuth: azimuth(H, phi, c.dec),
        altitude: altitude(H, phi, c.dec)
    };
};


// sun times configuration (angle, morning name, evening name)

var times = SunCalc.times = [
    [-0.833, 'sunrise',       'sunset'      ],
    [  -0.3, 'sunriseEnd',    'sunsetStart' ],
    [    -6, 'dawn',          'dusk'        ],
    [   -12, 'nauticalDawn',  'nauticalDusk'],
    [   -18, 'nightEnd',      'night'       ],
    [     6, 'goldenHourEnd', 'goldenHour'  ]
];

// adds a custom time to the times config

SunCalc.addTime = function (angle, riseName, setName) {
    times.push([angle, riseName, setName]);
};


// calculations for sun times

var J0 = 0.0009;

function julianCycle(d, lw) { return Math.round(d - J0 - lw / (2 * PI)); }

function approxTransit(Ht, lw, n) { return J0 + (Ht + lw) / (2 * PI) + n; }
function solarTransitJ(ds, M, L)  { return J2000 + ds + 0.0053 * sin(M) - 0.0069 * sin(2 * L); }

function hourAngle(h, phi, d) { return acos((sin(h) - sin(phi) * sin(d)) / (cos(phi) * cos(d))); }
function observerAngle(height) { return -2.076 * Math.sqrt(height) / 60; }

// returns set time for the given sun altitude
function getSetJ(h, lw, phi, dec, n, M, L) {

    var w = hourAngle(h, phi, dec),
        a = approxTransit(w, lw, n);
    return solarTransitJ(a, M, L);
}


// calculates sun times for a given date, latitude/longitude, and, optionally,
// the observer height (in meters) relative to the horizon

SunCalc.getTimes = function (date, lat, lng, height) {

    height = height || 0;

    var lw = rad * -lng,
        phi = rad * lat,

        dh = observerAngle(height),

        d = toDays(date),
        n = julianCycle(d, lw),
        ds = approxTransit(0, lw, n),

        M = solarMeanAnomaly(ds),
        L = eclipticLongitude(M),
        dec = declination(L, 0),

        Jnoon = solarTransitJ(ds, M, L),

        i, len, time, h0, Jset, Jrise;


    var result = {
        solarNoon: fromJulian(Jnoon),
        nadir: fromJulian(Jnoon - 0.5)
    };

    for (i = 0, len = times.length; i < len; i += 1) {
        time = times[i];
        h0 = (time[0] + dh) * rad;

        Jset = getSetJ(h0, lw, phi, dec, n, M, L);
        Jrise = Jnoon - (Jset - Jnoon);

        result[time[1]] = fromJulian(Jrise);
        result[time[2]] = fromJulian(Jset);
    }

    return result;
};


// moon calculations, based on http://aa.quae.nl/en/reken/hemelpositie.html formulas

function moonCoords(d) { // geocentric ecliptic coordinates of the moon

    var L = rad * (218.316 + 13.176396 * d), // ecliptic longitude
        M = rad * (134.963 + 13.064993 * d), // mean anomaly
        F = rad * (93.272 + 13.229350 * d),  // mean distance

        l  = L + rad * 6.289 * sin(M), // longitude
        b  = rad * 5.128 * sin(F),     // latitude
        dt = 385001 - 20905 * cos(M);  // distance to the moon in km

    return {
        ra: rightAscension(l, b),
        dec: declination(l, b),
        dist: dt
    };
}

SunCalc.getMoonPosition = function (date, lat, lng) {

    var lw  = rad * -lng,
        phi = rad * lat,
        d   = toDays(date),

        c = moonCoords(d),
        H = siderealTime(d, lw) - c.ra,
        h = altitude(H, phi, c.dec),
        // formula 14.1 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.
        pa = atan(sin(H), tan(phi) * cos(c.dec) - sin(c.dec) * cos(H));

    h = h + astroRefraction(h); // altitude correction for refraction

    return {
        azimuth: azimuth(H, phi, c.dec),
        altitude: h,
        distance: c.dist,
        parallacticAngle: pa
    };
};


// calculations for illumination parameters of the moon,
// based on http://idlastro.gsfc.nasa.gov/ftp/pro/astro/mphase.pro formulas and
// Chapter 48 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.

SunCalc.getMoonIllumination = function (date) {

    var d = toDays(date || new Date()),
        s = sunCoords(d),
        m = moonCoords(d),

        sdist = 149598000, // distance from Earth to Sun in km

        phi = acos(sin(s.dec) * sin(m.dec) + cos(s.dec) * cos(m.dec) * cos(s.ra - m.ra)),
        inc = atan(sdist * sin(phi), m.dist - sdist * cos(phi)),
        angle = atan(cos(s.dec) * sin(s.ra - m.ra), sin(s.dec) * cos(m.dec) -
                cos(s.dec) * sin(m.dec) * cos(s.ra - m.ra));

    return {
        fraction: (1 + cos(inc)) / 2,
        phase: 0.5 + 0.5 * inc * (angle < 0 ? -1 : 1) / Math.PI,
        angle: angle
    };
};


function hoursLater(date, h) {
    return new Date(date.valueOf() + h * dayMs / 24);
}

// calculations for moon rise/set times are based on http://www.stargazing.net/kepler/moonrise.html article

SunCalc.getMoonTimes = function (date, lat, lng, inUTC) {
    var t = new Date(date);
    if (inUTC) t.setUTCHours(0, 0, 0, 0);
    else t.setHours(0, 0, 0, 0);

    var hc = 0.133 * rad,
        h0 = SunCalc.getMoonPosition(t, lat, lng).altitude - hc,
        h1, h2, rise, set, a, b, xe, ye, d, roots, x1, x2, dx;

    // go in 2-hour chunks, each time seeing if a 3-point quadratic curve crosses zero (which means rise or set)
    for (var i = 1; i <= 24; i += 2) {
        h1 = SunCalc.getMoonPosition(hoursLater(t, i), lat, lng).altitude - hc;
        h2 = SunCalc.getMoonPosition(hoursLater(t, i + 1), lat, lng).altitude - hc;

        a = (h0 + h2) / 2 - h1;
        b = (h2 - h0) / 2;
        xe = -b / (2 * a);
        ye = (a * xe + b) * xe + h1;
        d = b * b - 4 * a * h1;
        roots = 0;

        if (d >= 0) {
            dx = Math.sqrt(d) / (Math.abs(a) * 2);
            x1 = xe - dx;
            x2 = xe + dx;
            if (Math.abs(x1) <= 1) roots++;
            if (Math.abs(x2) <= 1) roots++;
            if (x1 < -1) x1 = x2;
        }

        if (roots === 1) {
            if (h0 < 0) rise = i + x1;
            else set = i + x1;

        } else if (roots === 2) {
            rise = i + (ye < 0 ? x2 : x1);
            set = i + (ye < 0 ? x1 : x2);
        }

        if (rise && set) break;

        h0 = h2;
    }

    var result = {};

    if (rise) result.rise = hoursLater(t, rise);
    if (set) result.set = hoursLater(t, set);

    if (!rise && !set) result[ye > 0 ? 'alwaysUp' : 'alwaysDown'] = true;

    return result;
};


return SunCalc;
}());

class JarvisPowerSun extends HTMLElement {
 setConfig(c){this.cfg=c;if(!this.shadowRoot)this.attachShadow({mode:'open'});this.hiddenLines??=new Set();this.rows??={};}
 set hass(h){this.h=h;if(!this.loading&&(!this.updated||Date.now()-this.updated>120000))this.fetchHistory();else this.render();}
 connectedCallback(){this.clock=setInterval(()=>{if(this.h)this.fetchHistory()},120000);this.resize=new ResizeObserver(()=>this.render());this.resize.observe(this);}
 disconnectedCallback(){clearInterval(this.clock);this.resize?.disconnect();}
 getCardSize(){return 7;}
 ids(){return ['sensor.inverter_pv_power','sensor.inverter_load_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.jarvis_spot_ote'];}
 dateKey(t=Date.now()){return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(t);}
 selectedBounds(now=Date.now()){return this.dayBounds(this.selectedDate?Date.parse(this.selectedDate+'T12:00:00Z'):now);}
 async chooseDay(date){if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date+'T12:00:00Z')))return;this.selectedDate=date;this.hoverTime=null;this.rows={};this.historyDay=null;this.updated=null;this.error=null;this.render();await this.fetchHistory();}
 shiftDay(delta){const d=new Date((this.selectedDate||this.dateKey())+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);return d.toISOString().slice(0,10);}
 value(v){if(v===null||v===undefined||String(v).trim()==='')return null;const n=Number(v);return Number.isFinite(n)?n:null;}
 dayBounds(now=Date.now()){
  const f=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  const parts=t=>Object.fromEntries(f.formatToParts(t).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
  const p=parts(now),midnight=Date.UTC(p.year,p.month-1,p.day);
  const resolve=target=>{let t=target;for(let i=0;i<4;i++){const q=parts(t);const displayed=Date.UTC(q.year,q.month-1,q.day,q.hour,q.minute,q.second);t+=target-displayed;}return t;};
  return {start:resolve(midnight),end:resolve(midnight+86400000),label:`${p.day}. ${p.month}. ${p.year}`};
 }
 async fetchHistory(){if(!this.h)return;const request=(this.historyRequest||0)+1;this.historyRequest=request;this.loading=true;
  const day=this.selectedBounds(),now=Date.now();
  try{
   const data=day.start>now?[]:await this.h.callApi('GET',`history/period/${new Date(day.start).toISOString()}?end_time=${encodeURIComponent(new Date(Math.min(day.end,now)).toISOString())}&filter_entity_id=${this.ids().join(',')}&minimal_response&no_attributes`);
   if(request!==this.historyRequest)return;
   const rows={};for(const series of data){const id=series[0]?.entity_id;if(!this.ids().includes(id))continue;rows[id]=series.map(p=>({t:Date.parse(p.last_changed||p.last_updated),v:this.value(p.state)})).filter(p=>Number.isFinite(p.t)).sort((a,b)=>a.t-b.t);}
   this.rows=rows;this.historyDay=day.start;this.error=null;this.updated=Date.now();
  }catch(e){if(request===this.historyRequest)this.error='Historii vybraného dne se nepodařilo načíst. Zkusím to znovu.';}finally{if(request===this.historyRequest){this.loading=false;this.render();}}}
 priceAt(t,points,now){
  const rows=this.h?.states['sensor.jarvis_spot_ote']?.attributes?.rows||[];
  const interval=rows.find(r=>{const a=Date.parse(r.time);return a<=t&&t<a+900000;});
  if(interval)return this.value(interval.price);
  return this.reading(points,t,now);
 }
 priceSegments(start,end,points,now){
  const boundaries=new Set([start,end]);if(now>start&&now<end)boundaries.add(now);
  for(const p of points)if(p.t>start&&p.t<end)boundaries.add(p.t);
  for(const r of this.h?.states['sensor.jarvis_spot_ote']?.attributes?.rows||[]){const a=Date.parse(r.time);for(const t of [a,a+900000])if(t>start&&t<end)boundaries.add(t);}
  const ts=[...boundaries].sort((a,b)=>a-b);return ts.slice(1).map((b,i)=>({start:ts[i],end:b,v:this.priceAt((ts[i]+b)/2,points,now)}));
 }
 n(v){return Number.isFinite(v)?v.toLocaleString('cs-CZ',{maximumFractionDigits:1}):'—';}
 time(t){return new Date(t).toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Prague'});}
 altitude(t){return JarvisSolarMath.getPosition(new Date(t),50.555,14.156).altitude*180/Math.PI;}
 selectionTime(t,now){return t===now?now:Math.min(Math.round(t/60000)*60000,t<now?now:Infinity);}
 reading(points,t,now){if(t>now)return null;let result=null;for(const p of points){if(p.t>t)break;result=p.v;}return result;}
 render(){if(!this.shadowRoot||!this.h)return;
  const active=this.shadowRoot.activeElement,focus=active?.matches('.scrub')?'.scrub':active?.matches('.date')?'.date':active?.dataset.day?`[data-day="${active.dataset.day}"]`:active?.dataset.line!==undefined?`[data-line="${Number(active.dataset.line)}"]`:null;
  const now=Date.now(),day=this.selectedBounds(now),start=day.start,end=day.end,span=end-start;
  const w=Math.max(300,this.clientWidth-8),h=340,l=52,r=112,top=24,bottom=36,pw=w-l-r,ph=h-top-bottom;
  const colors=['#4667d5','#e3aa32','#f06d58','#23a57b','#b05bd3','#b88500'],names=['Výroba soláru','Spotřeba domu','Síť + / −','Stav baterie','Spotová cena','Výška Slunce'],units=['W','W','W','%','Kč/kWh','°'];
  const series=this.ids().map(id=>{
   const all=this.historyDay===start?(this.rows[id]||[]):[];const p=all.filter(p=>p.t>=start&&p.t<=Math.min(end,now)).map(p=>({...p}));
   const before=all.filter(p=>p.t<start).at(-1);if(before)p.unshift({t:start,v:before.v});
   // A current unavailable state must terminate a curve rather than invent a zero.
   if(now>=start&&now<end)p.push({t:now,v:this.value(this.h.states[id]?.state)});else if(end<=now&&p.length)p.push({t:end,v:p.at(-1).v});return p;
  });
  const vals=series.slice(0,3).flatMap((ps,i)=>this.hiddenLines.has(i)?[]:ps.filter(p=>p.v!==null).map(p=>p.v));
  const rawLo=vals.reduce((a,b)=>Math.min(a,b),-100),rawHi=vals.reduce((a,b)=>Math.max(a,b),1000),step=Math.max(200,Math.ceil((rawHi-rawLo)/5/500)*500),lo=Math.floor(rawLo/step)*step,hi=Math.ceil(rawHi/step)*step;
  const forecast=(this.h.states['sensor.jarvis_spot_ote']?.attributes?.rows||[]).map(r=>({t:Date.parse(r.time),v:this.value(r.price)})).filter(p=>p.t>=start&&p.t<end);
  const priceSegments=this.priceSegments(start,end,series[4],now);const priceValues=priceSegments.filter(p=>p.v!==null).map(p=>p.v);const priceLo=Math.min(0,...priceValues),priceHi=Math.max(1,...priceValues);
  const x=t=>l+(t-start)/span*pw,y=v=>top+(hi-v)/(hi-lo)*ph,sy=v=>top+(90-v)/180*ph,by=v=>top+(100-v)/100*ph,py=v=>top+(priceHi-v)/(priceHi-priceLo)*ph;
  const sun=[];for(let t=start;t<end;t+=300000)sun.push({t,v:this.altitude(t)});sun.push({t:end,v:this.altitude(end)});
  const bands=sun.slice(1).map((p,i)=>{const a=(p.v+sun[i].v)/2,c=a>=0?'#fff7da':a>=-6?'#deebf5':a>=-12?'#bed0e0':a>=-18?'#a2b6cb':'#8796aa';return `<rect x="${x(sun[i].t)}" y="${top}" width="${x(p.t)-x(sun[i].t)+.2}" height="${ph}" fill="${c}" opacity=".48"/>`;}).join('');
  const grid=Array.from({length:Math.round((hi-lo)/step)+1},(_,i)=>{const v=lo+step*i;return `<line x1="${l}" x2="${w-r}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".14"/><text x="${l-7}" y="${y(v)+4}" text-anchor="end">${this.n(v)}</text>`;}).join('');
  const curves=series.slice(0,4).map((ps,i)=>{if(this.hiddenLines.has(i))return '';const scale=i===3?by:y;let d='',open=false;for(const p of ps){if(p.v===null){open=false;continue;}d+=`${open?'L':'M'}${x(p.t)},${scale(p.v)} `;open=true;}return `<path d="${d}" fill="none" stroke="${colors[i]}" stroke-width="2" vector-effect="non-scaling-stroke"/>`;}).join('');
  let priceCurve='';if(!this.hiddenLines.has(4)){let previous=null;priceCurve=priceSegments.map(p=>{if(p.v===null){previous=null;return '';}const vertical=previous&&previous.end===p.start?`<line x1="${x(p.start)}" x2="${x(p.start)}" y1="${py(previous.v)}" y2="${py(p.v)}" stroke="${colors[4]}" stroke-width="2"/>`:'';previous=p;return vertical+`<line x1="${x(p.start)}" x2="${x(p.end)}" y1="${py(p.v)}" y2="${py(p.v)}" stroke="${colors[4]}" stroke-width="2"/>`;}).join('');}
  const ticks=Array.from({length:7},(_,i)=>{const hour=i*4; // Clock labels, including explicit 24:00, stay in Prague time.
   let t=start;if(hour===24)t=end;else if(hour){t=start+hour*3600000;for(let j=0;j<3;j++){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',hourCycle:'h23',hour:'2-digit',minute:'2-digit'}).format(new Date(t)).split(':').map(Number);t+=(hour-parts[0]-parts[1]/60)*3600000;}}
   return `<text x="${x(t)}" y="${h-9}" text-anchor="${i===0?'start':i===6?'end':'middle'}">${String(hour).padStart(2,'0')}:00</text>`;}).join('');
  const legend=names.map((name,i)=>`<button data-line="${i}" aria-pressed="${!this.hiddenLines.has(i)}" class="${this.hiddenLines.has(i)?'muted':''}"><span class="dot" style="background:${colors[i]}"></span>${name} <b data-value="${i}"></b></button>`).join('');
  const svg=`<svg viewBox="0 0 ${w} ${h}" aria-label="Denní výkon od 00:00 do 24:00"><g font-size="11" fill="currentColor">${bands}${grid}<text x="${l}" y="15">W</text><text x="${w-r+6}" y="15" fill="${colors[3]}">%</text><text x="${w-r+40}" y="15" fill="${colors[4]}">Kč/kWh</text><text x="${w-10}" y="15" text-anchor="end" fill="${colors[5]}">°</text>${[0,25,50,75,100].map(v=>`<text x="${w-r+6}" y="${by(v)+4}" fill="${colors[3]}">${v}</text><text x="${w-r+40}" y="${by(v)+4}" fill="${colors[4]}">${this.n(priceLo+(priceHi-priceLo)*v/100)}</text><text x="${w-10}" y="${by(v)+4}" text-anchor="end" fill="${colors[5]}">${-90+v*1.8}</text>`).join('')}${curves}${priceCurve}${this.hiddenLines.has(5)?'':`<polyline fill="none" stroke="${colors[5]}" stroke-width="2" stroke-dasharray="6 4" points="${sun.map(p=>`${x(p.t)},${sy(p.v)}`).join(' ')}"/>`}${now>=start&&now<end?`<line x1="${x(now)}" x2="${x(now)}" y1="${top}" y2="${h-bottom}" stroke="currentColor" stroke-dasharray="3 4" opacity=".4"/>`:""}${ticks}<line class="cursor" y1="${top}" y2="${h-bottom}" stroke="var(--primary-text-color,#172c42)" stroke-width="1" visibility="hidden"/><rect class="hit" x="${l}" y="${top}" width="${pw}" height="${ph}" fill="transparent"/></g></svg>`;
  this.shadowRoot.innerHTML=`<style>:host{display:block;min-width:0}*{box-sizing:border-box}ha-card{display:block;padding:16px 12px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#172c42);font:14px system-ui;border-radius:18px}header{display:flex;align-items:center;justify-content:space-between;gap:10px}h2{font-size:21px;margin:0 0 5px}.subtitle{font-size:12px;color:var(--secondary-text-color,#63758a)}.days{display:flex;gap:8px;align-items:center;margin-top:12px}.date{font:inherit;color:inherit;background:transparent;border:1px solid #8796aa55;padding:8px;border-radius:8px;min-width:0}.legend{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 8px}button{font:inherit;font-size:12px;border:1px solid #8796aa55;border-radius:10px;padding:9px;background:transparent;color:inherit;cursor:pointer;text-align:left}button[aria-pressed=true]{background:#8796aa12}.muted{opacity:.45}button:focus-visible,.scrub:focus-visible{outline:2px solid #4667d5;outline-offset:3px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}b[data-value]{display:inline-block;min-width:62px}svg{display:block;width:100%;overflow:visible}.hit{cursor:crosshair;touch-action:pan-y}.readout{font-weight:600;min-height:22px;padding:5px 0}.hint,details{font-size:12px;color:var(--secondary-text-color,#63758a);line-height:1.6}.error{color:#bd2435}.scrub{width:100%;accent-color:#4667d5;margin:6px 0}@media(max-width:500px){ha-card{padding:12px 6px}h2{font-size:19px}.legend{display:grid;grid-template-columns:1fr 1fr;gap:5px}button{font-size:11px;padding:8px 5px}b[data-value]{display:block;margin:4px 0 0 15px}svg{min-height:280px}}</style><ha-card><header><div><h2>Výkon během dne</h2><span class="subtitle">${day.label} · 00:00–24:00 · Žitenice</span></div></header><nav class="days" aria-label="Výběr dne"><button data-day="prev" aria-label="Předchozí den">‹</button><input class="date" type="date" aria-label="Den grafu" value="${this.selectedDate||this.dateKey(now)}"><button data-day="next" aria-label="Následující den">›</button><button data-day="today">Dnes</button></nav><div class="legend" aria-label="Zobrazované křivky">${legend}</div><div class="readout" aria-live="off"></div>${this.error?`<p class="error">${this.error}</p>`:''}${svg}<input class="scrub" type="range" min="0" max="${span/60000}" step="1" aria-label="Čas v grafu"><div class="hint">Přejeď myší, klepni do grafu nebo posuň čas jezdcem. Síť: + odběr, − dodávka.</div><details><summary>Jak číst graf</summary>Výkony jsou ve W. Baterie je v procentech, cena v Kč/kWh bez DPH před poplatky obchodníka a Slunce ve stupních; každá veličina má vlastní barevnou stupnici vpravo. Šedá znamená noc, modrá soumrak, světlá den. Budoucí naměřené hodnoty ani výpadky nejsou doplňovány nulou. Křivka Slunce je astronomický výpočet.</details><div class="hint">${this.loading?"Načítám historii… ":""}${day.start>now?"Budoucí den: naměřené výkony a baterie zatím nejsou dostupné. ":""}${!forecast.length&&day.start>now?"Spotové ceny pro tento den zatím nejsou zveřejněné.":""} Historie je dostupná podle uchovávání dat v Home Assistantu.</div></ha-card>`;
  const update=t=>{t=Math.max(start,Math.min(end,this.selectionTime(t,now)));this.hoverTime=t;const future=t>now;this.shadowRoot.querySelector('.readout').textContent=`${t===end?'24:00':this.time(t)}${future?' · zatím bez měření':''}`;
   this.shadowRoot.querySelectorAll('[data-value]').forEach(el=>{const i=Number(el.dataset.value),v=i===5?this.altitude(t):i===4?this.priceAt(t,series[4],now):this.reading(series[i],t,now);el.textContent=this.hiddenLines.has(i)?'skryto':`${this.n(v)} ${units[i]}`;});
   const line=this.shadowRoot.querySelector('.cursor');line.setAttribute('x1',x(t));line.setAttribute('x2',x(t));line.setAttribute('visibility','visible');this.shadowRoot.querySelector('.scrub').value=(t-start)/60000;
  };
  this.shadowRoot.querySelector('[data-day=prev]').onclick=()=>this.chooseDay(this.shiftDay(-1));
  this.shadowRoot.querySelector('[data-day=next]').onclick=()=>this.chooseDay(this.shiftDay(1));
  this.shadowRoot.querySelector('[data-day=today]').onclick=()=>this.chooseDay(this.dateKey());
  this.shadowRoot.querySelector('.date').onchange=e=>this.chooseDay(e.target.value);
  this.shadowRoot.querySelectorAll('[data-line]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.line);this.hiddenLines.has(i)?this.hiddenLines.delete(i):this.hiddenLines.add(i);this.render();});
  this.shadowRoot.querySelector('.hit').onpointermove=e=>{const rect=this.shadowRoot.querySelector('svg').getBoundingClientRect();const px=(e.clientX-rect.left)/rect.width*w;update(start+(px-l)/pw*span);};
  this.shadowRoot.querySelector('.hit').onpointerdown=e=>{const rect=this.shadowRoot.querySelector('svg').getBoundingClientRect();update(start+((e.clientX-rect.left)/rect.width*w-l)/pw*span);};
  this.shadowRoot.querySelector('.scrub').oninput=e=>update(start+Number(e.target.value)*60000);
  update(this.hoverTime>=start&&this.hoverTime<=end?this.hoverTime:now>=start&&now<end?now:start);
  if(focus)this.shadowRoot.querySelector(focus)?.focus({preventScroll:true});
 }
}
if(!customElements.get('jarvis-power-sun'))customElements.define('jarvis-power-sun',JarvisPowerSun);
