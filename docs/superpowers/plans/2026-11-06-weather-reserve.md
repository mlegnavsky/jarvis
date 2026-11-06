# Weather Reserve Implementation Plan

**Goal:** HA autonomously sets scheduled battery reserve and explains it in Spoty.
**Architecture:** Pure reserve module + durable read-only adapter; existing controller consumes effective floor; existing weather feed supplies GTI; expandable hub displays report.
**Tech Stack:** existing Python HA integrations, vanillaJS.
**Spec:** docs/superpowers/specs/2026-11-06-weather-reserve-design.md

## Global Constraints
Keep hardware protections/native30%/owner OFF, selected business window and recovery gates. Capacity23.552kWh; estimated bootstrap factor0.80546;20% forecast haircut;25% household cushion;8kWh minimum household bootstrap. No battery sale on missing/stale forecast. No future storage credit.

## Review Focus
Wrong forecast day, stale/future/missing rows, DST/timezone, high actual household load, active-sale floor regression. Each has pure/adapter tests. Test tiny export/PV independence and explicit owner floor.

### Task1 Pure forecast/reserve and load adapter
- [x] Write failing tests for Sunday-after-Saturday reserve75, poor/unknown forecast100, sunny60, weak90, high load floor, owner floor, timestamps/DST and no mutations.
- [x] Implement weather_reserve.py calculate_reserve(weather,block,now,capacity_kwh,daily_house_kwh,owner_floor); weather_reserve_setup.py durable local load sampling and snapshots for business block.
- [x] Extend weather request GTI/tilt45/azimuth-45; preserve GHI/history contracts.
- [x] Run pure and adapter regressions.

### Task2 Control integration + monitoring
- [x] Failing adapter regression: computed floor passed to choose/start/size; higher floor stops active automatic sale, lower never weakens active record.
- [x] Wire through sale_decision,battery_size,automatic start/report; preserve manual/commission and PV gates.
- [x] Add expandable weather reserve panel and DOM regression for values/stale/source/no passive writes.
- [x] Run full existing Python suite and relevantNode suites; review diff.

### Task3 Publish/deploy/verify
- [ ] Publish all source with expected Git HEAD. CAS read each exact live file; acquire lease and check storage/active state.
- [ ] Deploy coherent static/backend bundle with required backed-up activation. Poll same job; reconcile unknown instead of retry.
- [ ] Exact readbacks/runtime versions, owner intent, live next-day report and browser UI; durable receipt and release lease.
