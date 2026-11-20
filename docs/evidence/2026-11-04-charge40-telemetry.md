# Charge 40 A and telemetry — 2026-11-04

User authorized increased charging current, temperature display and investigation of stuck data. Live inventory 16:54:56 UTC: grid import 18 W, battery discharge 261 W / 4.92 A, SOC 42%, inverter temperature 36.6 C, battery temperature value 13.5 C unchanged since 16:36:40 (inventory lacks last_reported). Grid current setting 40 A, max charge 100 A. Controller idle. No new physical test started.

Root cause: existing test plan caps current at min(20, previous setting); UI uses last_updated when browser state lacks last_reported, falsely aging unchanged PV zero and suppressing whole flow status. OTE sensor changed at 16:45 UTC and updated 16:54:47, so backend price not frozen.

Prepared 0.3.0: 40 A capped by previous setting and configured maximum, battery temperature test guard 0 <= T <45 C, stale temperature/limits abort, original 10 min/+5pp/90% restore retained. This is a conservative test cutoff, not manufacturer maximum. Report backend last_reported telemetry for PV/load/grid/battery/SOC/temperature/current/voltage; UI consumes it and shows temperature/current/voltage. Existing slider/current quarter and CEZ helper preserved.

Validation: 13 controller tests pass including temperature abort and lower configured cap; chart and card tests pass; Python compile and JS parse pass. Files staged and verified through charge40-stage-engine-py, charge40-stage-xxinitxx-py, charge40-stage-manifest-json, charge40-stage-card, charge40-stage-config. Configuration module URL bumped to v=0.3.0-telemetry. Activation pending restart; do not report live 40 A or new UI yet.

Storage has 1.9 GiB free; backup requires 2.0. Retention preview identifies old unprotected backup b74d6651 (2026-11-04T08:11:00Z, 732.67 MB), revision f68ca1d1bceb45434c17aa48fb3df6c505ee974d23429dbf104235b19d9b1c4a. Deleting it would preserve three latest administration backups and all protected backups. No deletion authorized/performed yet. Ask user approval for this exact irreversible deletion, then fresh metadata check, deletion, storage check, one backed-up restart, runtime/UI/charge verification. Do not bypass restart backup guard.
