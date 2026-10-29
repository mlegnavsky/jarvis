# Solar heating — deployed 2026-10-29

Source: managed_sources/solar_heating, native HA integration version 1.0.0. The visible automation Jarvis solární topení calls the controller every 15 seconds. Sensor/state events also reevaluate safety immediately. The automation switch disables automatic heating; manual temperature and SOC safety remain active.

Shared sensor sensor.aqara_temp_humidity_sensor_t1_teplota is the child-room sensor despite its historical Jídelna friendly name. Child switch aqara_smart_plug_eu, living aqara_smart_plug_eu_2.

Time-weighted rolling PV mean: child starts above1200W, stops below1000W; living starts above3500W, stops below3100W. Thermal demand enters below22C and exits at23.5C. Minimum automatic off-time300s; living waits120s after confirmed child turn-on. New automatic loads require actual PV-minus-house-load headroom950W/2200W and no battery discharge above300W. These headroom values conservatively cover the observed roughly900W/2150W heaters.

Full-battery override enters atSOC>=90%, exits below85%. Manual switch-on ignores solar conditions, stops at23.5C orSOC<=50%, then returns to auto with normal cooldown. Manual off returns to auto. Continuous battery discharge>300W sheds automatic living after120s and child after240s, excluding manual and full-battery heating. Temperature loss fails off, missing energy prevents solar automatic operation.

No mandatory restart warmup. Samples, demand, manual mode and cooldown timestamps are persisted. The average uses available valid recent samples, so the first installation or a prolonged outage can initially have partial coverage; coverage_seconds is exposed in the mean sensor. This avoids the restart wait explicitly rejected by the homeowner.

Live activation job heat-activate-core-20261029 verified at09:35:23UTC on Core2026.6.4, backup94e01687. The solarman integration temporarily reported setup_retry, then recovered automatically at09:37:11UTC. A requested targeted reload was rejected by revision CAS because it had already recovered; no second restart was performed.

At09:37:51UTC the child switch was confirmed on (since09:37:12), reason Ze soláru; living off, reason Čeká na slunce; shared temperature20.29C, PV2297W, average2274.9W, SOC74%, battery power-912W (charging), house load1279W. This verifies a real automatic activation following the homeowner's switch-off. Simulated scenarios cover temperature/SOC limits and clouds; extreme physical temperature/SOC conditions were not forced in the home.

Dashboard: four live status labels across main floorplan and room details; the Automatizace view has the visible heating automation, statuses, mean, shared temperature, SOC and manual switch controls. Existing voice automations are grouped as legacy fallback; their conditions inhibit them while the current voice adapter is active. Original voice automation actions were preserved. Dashboard structure/readback checked; no visual browser check performed.

Validation:16 heating engine/adapter tests,193 addon tests and5 firmware-native tests passed. Fifteen-minute alternating-cloud simulation yielded one switch change and respected the five-minute off pause. Dashboard patch is idempotent and preserves all views. Services description added after a harmless missing-services.yaml diagnostic; controller services and sensor output were already working.
