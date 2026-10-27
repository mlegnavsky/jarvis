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
 setConfig(c){this.cfg=c;if(!this.shadowRoot)this.attachShadow({mode:'open'});this.hiddenLines=new Set();this.rows={};}
 set hass(h){this.h=h;if(!this.loading&&(!this.updated||Date.now()-this.updated>120000))this.fetchHistory();else this.render();}
 connectedCallback(){this.clock=setInterval(()=>{if(this.h)this.fetchHistory()},120000);this.resize=new ResizeObserver(()=>this.render());this.resize.observe(this);}
 disconnectedCallback(){clearInterval(this.clock);this.resize?.disconnect();}
 getCardSize(){return 7;}
 ids(){return ['sensor.inverter_pv_power','sensor.inverter_load_power','sensor.inverter_grid_power'];}
 async fetchHistory(){if(this.loading||!this.h)return;this.loading=true;try{
  let start=new Date(Date.now()-86400000).toISOString();let data=await this.h.callApi('GET',`history/period/${start}?filter_entity_id=${this.ids().join(',')}&minimal_response&no_attributes`);
  let rows={};for(let series of data){let id=series[0]?.entity_id;if(!this.ids().includes(id))continue;rows[id]=series.map(p=>({t:Date.parse(p.last_changed||p.last_updated),v:p.state===null||p.state===''?NaN:Number(p.state)})).filter(p=>Number.isFinite(p.v)&&Number.isFinite(p.t));}this.rows=rows;this.error=null;this.updated=Date.now();
 }catch(e){this.error='Historii se nepodařilo načíst. Zkusím to znovu.';}finally{this.loading=false;this.render();}}
 n(v){return Number.isFinite(v)?v.toLocaleString('cs-CZ',{maximumFractionDigits:1}):'—';}
 time(t){return new Date(t).toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Prague'});}
 altitude(t){return JarvisSolarMath.getPosition(new Date(t),50.555,14.156).altitude*180/Math.PI;}
 compact(points){let groups=new Map();for(let p of points){let k=Math.floor(p.t/60000);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(p);}return [...groups.values()].flatMap(g=>{let min=g.reduce((a,b)=>a.v<b.v?a:b),max=g.reduce((a,b)=>a.v>b.v?a:b);return [...new Set([g[0],min,max,g.at(-1)])].sort((a,b)=>a.t-b.t);});}
 render(){if(!this.shadowRoot||!this.h)return;let now=Date.now(),start=now-86400000,w=Math.max(280,(this.expanded?window.innerWidth:this.clientWidth)-8),h=this.expanded?Math.max(240,window.innerHeight-170):Math.min(420,Math.max(300,w*.82)),l=43,r=10,top=30,bottom=34,plotW=w-l-r,plotH=h-top-bottom;
  const colors=['#4667d5','#e3aa32','#f06d58'],names=['Výroba soláru','Spotřeba domu','Síť · + odběr / − dodávka'];
  let series=this.ids().map(id=>{let p=(this.rows[id]||[]).filter(p=>p.t>=start&&p.t<=now);if(p.length&&p[0].t>start){let before=(this.rows[id]||[]).filter(p=>p.t<start).at(-1);if(before)p.unshift({t:start,v:before.v});}let v=Number(this.h.states[id]?.state);if(Number.isFinite(v))p.push({t:now,v});return this.compact(p)});
  let vals=series.flat().map(p=>p.v),rawLo=Math.min(-100,...vals),rawHi=Math.max(1000,...vals),step=Math.max(200,Math.ceil((rawHi-rawLo)/5/500)*500),lo=Math.floor(rawLo/step)*step,hi=Math.ceil(rawHi/step)*step,x=t=>l+(t-start)/86400000*plotW,y=v=>top+(hi-v)/(hi-lo)*plotH,sy=v=>top+(90-v)/180*plotH;
  let sun=[];for(let t=start;t<=now;t+=300000)sun.push({t,v:this.altitude(t)});sun.push({t:now,v:this.altitude(now)});
  let runs=[];for(let i=1;i<sun.length;i++){let e=(sun[i].v+sun[i-1].v)/2,c=e>=0?'#fff7da':e>=-6?'#deebf5':e>=-12?'#bed0e0':e>=-18?'#a2b6cb':'#8796aa';let last=runs.at(-1);if(last&&last.c===c)last.end=sun[i].t;else runs.push({start:sun[i-1].t,end:sun[i].t,c});}let bands=runs.map(p=>`<rect x="${x(p.start)}" y="${top}" width="${x(p.end)-x(p.start)}" height="${plotH}" fill="${p.c}" opacity=".48"/>`).join('');
  let grid=Array.from({length:Math.round((hi-lo)/step)+1},(_,i)=>{let v=lo+step*i;return `<line x1="${l}" x2="${w-r}" y1="${y(v)}" y2="${y(v)}" stroke="currentColor" opacity=".16"/><text x="${l-7}" y="${y(v)+4}" text-anchor="end">${Math.round(v).toLocaleString('cs-CZ')}</text>`}).join('');
  let curves=series.map((p,i)=>this.hiddenLines.has(i)?'':`<polyline fill="none" stroke="${colors[i]}" stroke-width="1.5" vector-effect="non-scaling-stroke" points="${p.map(p=>`${x(p.t)},${y(p.v)}`).join(' ')}"/>`).join('');
  let currentSun=sun.at(-1).v,phase=currentSun>=0?'nad horizontem':currentSun>=-6?'občanský soumrak':currentSun>=-12?'nautický soumrak':currentSun>=-18?'astronomický soumrak':'noc';
  const svg=`<svg role="img" aria-label="Výkon domu za 24 hodin s nočním stínováním a výškou Slunce na pravé ose" viewBox="0 0 ${w} ${h}"><g font-size="12" fill="currentColor">${bands}${grid}<text x="${l}" y="16">W</text><text x="${w-r-3}" text-anchor="end" y="16" fill="#9a6500">Slunce °</text>${[-90,-45,0,45,90].map(v=>`<text x="${w-r-4}" y="${sy(v)+4}" text-anchor="end" fill="#835800" stroke="var(--card-background-color,#fff)" stroke-width="3" paint-order="stroke">${v}°</text>`).join('')}<line x1="${l}" x2="${w-r}" y1="${sy(0)}" y2="${sy(0)}" stroke="#9a6500" stroke-dasharray="5 4" opacity=".7"/><text x="${l+4}" y="${sy(0)-6}" fill="#835800">horizont Slunce 0°</text>${curves}${this.hiddenLines.has(3)?'':`<polyline fill="none" stroke="#b88500" stroke-width="2" stroke-dasharray="7 3" points="${sun.map(p=>`${x(p.t)},${sy(p.v)}`).join(' ')}"/><circle cx="${x(now)-5}" cy="${sy(currentSun)}" r="7" fill="#ffcc19" stroke="#fff" stroke-width="2"/>`}${Array.from({length:5},(_,i)=>{let t=start+i*86400000/4;return `<text x="${x(t)}" y="${h-10}" text-anchor="${i===0?'start':i===4?'end':'middle'}">${this.time(t)}</text>`}).join('')}</g></svg>`;
  const body=`<ha-card><header><div><h2>Okamžitý výkon</h2><span class="subtitle">Posledních 24 hodin · Žitenice</span></div><button class="expand" aria-label="${this.expanded?'Zavřít zvětšený graf':'Zvětšit graf přes celou obrazovku'}">${this.expanded?'✕ Zavřít':'⛶ Zvětšit'}</button></header>${this.error?`<p class="error">${this.error}</p>`:''}${!this.updated?'<p>Načítám historii výkonu…</p>':svg}<div class="legend">${[...names,'Slunce · °'].map((name,i)=>`<button data-line="${i}" aria-pressed="${!this.hiddenLines.has(i)}" class="${this.hiddenLines.has(i)?'muted':''}"><span class="dot" style="background:${i===3?'#b88500':colors[i]}"></span>${name}${i<3?' <b>'+this.n(Number(this.h.states[this.ids()[i]]?.state))+' W</b>':''}</button>`).join('')}</div><div class="status">☀ ${this.time(now)} · Slunce <b>${this.n(currentSun)}°</b> · ${phase}</div><details><summary>Noc, soumraky a údaje grafu</summary><small>Šedá: noc · modré odstíny: soumraky · světlá: den. Levá osa: W, pravá: výška Slunce nad horizontem (°), nikoli sklon panelů. Astronomický horizont bez místního zastínění.</small><small>Historie obnovena ${this.updated?this.time(this.updated):'—'} · SunCalc (MIT).</small></details></ha-card>`;
  this.shadowRoot.innerHTML=`<style>:host{display:block;min-width:0}*{box-sizing:border-box}ha-card{display:block;padding:4px;color:var(--primary-text-color);font:14px var(--paper-font-body1_-_font-family,sans-serif)}header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 10px 8px}h2{font-size:21px;line-height:1.25;margin:0}.subtitle{font-size:12px;color:var(--secondary-text-color)}svg{width:100%;display:block;overflow:hidden}.legend{display:flex;flex-wrap:wrap;gap:2px 10px;justify-content:center;padding:4px 6px;margin:0}button{font:inherit;font-size:12px;border:0;border-radius:6px;padding:6px 2px;background:transparent;color:var(--primary-text-color);cursor:pointer}.expand{padding:8px;background:var(--secondary-background-color);white-space:nowrap}.muted{opacity:.35}.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px}.status{text-align:center;padding:7px;font-size:13px;line-height:1.3}details{margin:0 10px 8px;color:var(--secondary-text-color);font-size:11px}summary{cursor:pointer}small{display:block;line-height:1.5;margin-top:6px}.error{color:var(--error-color)}dialog{position:fixed;inset:0;width:100vw;height:100dvh;max-width:100vw;max-height:100dvh;padding:0;margin:0;border:0;background:var(--card-background-color,#fff);color:var(--primary-text-color);overflow:auto}dialog ha-card{border:0;border-radius:0;min-height:100%}dialog::backdrop{background:#111a}@media(max-width:500px){h2{font-size:19px}.legend{justify-content:flex-start;column-gap:12px}.legend button{font-size:11px}}</style>${this.expanded?`<dialog aria-label="Zvětšený graf výkonu">${body}</dialog>`:body}`;
  this.shadowRoot.querySelector('.expand').onclick=()=>{this.expanded=!this.expanded;this.render()};
  const dialog=this.shadowRoot.querySelector('dialog');if(dialog){dialog.oncancel=e=>{e.preventDefault();this.expanded=false;this.render()};dialog.showModal();}
  this.shadowRoot.querySelectorAll('button[data-line]').forEach(b=>b.onclick=()=>{let i=Number(b.dataset.line);this.hiddenLines.has(i)?this.hiddenLines.delete(i):this.hiddenLines.add(i);this.render()});
 }
}
if(!customElements.get('jarvis-power-sun'))customElements.define('jarvis-power-sun',JarvisPowerSun);
