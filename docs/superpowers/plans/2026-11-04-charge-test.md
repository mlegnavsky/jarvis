# Manual grid charge implementation
Goal: working bounded test button and restored visual Spoty screen; no export activation.
Architecture: native HA integration with durable transaction journal and readback; frontend explicitly registered as versioned extra module. User starts test. Scope excludes AI trading and contract accounting.
1. Test transaction recovery after partial write/restart, stale/missing telemetry, export guard, repeated start/stop.
2. Implement active-slot charge to at most +5 SOC (max90), at most20A DC, ten minute deadline; preserve zero export mode and every untouched setting. Persist rollback before first write; read back every changed field. Restore on stop/deadline/startup/failure. A powered-off HA cannot enforce software deadline; active slot still bounds inverter program.
3. Create independent visual card with exact house media, active state, OTE prices, buttons, measured flow. Expose service failures. No fake AI or financial totals.
4. Publish source, deploy CAS bundle with config check/restart, verify live integration and buttons without invoking start.

Exact documentation source: https://www.deyeinverter.com/deyeinverter/2026/03/19/BManualSUN-3-12K-SG05LP3-EU-SM220260319en.pdf pp37–39. Program power is discharge limit, not charging limit; DC charging current is constrained instead. Active-slot times are read from real entities. No zero export, safety/BMS, voltage, grid code or rated limit writes. Restore covers fields touched by this test, not a complete firmware backup. Full original baseline restore remains separately unimplemented.
