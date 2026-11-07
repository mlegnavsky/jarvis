# Solar supervision implementation plan

**Goal:** Extend the approved automatic solar supervision with fresh measurement evidence and sustained operation checks, visible in Spoty.
**Architecture:** Extend the existing read-only Supervisor; no controller commands, register writes or new polling of the inverter. Use existing reported timestamps, controller state and passive HA state reads. Publish compact evidence and a bounded recent incident list.
**Constraints:** Preserve owner intent, weather reserve, native protections and all existing control code. Internal grid evidence is not independent proof of connection-point export. Native Load zero in Export First is not alone a fault.
**Review focus:** Stable values use last_reported; stale/future/nonfinite measurements never confirm flow; charging is monitored despite sale health excluding charging; transient deviations need90s persistence; cleared faults and operation changes reset timers.

- [ ] Add regression tests for freshness, mode explanation, sustained missing export/charge and notification deduplication.
- [ ] Extend supervision.py with passive measurement evidence, mode/result explanation and bounded incidents; preserve evaluate() existing alerts.
- [ ] Add an expandable Spoty card using textContent and tables; label stale reports and meter uncertainty.
- [ ] Run Python suite and relevant Node checks; publish sanitized code with expected remote HEAD.
- [ ] Acquire deployment lease, prepare CAS bundle, back up/activate, verify exact files and live supervisor version; restore pre-existing automatic intent through existing confirmed command if maintenance pauses it.
