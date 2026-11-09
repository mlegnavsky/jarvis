# Radiator history controls — 9 November 2026

Owner requested explicit controls in the existing history window after observing long-hold navigation on the phone. Revised UI uses four native radiator state-icons with existing toggle tap and history navigation hold. This avoids dependence on a cached custom module's gesture. The two existing radiator history subviews receive an explicit “Zapnout topení ze sítě” action (set_mode grid_manual, correct room), “Vypnout radiátor” action (set_mode off), current heating status, child-room temperature24C and battery reserve30% information. Both ON and OFF actions remain available; off can cancel a pending command.

No backend/controller/inverter setting change. Grid-only admission and24C stop remain runtime1.3.0. Solar automatic21/22 and native battery30 reserve unchanged. Existing history graph and logbook remain after controls. A later client refresh cannot cause long-hold direct activation because radiator elements now use HA's native state-icon, not the cached custom class.

Validation:3 patcher tests passed; actual255529-byte dashboard parsed with all !include references preserved; exact semantic comparison confirmed only four radiator element types/custom-only fields and six added cards differ. Idempotence confirmed. Manifest/diff checks pass. Native HA perform-action syntax and service data use the installed1.3.0 contract. No physical heater commands or artificial temperature changes performed. No iPhone visual acceptance claimed.

Deployment: pending supported CAS single-dashboard bundle, activation none, no Core restart. Exact receipt to follow.

Verified deployment: heat-history-apply-20261109 state verified, phase file_written, activation none. Exact fresh dashboard readback matches generated output; revision cb99537850060f8bdcac2ab40885066453c49daf85161b757f48f4fa974cfa00. Source083f4c1fd6c1c3ff76478d41e358b7e9cc38ca78. No Core restart, backend changes or physical heater commands. Client must refresh dashboard to fetch native radiator icons and history cards; actual phone rendering remains owner's acceptance.
