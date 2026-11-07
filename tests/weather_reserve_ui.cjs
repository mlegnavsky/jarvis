const assert=require('node:assert/strict');const {reserveView}=require('../managed_sources/spot_hub/hub.js');
const sales={weather_reserve:{required_soc:75,forecast_day:'2026-11-08',forecast_pv_kwh:14.7,conservative_pv_kwh:11.76,house_daily_kwh:8,house_with_margin_kwh:10,capacity_kwh:23.552,quality:'estimated',load_quality:'bootstrap_or_partial',forecast_issued_at:'2026-11-07T14:00:00+01:00',forecast_age_seconds:120,reason:'Zásoba pro dům',intervals:[],recent_decisions:[]},sale_floor_soc:75};
assert.match(reserveView(sales,true).summary,/75 %/);assert.match(reserveView(sales,true).production,/14,7/);assert.match(reserveView(sales,true).house,/10,0/);assert.match(reserveView(sales,true).quality,/odhad/i);assert.match(reserveView(sales,false).summary,/čerstvá/);assert.match(reserveView({},true).summary,/Čekám/);
console.log('Weather reserve UI: live reserve, source quality, house cushion and stale state PASS');
sales.weather_reserve.forecast_days=[{day:'2026-11-08',forecast_pv_kwh:20,conservative_pv_kwh:16},{day:'2026-11-09',forecast_pv_kwh:4,conservative_pv_kwh:3.2}];
assert.match(reserveView(sales,true).day,/2026-11-09/);
assert.match(reserveView(sales,true).quality,/20 %/);
