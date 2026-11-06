# Energy 1.0.5 — surplus and planned-sale resilience

Review of1.0.4 found two uncovered read-only timeout paths: the periodic battery-sale native audit became generic controller_error, and idle profile/baseline admission reads disabled automatic intent. The diagnostic read_native_program path already records its errors and was not the failing boundary.

A TimeoutError from the periodic battery native audit now records exact typed transport evidence, recomputes current telemetry and runs the existing electrical/market guards before confirmed cleanup. Existing strict recovery requires matching stop identity, no conflicts, confirmed physical stop,30s healthy data and a fresh ordinary native profile. If the timeout crosses the HA deadline, the completed plan is marked deadline rather than resumed. Voltage/current/export/fault/native-conflict and unknown write failures remain fail-closed.

Idle automatic profile/baseline read-only admission timeouts wait for a later cycle without clearing owner intent. No transaction begins until admission succeeds. No write/start failure is swallowed by this path. Surplus uses the existing1.0.4 transaction controller; a dedicated unavailable-control PV regression now verifies its recovery proof.

Verification:761 tests run,741 passed,20 existing optional PHP skips,0failures; release manifest and whitespace checks. Added failures first for battery native timeout, simultaneous export violation, deadline-crossing timeout and idle admission timeout. Actual PV/planned-sale operations were not deliberately started outside their conditions. Private operational receipt records installation separately. History, schedules, native SOC floors, BMS/current protections and watt accounting unchanged.
