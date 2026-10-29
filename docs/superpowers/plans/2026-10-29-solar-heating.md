# Solar heating implementation plan

Goal: deploy the user-approved shared-temperature solar heating and live floorplan modes.
Architecture: native HA integration with a pure decision engine, persistent five-minute samples and mode/cooldown state, event-driven manual recognition and 15-second reevaluation. No mandatory restart warmup; use valid retained samples or available current data. Native switch state is always read back, never assumed.

Approved specification: shared child-room sensor; 22/23.5C thermal hysteresis; PV five-minute time-weighted mean 1200/1000W child and 3500/3100W living; 300-second minimum automatic off time; living starts at least120 seconds after child. Full-battery exception enters90%, exits below85%. Manual on overrides PV until23.5C orSOC<=50%, off returns auto. Auto battery-discharge protection>300W for120s sheds living, after240s sheds child, exempt manual/full-battery. Missing temperature fails off; missing energy disables solar auto. Restart imposes no new timer. Check actual house headroom before adding loads. Preserve state/cooldowns over restart.

- [ ] Write scenario tests for thresholds, alternating clouds, restart continuity, manual termination, missing inputs, sequential shedding and adequate headroom.
- [ ] Implement pure engine and HA adapter using Store, state/service events and native switch services. Expose live reason sensors and bounded manual/auto/toggle services.
- [ ] Add state labels beside radiator icons in every applicable floorplan; add heating controls/details.
- [ ] Run scenario and existing tests, validate deployment configuration, publish source through Git, write via CAS bridge and activate once.
- [ ] Verify live sensors, no collision with existing automation, actual source/mode, dashboard readback; record evidence.
