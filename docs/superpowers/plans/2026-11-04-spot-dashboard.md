# Spot dashboard implementation plan

Goal: implement approved Spoty screen without changing inverter operation.
Architecture: isolated custom Lovelace element with live HA state, read-only market chart and explicit readiness gates. Existing energy module loads the element; dashboard appends one view. Private inverter baseline stays on Green and never enters public Git.

- [ ] Capture immutable exposed inverter settings with unavailable entries explicit.
- [ ] Build live responsive house/battery/grid card, direction-specific animations, current purchase/sale prices separated from raw OTE, explicit missing tariff.
- [ ] Show three modes and manual actions with honest preparation status; do not simulate successful control. Physical execution remains blocked until contract and export limits verified and controller implemented/tested.
- [ ] Show daily measured import/export; week/month and financial settlement need interval accounting. Never substitute today's price for historical prices.
- [ ] Verify null/stale telemetry, zero/negative prices, power directions, inactive mode, narrow viewport. Publish source, deploy CAS, read back exact content.

Remaining activation requirements: verified settlement fees and price basis, allowed export power, complete operational rollback mapping, actual tested control service, forecast calibration and interval ledger. No AI active claims before these exist. Preserve existing dashboard and firmware.

Owner steering: for now both purchase and export use TEST OTE without fees/VAT.
This removes the tariff dependency for simulation, not the unverified actuator mapping.
Implemented: live telemetry/directional flow, market dates, current TEST prices, daily energy counters, explicit unavailable period/financial aggregates, disabled unimplemented physical controls. Snapshot verified on Green; no settings written. Source validation passes. Browser harness prepared; runtime browser download unavailable so visual live verification outstanding.
