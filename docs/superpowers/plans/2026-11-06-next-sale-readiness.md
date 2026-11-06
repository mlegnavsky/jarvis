# Next sale readiness implementation plan

> For agentic workers: execute sequentially with tests and final independent review.

Goal: show an honest ready/waiting tomorrow price plan and retain it across midnight.
Architecture: pure upcoming_plan.py validates full local-day price coverage and reuses choose_daily_block; sale_setup persists/promotes separately from completion; existing hub renders one next-plan paragraph.
Tech stack: existing Python HA and plain JavaScript.
Spec: ../specs/2026-11-06-next-sale-readiness-design.md

Constraints: no inverter/current/SOC/schedule changes; configured120minute window unchanged; net prices; no fake ready on missing data.
Review focus: midnight promotion, stale/corrected quotes, duplicate/missing quarters,23/25hour days, completed-day reentry.

- [x] Add failing pure tests for optimal tomorrow window, incomplete/duplicate data, no positive window, DST and prepared-block quote validation; implement pure helper and verify.
- [x] Add failing adapter tests for completed-day preserving tomorrow plan and midnight promotion; persist next_plan separately and expose it in snapshots; verify no sale starts early.
- [x] Add DOM readiness/waiting tests, add next-plan paragraph and cache revision; verify Python suite and UI suites.
- [ ] Review, publish exact source, deploy with CAS and backup, restore previous automatic intent and verify live readiness plus small flow. Update private receipt and open work.
