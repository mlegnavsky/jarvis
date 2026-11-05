# Energy sales implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver PV-surplus selling, guarded battery selling, manual mobile controls, quarter-hour planning, and durable historical evidence.

**Architecture:** Extend the existing native spot-control component with separate pure policy, persistent journal, and a serialized sales controller. Preserve the existing charging test and enforce mutual exclusion. Use native inverter export/SOC limits, verified readback, and the existing private energy archive. First prove PV-only export at low power before enabling the full automatic policy.

**Tech Stack:** Python stdlib/SQLite, native Home Assistant 2026.6.4 services and entities, YAML Lovelace, existing authenticated PHP archive. No new cloud automation runtime.

**Spec:** docs/superpowers/specs/2026-11-05-energy-sales-design.md

## Global Constraints

- Export contractual 9500 W, operating 9300 W; never restore 9990 W with export enabled.
- Sale SOC floor60%, existing175 A and battery10kW caps; lower BMS/inverter limits take precedence.
- Purchase remains ČEZ5 Kč/kWh; sell OTE converted by dated CNB rate minus0.30 Kč/kWh; no charging from grid for resale.
- Native protection is distinct from an HA timer. Do not claim autonomous full stop without physical evidence.
- Preserve existing voice/dashboard configuration and dirty original checkout. Fresh source baseline521b72c.
- Historical measurements every10s plus immediate control events, private server, durable local queue, no fabricated backfill or deletion.

## Review Focus

- Price boundary at midnight/DST: no stale previous interval or invented future price.
- Concurrent charging/manual/automatic commands: one owner, stop cannot be immediately reversed by automatic tick.
- Missing or stale inverter acknowledgement: no false running state; recover from partial write/restart.
- PV curtailment: measured PV before opening export is not proof no surplus is available.
- Offline controller: retain native export cap and battery SOC floor, disclose continuing PV export if no native timeout.

---

### Task 1: Policy and permanent transaction history

**Files:** create managed_sources/spot_control/sales.py, journal.py; tests/test_energy_sales.py.
**Interfaces:** finite numeric states + UTC timestamps -> price_at(rows, now, rate)/sale_decision(...); Journal(path) -> append(kind,payload), recent(limit), sample/query settlement.
- [ ] Write failing behavior tests: signed price conversion; wrong/missing quarter-hour; reserve60; cap9300; battery current/power; PV surplus can be probed even if measured PV is low; lower price PV overflow vs expensive battery windows.
- [ ] Run `python -m unittest discover -s tests -p test_energy_sales.py -q`; observe missing feature then implement pure policy and journal.
- [ ] Prove journal survives reopening; records unknowns as unknown and cannot silently discard data; quarter-hour settlement handles counter reset without negative energy.
- [ ] Run combined sale/charge tests and commit.

### Task 2: Native controller and readback/stop

**Files:** create managed_sources/spot_control/sale_controller.py; modify __init__.py and engine.py; tests/test_sale_controller.py.
**Interfaces:** SaleController(read,write,save,journal,clock) serialized start/stop/tick; adapter freshness via state.last_reported.
- [ ] Write failing tests: cap/SOC set before export, no charge conflict, no battery discharge for PV-only, stop ordering, partial failure, restart reconciliation, manual override and negative price.
- [ ] Implement PV-only via Zero Export To CT+Solar Sell; battery via Export First+TOU with verified program SOC floor and safe following slots. Every actual write records intent before execution and result after readback.
- [ ] Add HA services enable_auto/start_sale/stop_sale/configure_sale; use admin services with bounded schemas, not an arbitrary proxy. Register native configuration Number/Switch entities or a tested mobile form.
- [ ] Persist automatic mode and recovery state, but never resume interrupted manual export blindly. Charging test refuses while sale active and vice versa.
- [ ] Verify real services and simulated I/O failure cases; run sale+charge suite; commit.

### Task 3: Mobile controls and historical archive

**Files:** modify native_view.py; add sale_view.py/number.py as needed; modify energy_archive/__init__.py; tests/test_sale_view.py and archive tests.
**Interfaces:** service start_sale(power_w,duration_minutes); sensor.jarvis_energy_sales status/attributes; archive immediate sample event callback.
- [ ] Write failing tests for form values surviving updates, open not starting sale, running only after measured export, stop visible and disabled/unavailable behavior.
- [ ] Build native subview Vlastní prodej, power/duration selectors, Start/Stop, prices and reason. Explicit connected-timer limitation where appropriate; no automatic dismissal.
- [ ] Capture available inverter sensor/number/select/switch/binary/time states every10s with source timestamps; include sales decisions/settings/events immediately using supported sample records and a durable outbox. Keep existing graph API compatible.
- [ ] Verify restart/outbox retry, private authentication and server ack/readback. Commit.

### Task 4: Planning, commissioning, and live verification

**Files:** tests/test_sale_planner.py; sales.py/controller updates; deployment preparation script and evidence docs.
**Interfaces:** persisted verified PV-only export receipt gates auto activation; pure quarter-hour planner returns reason, budget and bounded target.
- [ ] Write tests for low-data conservative fallback, high-SOC curtailed PV export, expensive battery windows, terminal energy cost, fee, losses/wear, and manual Stop latching.
- [ ] Implement conservative source-backed forecast/history planning; unknown inputs may block battery sale but must not fabricate lost production. Genuine current PV-only surplus may sell independently.
- [ ] Build fresh CAS deployment bundle; native export limit lowered before first PV export. Private transaction history available before writes. Start with0.5kW/3min PV test, measure PV/grid/battery synchronously, then prove stop.
- [ ] Verify firmware/native TOU boundary and outage behavior before battery export. Never label full battery automation active if this is unresolved; present a concrete limitation/decision if needed.
- [ ] Publish exact source via expected-HEAD, checks, backed-up activation, runtime and UI readback. Respect concurrent voice work and avoid unrelated restart/upgrades. Final whole-branch independent review required.
- [ ] Record measured outcomes, implemented vs active status, history earliest date/gaps, remaining real limitations; no claim based only on accepted request.

## Execution rulings

- User explicitly said proceed and no further design approval round is needed; implement in this session. No unrelated delegation; one builder check and a final reviewer are required by this workflow.
- Initial PV commissioning is time-bounded under connected supervision. Permanent automatic activation requires the offline behavior to be resolved explicitly; do not quietly weaken this gate.
