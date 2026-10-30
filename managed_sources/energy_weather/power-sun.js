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
 setConfig(c){this.cfg=c;if(!this.shadowRoot)this.attachShadow({mode:'open'});this.hiddenLines??=new Set();this.rows??={};this.historyCache??=new Map();}
 set hass(h){const inputs=[...this.ids(),...this.energyIds(),...this.todayIds(),'sensor.jarvis_pocasi_zitenice'].map(id=>h.states[id]);const changed=!this.inputs||inputs.some((v,i)=>v!==this.inputs[i]);this.inputs=inputs;this.h=h;if(!this.statsKey||!this.statsUpdated||Date.now()-this.statsUpdated>120000)this.fetchStats();if((!this.period||this.period==='day')&&!this.loading&&(!this.updated||Date.now()-this.updated>120000))this.fetchHistory();else if(changed&&!this.renderTimer)this.renderTimer=setTimeout(()=>{this.renderTimer=null;this.render();},150);}
 connectedCallback(){this.clock=setInterval(()=>{if(this.h){if(!this.period||this.period==='day')this.fetchHistory();else this.fetchStats();}},120000);this.resize=new ResizeObserver(()=>this.render());this.resize.observe(this);}
 disconnectedCallback(){clearTimeout(this.renderTimer);clearInterval(this.clock);this.resize?.disconnect();}
 getCardSize(){return 7;}
 ids(){return ['sensor.inverter_pv_power','sensor.inverter_load_power','sensor.inverter_grid_power','sensor.inverter_battery','sensor.jarvis_spot_ote'];}
 dateKey(t=Date.now()){return new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit'}).format(t);}
 selectedBounds(now=Date.now()){return this.dayBounds(this.selectedDate?Date.parse(this.selectedDate+'T12:00:00Z'):now);}
 async chooseDay(date){if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date+'T12:00:00Z')))return;this.selectedDate=date;this.hoverTime=null;this.inspecting=false;this.historyRequest=(this.historyRequest||0)+1;this.loading=false;const start=this.selectedBounds().start,cached=this.historyCache?.get(start);this.rows=cached?.rows||{};this.historyResolution=cached?.resolution||'detail';this.historyDay=cached?start:null;this.updated=cached?.time||null;this.error=null;this.render(true);this.fetchStats();if(!this.period||this.period==='day')await this.fetchHistory();}
 shiftDay(delta){const d=new Date((this.selectedDate||this.dateKey())+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);return d.toISOString().slice(0,10);}
 value(v){if(v===null||v===undefined||String(v).trim()==='')return null;const n=Number(v);return Number.isFinite(n)?n:null;}
 dayBounds(now=Date.now()){
  const f=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Prague',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  const parts=t=>Object.fromEntries(f.formatToParts(t).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
  const p=parts(now),midnight=Date.UTC(p.year,p.month-1,p.day);
  const resolve=target=>{let t=target;for(let i=0;i<4;i++){const q=parts(t);const displayed=Date.UTC(q.year,q.month-1,q.day,q.hour,q.minute,q.second);t+=target-displayed;}return t;};
  return {start:resolve(midnight),end:resolve(midnight+86400000),label:`${p.day}. ${p.month}. ${p.year}`};
 }
 hourlyPoints(data,end){const intervals=data.filter(p=>Number.isFinite(p.start)&&this.value(p.mean)!==null).sort((a,b)=>a.start-b.start),rows=[];for(let i=0;i<intervals.length;i++){const p=intervals[i],stop=Math.min(end,p.end||p.start+3600000);if(stop<=p.start)continue;rows.push({t:p.start,v:this.value(p.mean)},{t:stop-1,v:this.value(p.mean)});if(intervals[i+1]?.start!==stop)rows.push({t:stop,v:null});}return rows;}
 panelProjection(t){const p=JarvisSolarMath.getPosition(new Date(t),50.555,14.156);if(p.altitude<=0)return 0;const tilt=Math.PI/4,azimuth=p.azimuth+Math.PI,arrayAzimuth=135*Math.PI/180;return Math.max(0,Math.sin(p.altitude)*Math.cos(tilt)+Math.cos(p.altitude)*Math.sin(tilt)*Math.cos(azimuth-arrayAzimuth));}
 panelPeak(day){this.solarPeaks??=new Map();if(this.solarPeaks.has(day.start))return this.solarPeaks.get(day.start);let peak={t:day.start,projection:0,altitude:0};for(let t=day.start;t<day.end;t+=60000){const projection=this.panelProjection(t);if(projection>peak.projection)peak={t,projection,altitude:this.altitude(t)};}this.solarPeaks.set(day.start,peak);while(this.solarPeaks.size>400)this.solarPeaks.delete(this.solarPeaks.keys().next().value);return peak;}
 forecastWindow(day){if(this.h?.states['sensor.jarvis_pocasi_zitenice']?.state!=='ready')return null;let best=null;for(const row of this.h.states['sensor.jarvis_pocasi_zitenice'].attributes?.rows||[]){const end=Date.parse(row.time),radiation=this.value(row.shortwave_radiation);if(end-3600000<day.start||end>day.end||radiation===null||radiation<=0)continue;if(!best||radiation>best.radiation)best={start:end-3600000,end,radiation,cloud:this.value(row.cloud_cover)};}return best;}
 solarPlanning(day){const peak=this.panelPeak(day),forecast=this.forecastWindow(day);return `<details class="solar-info"><summary aria-label="Informace o panelech a plánování výroby">ⓘ</summary><div class="solar-plan"><b>Panely DAH DHN-48Z16/DG(BB) · 22 × 460 Wp = 10,12 kWp</b><span>Fáze Měsíce je astronomický výpočet. Procenta ve vysvětlivce označují osvětlenou část jeho kotouče, nikoli osvětlení venku.</span><span>Plocha panelů 43,96 m² (22 × 1,762 × 1,134 m), bez mezer mezi panely.</span><b>☀ Nejlepší geometrické oslunění panelů: ${this.time(peak.t)}</b><span>Žitenice · jihovýchod (135°), sklon 45° · výška Slunce ${this.n(peak.altitude)}°. Zlatá tečka označuje výpočet pro tento den; mraky a stíny mohou skutečný vrchol posunout.</span>${forecast?`<span>☁ Podle předpovědi nejsilnější ozáření ${this.time(forecast.start)}–${this.time(forecast.end)}: ${this.n(forecast.radiation)} W/m² na vodorovnou plochu${forecast.cloud===null?'':` · oblačnost ${this.n(forecast.cloud)} %`}. Orientační okno pro plánování, nikoli odhad výkonu panelů v kW.</span>`:'<span>Pro tento den není dostupná uložená předpověď oblačnosti a ozáření.</span>'}</div></details>`;}
 async dayAverages(day,now){if(!this.h.callWS||day.end>now-86400000)return {};try{const ids=this.ids().slice(0,4),data=await this.h.callWS({type:'recorder/statistics_during_period',start_time:new Date(day.start).toISOString(),end_time:new Date(day.end).toISOString(),statistic_ids:ids,period:'hour',types:['mean'],units:{power:'W'}}),rows={};for(const id of ids){rows[id]=this.hourlyPoints(data[id]||[],day.end);}return rows;}catch{return {};}}
 async archiveDay(day){if(!this.h?.states?.['sensor.jarvis_energy_archive'])return null;try{const data=await this.h.callApi('GET','jarvis_energy_archive/day?date='+this.dateKey(day.start));if(!data||!data.rows)return null;this.archiveDays??=new Map();this.archiveDays.delete(day.start);this.archiveDays.set(day.start,data);while(this.archiveDays.size>14)this.archiveDays.delete(this.archiveDays.keys().next().value);return data;}catch{return null;}}
 async fetchHistory(){if(!this.h)return;const selected=this.selectedBounds(),cached=this.historyCache?.get(selected.start),ttl=selected.end<Date.now()&&cached?.time>=selected.end?86400000:120000;if(cached&&Date.now()-cached.time<ttl){this.rows=cached.rows;this.historyResolution=cached.resolution||'detail';this.historyDay=selected.start;this.updated=cached.time;this.render();return;}
  const request=(this.historyRequest||0)+1;this.historyRequest=request;this.loading=true;this.render();const day=this.selectedBounds(),now=Date.now();
  const archived=this.archiveDay(day);const averages=this.dayAverages(day,now).then(rows=>{if(request===this.historyRequest&&this.loading&&Object.values(rows).some(ps=>ps.some(p=>p.v!==null))){this.rows=rows;this.historyDay=day.start;this.historyResolution='hour';this.render();}return rows;});
  try{const data=day.start>now?[]:await this.h.callApi('GET',`history/period/${new Date(day.start).toISOString()}?end_time=${encodeURIComponent(new Date(Math.min(day.end,now)).toISOString())}&filter_entity_id=${this.ids().join(',')}&minimal_response&no_attributes`);
   if(request!==this.historyRequest)return;let rows={};for(const series of data){const id=series[0]?.entity_id;if(!this.ids().includes(id))continue;rows[id]=series.map(p=>({t:Date.parse(p.last_changed||p.last_updated),v:this.value(p.state)})).filter(p=>Number.isFinite(p.t)).sort((a,b)=>a.t-b.t);}
   const fallback=await averages;if(request!==this.historyRequest)return;this.historyResolution='detail';for(const id of this.ids().slice(0,4)){if(!(rows[id]||[]).some(p=>p.t>=day.start&&p.v!==null)&&(fallback[id]||[]).some(p=>p.v!==null)){rows[id]=fallback[id];this.historyResolution='hour';}}
   const archive=this.h?.states?.['sensor.jarvis_energy_archive']?await archived:null;if(request!==this.historyRequest)return;for(const id of this.ids()){const points=(archive?.rows[id]||[]).map(p=>({t:p.t,v:this.value(p.v)}));if(points.length){const lo=points[0].t,hi=points[points.length-1].t;rows[id]=[...(rows[id]||[]).filter(p=>p.t<lo||p.t>hi),...points].sort((a,b)=>a.t-b.t);}}
   this.rows=rows;this.historyDay=day.start;this.error=null;this.updated=Date.now();this.historyCache??=new Map();this.historyCache.delete(day.start);this.historyCache.set(day.start,{rows,time:this.updated,resolution:this.historyResolution});while(this.historyCache.size>14)this.historyCache.delete(this.historyCache.keys().next().value);
  }catch(e){await averages;if(request===this.historyRequest){this.error=this.historyResolution==='hour'?'Podrobná historie se nenačetla; zobrazuji uložené hodinové průměry.':'Historii vybraného dne se nepodařilo načíst. Zkusím to znovu.';if(this.historyResolution==='hour')this.updated=Date.now();}}finally{if(request===this.historyRequest){this.loading=false;this.render();}}}
 priceAt(t,points,now){
  const rows=[...(this.h?.states['sensor.jarvis_spot_ote']?.attributes?.rows||[]),...(this.archiveDays?.get(this.selectedBounds().start)?.spot||[])];
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
 pointIndex(points,t){let lo=0,hi=points.length;while(lo<hi){const mid=(lo+hi)>>>1;if(points[mid].t<=t)lo=mid+1;else hi=mid;}return lo-1;}
 reading(points,t,now){if(t>now)return null;const i=this.pointIndex(points,t);return i<0?null:points[i].v;}
 batteryAt(points,t,now){let i=this.pointIndex(points,t),j=i+1;if(t>now||i<0)return {value:null,estimated:false};const value=points[i].v;if(value!==null&&!(t>points[i].t&&points[j]?.v===null))return {value,estimated:false};while(i>=0&&points[i].v===null)i--;while(j<points.length&&points[j].v===null)j++;if(i<0||j>=points.length||points[j].t>now)return {value:null,estimated:false};const a=points[i],b=points[j];return {value:a.v+(b.v-a.v)*(t-a.t)/(b.t-a.t),estimated:true};}
 plotPoints(points){const out=[];let bucket=[],minute=null;const flush=()=>{if(!bucket.length)return;const valid=bucket.filter(p=>p.v!==null),extra=valid.length?[valid.reduce((a,b)=>a.v<b.v?a:b),valid.reduce((a,b)=>a.v>b.v?a:b)]:[];out.push(...[...new Set([bucket[0],...extra,...bucket.filter(p=>p.v===null),bucket.at(-1)])].sort((a,b)=>a.t-b.t));};for(const p of points){const next=Math.floor(p.t/60000);if(next!==minute){flush();bucket=[];minute=next;}bucket.push(p);}flush();return out;}
 weatherAt(t){const state=this.h?.states['sensor.jarvis_pocasi_zitenice'];const rows=[...(state?.state==='ready'?state.attributes?.rows||[]:[]),...(this.archiveDays?.get(this.selectedBounds().start)?.weather||[])];return rows.find(r=>{const a=Date.parse(r.time);return a<=t&&t<a+3600000;})||null;}
 weatherInfo(row){const c=this.value(row?.weather_code);if(c===null)return {icon:'?',label:'Počasí není dostupné'};if(c===0)return {icon:'☀️',label:'Jasno'};if(c<3)return {icon:'🌤️',label:'Polojasno'};if(c===3)return {icon:'☁️',label:'Zataženo'};if(c===45||c===48)return {icon:'🌫️',label:'Mlha'};if(c>=95)return {icon:'⛈️',label:'Bouřka'};if(c>=71&&c<=77||c===85||c===86)return {icon:'🌨️',label:'Sněžení'};return {icon:'🌧️',label:'Déšť'};}
 weatherStrip(start,end,w,l,pw){const count=Math.max(3,Math.min(8,Math.floor(pw/80))),cells=[];for(let i=0;i<count;i++){const t=start+(i+.5)/count*(end-start),row=this.weatherAt(t),info=this.weatherInfo(row),night=this.altitude(t)<0,moon=this.moonInfo(t),icon=night?(row?.weather_code<=2?moon.icon:info.icon):info.icon;cells.push(`<span class="weather-cell" style="left:${(l+(i+.5)/count*pw)/w*100}%;width:${pw/w/count*100}%" title="${this.time(t)} · ${info.label}${night?' · '+moon.label+' · osvětlená část měsíčního kotouče '+moon.lit+' %':''}${row?' · předpověď pro Žitenice':''}"><small>${this.time(t)}</small><span class="weather-inline"><span>${row?icon:(night?moon.icon:'—')}</span><b>${row?this.n(this.value(row.temperature_2m))+' °C':'—'}</b></span>${row&&this.value(row.cloud_cover)!==null?`<small>☁ ${this.n(this.value(row.cloud_cover))} %</small>`:''}</span>`);}return `<div class="weather-location">Počasí · Žitenice · předpověď Open-Meteo · ☁ oblačnost v %</div><div class="weather-strip" aria-label="Žitenice · hodinová předpověď počasí a venkovní teploty">${cells.join('')}</div>`;}

 moonInfo(t){const m=JarvisSolarMath.getMoonIllumination(new Date(t)),i=Math.round(m.phase*8)%8;return {icon:['🌑','🌒','🌓','🌔','🌕','🌖','🌗','🌘'][i],label:['Nov','Dorůstající srpek','První čtvrť','Dorůstající Měsíc','Úplněk','Ubývající Měsíc','Poslední čtvrť','Ubývající srpek'][i],lit:Math.round(m.fraction*100)};}
 energyIds(){return ['sensor.inverter_total_production','sensor.inverter_total_load_consumption','sensor.inverter_total_energy_import','sensor.inverter_total_energy_export'];}
 todayIds(){return ['sensor.inverter_today_production','sensor.inverter_today_load_consumption','sensor.inverter_today_energy_import','sensor.inverter_today_energy_export'];}
 periodBounds(){const date=this.selectedDate||this.dateKey(),d=new Date(date+'T12:00:00Z'),period=this.period||'day';let start=new Date(d),end=new Date(d);if(period==='week'){start.setUTCDate(start.getUTCDate()-(start.getUTCDay()+6)%7);end=new Date(start);end.setUTCDate(end.getUTCDate()+7);}else if(period==='month'){start.setUTCDate(1);end=new Date(start);end.setUTCMonth(end.getUTCMonth()+1);}else if(period==='year'){start.setUTCMonth(0,1);end=new Date(start);end.setUTCFullYear(end.getUTCFullYear()+1);}else end.setUTCDate(end.getUTCDate()+1);return {start:this.dayBounds(start.getTime()).start,end:this.dayBounds(end.getTime()).start,period};}
 async fetchStats(){if(!this.h?.callWS)return;const b=this.periodBounds(),key=`${b.period}:${b.start}`,now=Date.now();if(this.statsLoading&&this.statsKey===key)return;if(this.statsKey===key&&now-this.statsUpdated<120000)return;
  const request=(this.statsRequest||0)+1;this.statsRequest=request;this.statsKey=key;this.statsCache??=new Map();const cached=this.statsCache.get(key),ttl=b.end<now&&cached?.time>=b.end?86400000:120000;
  if(cached&&now-cached.time<ttl){this.stats=cached.data;this.statsBounds=b;this.statsUpdated=cached.time;this.statsLoading=false;this.statsError=null;this.render();return;}
  this.statsLoading=true;this.statsError=null;this.render();
  try{const data=b.start>now?{}:await this.h.callWS({type:'recorder/statistics_during_period',start_time:new Date(b.start).toISOString(),end_time:new Date(Math.min(b.end,now)).toISOString(),statistic_ids:this.energyIds(),period:b.period==='day'?'hour':'day',types:['change'],units:{energy:'kWh'}});if(request!==this.statsRequest)return;this.stats=data;this.statsBounds=b;this.statsError=null;this.statsCache.delete(key);this.statsCache.set(key,{data,time:Date.now()});while(this.statsCache.size>24)this.statsCache.delete(this.statsCache.keys().next().value);
  }catch(e){if(request!==this.statsRequest)return;this.stats={};this.statsBounds=b;this.statsError='Statistiky pro toto období nejsou dostupné.';}finally{if(request===this.statsRequest){this.statsLoading=false;this.statsUpdated=Date.now();this.render();}}}
 choosePeriod(period){this.period=period;this.statsKey=null;this.fetchStats();this.render();if(period==='day'&&!this.updated)this.fetchHistory();}
 periodButtons(){return `<nav class="periods" aria-label="Období přehledu">${[['day','Den'],['week','Týden'],['month','Měsíc'],['year','Rok']].map(([id,label])=>`<button data-period="${id}" aria-pressed="${(this.period||'day')===id}">${label}</button>`).join('')}</nav>`;}
 energyTotals(){const b=this.periodBounds(),today=this.dayBounds(),now=Date.now();return this.energyIds().map((id,i)=>{if(b.period==='day'&&b.start===today.start)return this.value(this.h.states[this.todayIds()[i]]?.state);if(this.statsBounds?.start!==b.start||this.statsBounds?.period!==b.period)return null;const rows=(this.stats?.[id]||[]).filter(r=>r.start>=b.start&&r.start<Math.min(b.end,now));let valid=rows.filter(r=>Number.isFinite(r.change));if(b.period!=='day'&&b.start<=today.start&&b.end>now){valid=valid.filter(r=>r.start<today.start);const current=this.value(this.h.states[this.todayIds()[i]]?.state);if(current!==null)valid.push({change:current});}return valid.length?valid.reduce((total,r)=>total+r.change,0):null;});}
 summaryHTML(){const names=['Vyrobeno ze slunce','Spotřeba domu','Odběr ze sítě','Dodávka do sítě'];return `<section class="energy-summary" aria-label="Energetická bilance vybraného období">${this.energyTotals().map((v,i)=>`<div><span>${names[i]}</span><b>${this.n(v)} kWh</b></div>`).join('')}</section><div class="balance-note">${this.statsLoading?'⏳ Načítám uložené statistiky… ':''}${this.statsError||''} Množství podle měniče, nikoli potvrzení placeného prodeje. Finance zatím nejsou vypočtené. ${(this.period&&this.period!=='day')||this.selectedBounds().start!==this.dayBounds().start?'Součet dostupných statistik; chybějící období nejsou doplněná nulou. Statistiky mohou mít zpoždění, dnešek doplňuji z denních čítačů.':''}</div>`;}
 periodStyles(){return `.periods{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}.periods button{font:inherit;padding:7px 12px;border:1px solid #8796aa55;border-radius:9px;background:transparent;color:inherit;cursor:pointer}.periods button[aria-pressed=true]{background:#4667d51a;border-color:#4667d5}.energy-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0}.energy-summary div{padding:10px;border-radius:10px;background:#8796aa12}.energy-summary span{display:block;font-size:11px}.energy-summary b{display:block;font-size:18px;margin-top:5px}.balance-note{font-size:11px;color:var(--secondary-text-color,#63758a);line-height:1.5;margin:5px 0 12px}@media(max-width:600px){.energy-summary{grid-template-columns:1fr 1fr}.energy-summary b{font-size:16px}}`;}
 bindPeriods(){this.shadowRoot.querySelectorAll('[data-period]').forEach(b=>b.onclick=()=>this.choosePeriod(b.dataset.period));}
 periodDateLabel(key,full=false){const d=new Date(key+(key.length===7?'-01':'')+'T12:00:00Z');return d.toLocaleDateString('cs-CZ',key.length===7?{month:full?'long':'short',...(full?{year:'numeric'}:{}),timeZone:'UTC'}:{...(full?{weekday:'long',year:'numeric'}:{}),day:'numeric',month:'numeric',timeZone:'UTC'});}
 periodEntries(){const b=this.periodBounds(),byDay=new Map(),today=this.dayBounds();
  const date=new Date(this.dateKey(b.start)+'T12:00:00Z'),last=this.dateKey(b.end);
  while(date.toISOString().slice(0,10)<last){const key=date.toISOString().slice(0,b.period==='year'?7:10);byDay.set(key,[null,null,null,null]);if(b.period==='year')date.setUTCMonth(date.getUTCMonth()+1);else date.setUTCDate(date.getUTCDate()+1);}
  if(this.statsBounds?.start===b.start&&this.statsBounds?.period===b.period){this.energyIds().forEach((id,i)=>{for(const row of this.stats?.[id]||[]){if(!Number.isFinite(row.change)||row.start<b.start||row.start>=b.end||b.start<=today.start&&b.end>Date.now()&&row.start>=today.start)continue;const key=this.dateKey(row.start).slice(0,b.period==='year'?7:10),values=byDay.get(key);if(values)values[i]=(values[i]??0)+row.change;}});
   if(b.start<=today.start&&b.end>Date.now()){const values=byDay.get(this.dateKey().slice(0,b.period==='year'?7:10));this.todayIds().forEach((id,i)=>{const v=this.value(this.h.states[id]?.state);if(v!==null&&values)values[i]=(values[i]??0)+v;});}}
  return [...byDay];
 }
 renderPeriod(force=false){
  const active=force?null:this.shadowRoot.activeElement,focus=active?.dataset.period?`[data-period="${active.dataset.period}"]`:active?.dataset.energy!==undefined?`[data-energy="${active.dataset.energy}"]`:active?.matches('input[type=date]')?'input[type=date]':active?.matches('.period-scrub')?'.period-scrub':active?.hasAttribute('data-back')?'[data-back]':active?.hasAttribute('data-next')?'[data-next]':active?.hasAttribute('data-today')?'[data-today]':null;
  const b=this.periodBounds(),names={week:'Týden',month:'Měsíc',year:'Rok'},colors=['#4667d5','#d99c16','#eb6859','#199b7b'],series=['Výroba','Spotřeba','Odběr ze sítě','Dodávka do sítě'],entries=this.periodEntries();this.hiddenEnergy??=new Set();
  const w=Math.max(330,this.clientWidth-32),h=310,l=48,r=15,top=24,bottom=48,pw=w-l-r,ph=h-top-bottom,group=pw/entries.length,bw=Math.min(20,group*.18),max=Math.max(1,...entries.flatMap(e=>e[1].filter((v,i)=>v!==null&&!this.hiddenEnergy.has(i)))),hi=Math.ceil(max*1.08*10)/10,base=h-bottom;
  const labelStep=Math.max(1,Math.ceil(entries.length/Math.max(2,Math.floor(pw/85))));
  const bars=entries.map(([key,vals],j)=>`${b.period!=='year'&&[0,6].includes(new Date(key+'T12:00:00Z').getUTCDay())?`<rect x="${l+j*group}" y="${top}" width="${group}" height="${ph}" fill="currentColor" opacity=".025"/>`:''}${vals.map((v,i)=>v===null||this.hiddenEnergy.has(i)?'':`<rect x="${l+(j+.5)*group+(i-2)*bw}" y="${base-v/hi*ph}" width="${bw*.84}" height="${Math.max(.6,v/hi*ph)}" rx="1.5" fill="${colors[i]}"/>`).join('')}${b.period==='year'?'':`<circle class="period-solar-peak" cx="${l+(j+.5)*group}" cy="${base+11}" r="3" fill="#b88500"><title>${this.periodDateLabel(key,true)} · nejlepší oslunění ${this.time(this.panelPeak(this.dayBounds(Date.parse(key+'T12:00Z'))).t)}</title></circle>`}${j%labelStep===0||j===entries.length-1&&entries.length%labelStep>1?`<text x="${l+(j+.5)*group}" y="${h-20}" text-anchor="middle">${this.periodDateLabel(key)}</text>`:''}`).join('');
  this.shadowRoot.innerHTML=`<style>:host{display:block;min-width:0}*{box-sizing:border-box}ha-card{display:block;padding:16px;color:var(--primary-text-color,#172c42);background:var(--card-background-color,#fff);font:14px system-ui;border-radius:18px}h2{margin:0 0 5px;font-size:21px}.subtitle,.hint{font-size:12px;color:var(--secondary-text-color,#63758a)}svg{display:block;width:100%;overflow:visible}.days{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}button,input{font:inherit;color:inherit;background:transparent;border:1px solid #8796aa55;border-radius:8px;padding:8px;min-width:0}.legend{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.legend button{font-size:12px;cursor:pointer;text-align:left;flex:1;min-width:135px}.legend button[aria-pressed=false]{opacity:.4}.legend b{display:block;margin:4px 0 0 13px;font-size:15px}.period-readout{font-weight:600;min-height:26px;padding:3px 0}.period-hit{cursor:crosshair;touch-action:pan-y}.period-scrub{width:100%;accent-color:#4667d5;padding:0;margin:8px 0}button:focus-visible,input:focus-visible{outline:2px solid #4667d5;outline-offset:2px}${this.periodStyles()}@media(max-width:500px){ha-card{padding:12px 8px}.legend{display:grid;grid-template-columns:1fr 1fr}.legend button{min-width:0}h2{font-size:19px}}</style><ha-card><h2>Energetická bilance · ${names[b.period]}</h2><div class="subtitle">${new Date(b.start).toLocaleDateString('cs-CZ',{timeZone:'Europe/Prague'})} – ${new Date(b.end-1).toLocaleDateString('cs-CZ',{timeZone:'Europe/Prague'})}</div>${this.periodButtons()}<div class="days"><button data-back aria-label="Předchozí období">‹</button><input type="date" aria-label="Den grafu" value="${this.selectedDate||this.dateKey()}"><button data-next aria-label="Následující období">›</button><button data-today>Dnes</button></div>${this.summaryHTML()}<div class="legend" aria-label="Zobrazované energie">${series.map((n,i)=>`<button data-energy="${i}" aria-pressed="${!this.hiddenEnergy.has(i)}"><span style="color:${colors[i]}">●</span> ${n}<b data-energy-value="${i}">— kWh</b></button>`).join('')}</div><div class="period-readout" aria-live="off"></div><svg viewBox="0 0 ${w} ${h}" aria-label="Energetická bilance v kWh"><g font-size="11" fill="currentColor"><text x="${l}" y="14">kWh</text>${[0,.25,.5,.75,1].map(f=>`<text x="${l-7}" y="${base-f*ph+4}" text-anchor="end">${this.n(hi*f)}</text><line x1="${l}" x2="${w-r}" y1="${base-f*ph}" y2="${base-f*ph}" stroke="currentColor" opacity=".12"/>`).join('')}${bars}<rect class="period-selection" y="${top}" width="${group}" height="${ph}" fill="#4667d5" opacity=".08"/><line class="period-cursor" y1="${top}" y2="${base}" stroke="currentColor" opacity=".5"/><rect class="period-hit" x="${l}" y="${top}" width="${pw}" height="${ph}" fill="transparent"/></g></svg><input class="period-scrub" type="range" min="0" max="${entries.length-1}" step="1" aria-label="${b.period==='year'?'Měsíc':'Den'} v přehledu"><div class="hint">Přejeď myší nebo klepni do grafu. Hodnoty se zobrazí hned nahoře; barevnými tlačítky zapínáš jednotlivé řady. ${b.period==='year'?'Sloupce představují měsíce.':'Sloupce představují jednotlivé dny; víkendy mají jemné pozadí.'} ${b.period==='year'?'':'Zlaté body pod sloupci označují geometrické maximum oslunění pro jednotlivé dny (JV, sklon 45°); čas je v přehledu vybraného dne. '}Prázdné místo znamená chybějící nebo budoucí údaje.</div></ha-card>`;
  const update=index=>{index=Math.max(0,Math.min(entries.length-1,Math.round(index)));const [key,values]=entries[index];this.periodHoverKey=key;this.shadowRoot.querySelector('.period-readout').textContent=this.periodDateLabel(key,true)+(b.period==='year'?'':' · ☀ nejlepší oslunění '+this.time(this.panelPeak(this.dayBounds(Date.parse(key+'T12:00Z'))).t))+(values.every(v=>v===null)?' · zatím bez údajů':'');this.shadowRoot.querySelectorAll('[data-energy-value]').forEach(el=>{const i=Number(el.dataset.energyValue);el.textContent=this.hiddenEnergy.has(i)?'skryto':this.n(values[i])+' kWh';});this.shadowRoot.querySelector('.period-selection').setAttribute('x',l+index*group);for(const a of ['x1','x2'])this.shadowRoot.querySelector('.period-cursor').setAttribute(a,l+(index+.5)*group);this.shadowRoot.querySelector('.period-scrub').value=index;};
  const pointer=e=>{const rect=this.shadowRoot.querySelector('svg').getBoundingClientRect();update(Math.floor(((e.clientX-rect.left)/rect.width*w-l)/group));};const hit=this.shadowRoot.querySelector('.period-hit');hit.onpointermove=pointer;hit.onpointerdown=pointer;this.shadowRoot.querySelector('.period-scrub').oninput=e=>update(Number(e.target.value));
  this.bindPeriods();this.shadowRoot.querySelectorAll('[data-energy]').forEach(el=>el.onclick=()=>{const i=Number(el.dataset.energy);this.hiddenEnergy.has(i)?this.hiddenEnergy.delete(i):this.hiddenEnergy.add(i);this.render();});
  this.bindDateInput();this.shadowRoot.querySelector('[data-today]').onclick=()=>this.chooseDay(this.dateKey());for(const [selector,sign]of [['[data-back]',-1],['[data-next]',1]])this.shadowRoot.querySelector(selector).onclick=()=>{const date=new Date((this.selectedDate||this.dateKey())+'T12:00:00Z');if(b.period==='week')date.setUTCDate(date.getUTCDate()+7*sign);else if(b.period==='month'){date.setUTCDate(1);date.setUTCMonth(date.getUTCMonth()+sign);}else{date.setUTCMonth(0,1);date.setUTCFullYear(date.getUTCFullYear()+sign);}this.periodHoverKey=null;this.chooseDay(date.toISOString().slice(0,10));};
  let selected=entries.findIndex(e=>e[0]===this.periodHoverKey);if(selected<0)selected=entries.findIndex(e=>e[0]===this.dateKey().slice(0,b.period==='year'?7:10));if(selected<0)selected=0;update(selected);if(focus)this.shadowRoot.querySelector(focus)?.focus({preventScroll:true});
 }
 bindDateInput(){const input=this.shadowRoot.querySelector('input[type=date]');const commit=()=>{const date=input.value;if(input.validity?.valid===false||!/^\d{4}-\d{2}-\d{2}$/.test(date)||date===(this.selectedDate||this.dateKey()))return false;this.chooseDay(date);return true;};input.oninput=commit;input.onchange=commit;input.onblur=()=>{if(commit())return;if(this.dateRenderPending){this.dateRenderPending=false;setTimeout(()=>this.render(),0);}};}
 render(force=false){if(!this.shadowRoot||!this.h)return;if(!force&&this.shadowRoot.activeElement?.matches('input[type=date]')){this.dateRenderPending=true;return;}this.dateRenderPending=false;if(this.period&&this.period!=='day'){this.renderPeriod(force);return;}
  const active=force?null:this.shadowRoot.activeElement,focus=active?.matches('.scrub')?'.scrub':active?.matches('.date')?'.date':active?.dataset.period?`[data-period="${active.dataset.period}"]`:active?.dataset.day?`[data-day="${active.dataset.day}"]`:active?.dataset.line!==undefined?`[data-line="${Number(active.dataset.line)}"]`:null;
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
  const peak=this.panelPeak(day);const sun=[];for(let t=start;t<end;t+=300000)sun.push({t,v:this.altitude(t)});sun.push({t:end,v:this.altitude(end)});
  const bands=sun.slice(1).map((p,i)=>{const a=(p.v+sun[i].v)/2,c=a>=0?'#fff7da':a>=-6?'#deebf5':a>=-12?'#bed0e0':a>=-18?'#a2b6cb':'#8796aa';return `<rect x="${x(sun[i].t)}" y="${top}" width="${x(p.t)-x(sun[i].t)+.2}" height="${ph}" fill="${c}" opacity=".48"/>`;}).join('');
  const grid=Array.from({length:Math.round((hi-lo)/step)+1},(_,i)=>{const v=lo+step*i;return `<line x1="${l}" x2="${w-r}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".14"/><text x="${l-7}" y="${y(v)+4}" text-anchor="end">${this.n(v)}</text>`;}).join('');
  const curves=series.slice(0,4).map((ps,i)=>{if(this.hiddenLines.has(i))return '';const scale=i===3?by:y;let d='',open=false;for(const p of this.plotPoints(ps)){if(p.v===null){open=false;continue;}d+=`${open?'L':'M'}${x(p.t)},${scale(p.v)} `;open=true;}return `<path d="${d}" fill="none" stroke="${colors[i]}" stroke-width="2" vector-effect="non-scaling-stroke"/>`;}).join('');
  let priceCurve='';if(!this.hiddenLines.has(4)){let previous=null;priceCurve=priceSegments.map(p=>{if(p.v===null){previous=null;return '';}const vertical=previous&&previous.end===p.start?`<line x1="${x(p.start)}" x2="${x(p.start)}" y1="${py(previous.v)}" y2="${py(p.v)}" stroke="${colors[4]}" stroke-width="2"/>`:'';previous=p;return vertical+`<line x1="${x(p.start)}" x2="${x(p.end)}" y1="${py(p.v)}" y2="${py(p.v)}" stroke="${colors[4]}" stroke-width="2"/>`;}).join('');}
  let batteryBridges='';if(!this.hiddenLines.has(3)&&this.historyResolution!=='hour'){let previous=null,gap=false;for(const p of series[3]){if(p.v===null){gap=true;continue;}if(gap&&previous)batteryBridges+=`<line x1="${x(previous.t)}" x2="${x(p.t)}" y1="${by(previous.v)}" y2="${by(p.v)}" stroke="${colors[3]}" stroke-width="1.8" stroke-dasharray="4 3"><title>Odhad mezi dvěma měřeními baterie</title></line>`;previous=p;gap=false;}}
  const ticks=Array.from({length:7},(_,i)=>{const hour=i*4; // Clock labels, including explicit 24:00, stay in Prague time.
   let t=start;if(hour===24)t=end;else if(hour){t=start+hour*3600000;for(let j=0;j<3;j++){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Prague',hourCycle:'h23',hour:'2-digit',minute:'2-digit'}).format(new Date(t)).split(':').map(Number);t+=(hour-parts[0]-parts[1]/60)*3600000;}}
   return `<text x="${x(t)}" y="${h-9}" text-anchor="${i===0?'start':i===6?'end':'middle'}">${String(hour).padStart(2,'0')}:00</text>`;}).join('');
  const legend=names.map((name,i)=>`<button data-line="${i}" aria-pressed="${!this.hiddenLines.has(i)}" class="${this.hiddenLines.has(i)?'muted':''}"><span class="dot" style="background:${colors[i]}"></span>${name} <b data-value="${i}"></b></button>`).join('');
  const svg=`<svg viewBox="0 0 ${w} ${h}" aria-label="Denní výkon od 00:00 do 24:00"><g font-size="11" fill="currentColor">${bands}${grid}<text x="${l}" y="15">W</text><text x="${w-r+6}" y="15" fill="${colors[3]}">%</text><text x="${w-r+40}" y="15" fill="${colors[4]}">Kč/kWh</text><text x="${w-10}" y="15" text-anchor="end" fill="${colors[5]}">°</text>${[0,25,50,75,100].map(v=>`<text x="${w-r+6}" y="${by(v)+4}" fill="${colors[3]}">${v}</text><text x="${w-r+40}" y="${by(v)+4}" fill="${colors[4]}">${this.n(priceLo+(priceHi-priceLo)*v/100)}</text><text x="${w-10}" y="${by(v)+4}" text-anchor="end" fill="${colors[5]}">${-90+v*1.8}</text>`).join('')}${curves}${batteryBridges}${priceCurve}${this.hiddenLines.has(5)?'':`<polyline fill="none" stroke="${colors[5]}" stroke-width="2" stroke-dasharray="6 4" points="${sun.map(p=>`${x(p.t)},${sy(p.v)}`).join(' ')}"/>`}${now>=start&&now<end?`<line x1="${x(now)}" x2="${x(now)}" y1="${top}" y2="${h-bottom}" stroke="currentColor" stroke-dasharray="3 4" opacity=".4"/>`:""}${this.hiddenLines.has(5)?'':`<circle class="solar-peak" cx="${x(peak.t)}" cy="${sy(peak.altitude)}" r="6" fill="#ffbe28" stroke="#fff" stroke-width="2"><title>Nejlepší geometrické oslunění panelů ${this.time(peak.t)} · JV 135°, sklon 45°</title></circle>`}${ticks}<line class="cursor" y1="${top}" y2="${h-bottom}" stroke="var(--primary-text-color,#172c42)" stroke-width="1" visibility="hidden"/><rect class="hit" x="${l}" y="${top}" width="${pw}" height="${ph}" fill="transparent"/></g></svg>`;
  this.shadowRoot.innerHTML=`<style>${this.periodStyles()}:host{display:block;min-width:0}*{box-sizing:border-box}ha-card{display:block;padding:16px 12px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#172c42);font:14px system-ui;border-radius:18px}header{display:flex;align-items:center;justify-content:space-between;gap:10px}h2{font-size:21px;margin:0 0 5px}.subtitle{font-size:12px;color:var(--secondary-text-color,#63758a)}.days{display:flex;gap:8px;align-items:center;margin-top:12px}.date{font:inherit;color:inherit;background:transparent;border:1px solid #8796aa55;padding:8px;border-radius:8px;min-width:0}.legend{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 8px}button{font:inherit;font-size:12px;border:1px solid #8796aa55;border-radius:10px;padding:9px;background:transparent;color:inherit;cursor:pointer;text-align:left}button[aria-pressed=true]{background:#8796aa12}.muted{opacity:.45}button:focus-visible,.scrub:focus-visible{outline:2px solid #4667d5;outline-offset:3px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}b[data-value]{display:inline-block;min-width:62px}svg{display:block;width:100%;overflow:visible}.hit{cursor:crosshair;touch-action:pan-y}.weather-location{font-size:12px;font-weight:600;margin-top:8px;color:var(--secondary-text-color,#63758a)}.solar-info{position:relative;margin:4px 0 4px auto;width:28px;text-align:right}.solar-info::details-content{content-visibility:visible}.solar-info>summary{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border:1px solid #8796aa55;border-radius:50%;cursor:pointer;font-size:19px;list-style:none;color:var(--primary-color,#4667d5)}.solar-info>summary::-webkit-details-marker{display:none}.solar-info>.solar-plan{display:none;position:absolute;right:0;top:28px;width:min(620px,calc(100vw - 48px));max-height:60vh;overflow:auto;z-index:5;text-align:left;box-shadow:0 4px 18px #0003;background:var(--card-background-color,#fff)}.solar-info[open]>.solar-plan,.solar-info:focus-within>.solar-plan{display:flex}@media(hover:hover){.solar-info:hover>.solar-plan{display:flex}}.solar-info>summary:focus-visible{outline:2px solid #4667d5;outline-offset:3px}.solar-plan{display:flex;flex-direction:column;gap:4px;font-size:12px;line-height:1.45;border-left:3px solid #b88500;background:#b885000a;padding:8px 10px;margin:8px 0}.solar-plan span{color:var(--secondary-text-color,#63758a)}.weather-strip{height:63px;position:relative;border-top:1px solid #8796aa33;background:linear-gradient(180deg,#e2eff940,transparent);margin-top:7px}.weather-cell{position:absolute;transform:translateX(-50%);text-align:center;display:flex;flex-direction:column;align-items:center;gap:2px;padding-top:6px;font-size:17px;line-height:1.15}.weather-inline{display:flex;gap:4px;align-items:center;white-space:nowrap}.weather-cell small{font-size:10px;color:var(--secondary-text-color,#63758a)}.weather-cell b{font-size:12px;font-weight:600}.readout{font-weight:600;min-height:22px;padding:5px 0}.hint,details{font-size:12px;color:var(--secondary-text-color,#63758a);line-height:1.6}.error{color:#bd2435}.scrub{width:100%;accent-color:#4667d5;margin:6px 0}@media(max-width:500px){ha-card{padding:12px 6px}h2{font-size:19px}.legend{display:grid;grid-template-columns:1fr 1fr;gap:5px}button{font-size:11px;padding:8px 5px}b[data-value]{display:block;margin:4px 0 0 15px}svg{min-height:280px}}</style><ha-card><header><div><h2>Výkon během dne</h2><span class="subtitle">${day.label} · 00:00–24:00 · Žitenice</span></div></header>${this.periodButtons()}${this.summaryHTML()}<nav class="days" aria-label="Výběr dne"><button data-day="prev" aria-label="Předchozí den">‹</button><input class="date" type="date" aria-label="Den grafu" value="${this.selectedDate||this.dateKey(now)}"><button data-day="next" aria-label="Následující den">›</button><button data-day="today">Dnes</button></nav><div class="legend" aria-label="Zobrazované křivky">${legend}</div><div class="readout" aria-live="off"></div><div class="hint" role="status">${this.loading?'⏳ Načítám podrobnou historii vybraného dne… ':''}${this.historyResolution==='hour'?'Starší nebo chybějící podrobná měření nahrazuji dostupnými hodinovými průměry z dlouhodobých statistik. Navazující hodiny jsou propojené; skutečné výpadky zůstávají prázdné. ':''}${!this.loading&&day.end<now&&!series.slice(0,4).some(ps=>ps.some(p=>p.v!==null))?'Podrobná historie ani hodinové statistiky pro tento den nejsou dostupné.':''}</div>${this.error?`<p class="error">${this.error}</p>`:''}${this.solarPlanning(day)}${this.weatherStrip(start,end,w,l,pw)}${svg}<input class="scrub" type="range" min="0" max="${span/60000}" step="1" aria-label="Čas v grafu"><div class="hint">Přejeď myší, klepni do grafu nebo posuň čas jezdcem. Síť: + odběr, − dodávka.</div><details><summary>Jak číst graf</summary>Výkony jsou ve W. Baterie je v procentech, cena v Kč/kWh bez DPH před poplatky obchodníka a Slunce ve stupních; každá veličina má vlastní barevnou stupnici vpravo. Šedá znamená noc, modrá soumrak, světlá den. Přerušovaná zelená čára a ≈ znamenají odhad mezi dvěma měřeními baterie, nikoli nové měření. Bez obou krajních měření se odhad nedoplňuje. Lišta počasí a venkovní teploty je předpověď Open-Meteo; u starších dnů nemusí být dostupná. Výpadky se nedoplňují nulou. Křivka Slunce je astronomický výpočet.</details><div class="hint">${this.loading?"Načítám historii… ":""}${day.start>now?"Budoucí den: naměřené výkony a baterie zatím nejsou dostupné. ":""}${!forecast.length&&day.start>now?"Zdroj zatím neposkytl ceny pro tento den; automaticky je zkouším načítat každých 15 minut.":""} Historie je dostupná podle uchovávání dat v Home Assistantu.</div></ha-card>`;
  const update=t=>{t=Math.max(start,Math.min(end,this.selectionTime(t,now)));this.hoverTime=t;const future=t>now;this.shadowRoot.querySelector('.readout').textContent=`${t===end?'24:00':this.time(t)}${future?' · zatím bez měření':''}`;
   this.shadowRoot.querySelectorAll('[data-value]').forEach(el=>{const i=Number(el.dataset.value),battery=i===3?(this.historyResolution==='hour'?{value:this.reading(series[3],t,now),estimated:false}:this.batteryAt(series[3],t,now)):null,v=i===5?this.altitude(t):i===4?this.priceAt(t,series[4],now):i===3?battery.value:this.reading(series[i],t,now);el.textContent=this.hiddenLines.has(i)?'skryto':`${battery?.estimated?'≈ ':''}${this.n(v)} ${units[i]}`;});
   const weather=this.weatherAt(t),night=this.altitude(t)<0,moon=this.moonInfo(t);if(weather){const info=this.weatherInfo(weather),icon=night&&weather.weather_code<=2?moon.icon:info.icon;this.shadowRoot.querySelector('.readout').textContent+=` · ${icon} ${info.label} · venku ${this.n(this.value(weather.temperature_2m))} °C (předpověď)`;}if(night)this.shadowRoot.querySelector('.readout').textContent+=` · ${moon.icon} ${moon.label}`;
   const line=this.shadowRoot.querySelector('.cursor');line.setAttribute('x1',x(t));line.setAttribute('x2',x(t));line.setAttribute('visibility','visible');this.shadowRoot.querySelector('.scrub').value=(t-start)/60000;
  };
  this.bindPeriods();
  const info=this.shadowRoot.querySelector('.solar-info');info.onpointerenter=e=>{if(e.pointerType==='mouse')info.open=true;};info.onpointerleave=e=>{if(e.pointerType==='mouse')info.open=false;};
  this.shadowRoot.querySelector('[data-day=prev]').onclick=()=>this.chooseDay(this.shiftDay(-1));
  this.shadowRoot.querySelector('[data-day=next]').onclick=()=>this.chooseDay(this.shiftDay(1));
  this.shadowRoot.querySelector('[data-day=today]').onclick=()=>this.chooseDay(this.dateKey());
  this.bindDateInput();
  this.shadowRoot.querySelectorAll('[data-line]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.line);this.hiddenLines.has(i)?this.hiddenLines.delete(i):this.hiddenLines.add(i);this.render();});
  this.shadowRoot.querySelector('.hit').onpointermove=e=>{this.inspecting=true;const rect=this.shadowRoot.querySelector('svg').getBoundingClientRect();const px=(e.clientX-rect.left)/rect.width*w;update(start+(px-l)/pw*span);};
  this.shadowRoot.querySelector('.hit').onpointerdown=e=>{this.inspecting=true;const rect=this.shadowRoot.querySelector('svg').getBoundingClientRect();update(start+((e.clientX-rect.left)/rect.width*w-l)/pw*span);};
  this.shadowRoot.querySelector('.scrub').oninput=e=>{this.inspecting=true;update(start+Number(e.target.value)*60000);};
  update(this.inspecting&&this.hoverTime>=start&&this.hoverTime<=end?this.hoverTime:now>=start&&now<end?now:start);
  if(focus)this.shadowRoot.querySelector(focus)?.focus({preventScroll:true});
 }
}
if(!customElements.get('jarvis-power-sun'))customElements.define('jarvis-power-sun',JarvisPowerSun);
