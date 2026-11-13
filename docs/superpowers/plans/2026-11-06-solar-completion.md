# Solar operation completion

Goal: complete the five owner-approved items: capacity basis, sale-cycle verification, near-full PV surplus, cash/energy overview, and fault notifications.

Architecture: preserve the existing native controllers, fixed SOC60 protection, price gates, current175A and grid cap9300W. Add a shared conservative capacity/house-data adapter, read-only supervision and clearer native cards. Deploy one CAS bundle and verify a bounded500W/5min battery cycle only with fresh positive price/health/energy admission. No invented sunlight or historical physical acceptance.

Authorization: owner explicitly requested all five items, resolving obstacles, execution and deployment without further check-ins. Existing scheme is retained; no new design choice requires an owner decision.

## Constraints and review focus
- Core2026.6.4 unchanged. No battery capacity setting or electrical limits changed.
- Nominal basis comes from configured460Ah at51.2V; it is not a measured physical/SOH guarantee.47kWh remains unverified.
- Missing capacity/house/price data must not increase battery sale; native Load0 during ExportFirst is not valid house consumption.
- Cash balance is sale proceeds minus purchase cost, not full investment/degradation profit; partial accounting stays visibly partial.
- Notifications cannot block protective control or generate repeated pushes. Stop/failed export/stale measurements remain visible.
- Startup unavailability, no sunlight, insufficient reserve, and a legitimately waiting sale block are not failed sales.

## Tasks
- [x] 1. Shared capacity and canonical house reading: RED tests, minimal adapter + call sites, GREEN. Publish configured basis and energy estimates.
- [x] 2. Read-only supervision: RED tests for stale data, stuck stop, no export, setting mismatch, verified/full cycle and deduplication; GREEN. Persistent HA notifications, current sensor/runtime and resolved cleanup.
- [x] 3. Financial/energy cards: RED tests preserving unknown/partial accounting; add energy totals and cash balance; GREEN. Near-full PV production stays price guarded and battery-discharge protected; regression verification rather than an unrelated algorithm rewrite.
- [ ] 4. Full relevant suite, fresh independent code review, one fix pass if needed. Publish reviewed source with expected HEAD, CAS deploy once after storage/idle preflight; independent exact readback/runtime confirmation.
- [ ] 5. Physical bounded battery cycle if admission succeeds; record start/export/reserve/native expiry/full restoration. PV98% physical acceptance can only be recorded when those real conditions exist. Persist acceptance report/alerts to observe the next natural opportunity without claiming it already happened.
- [ ] 6. Update OPEN-WORK and durable evidence with exact active capabilities and physical limitations. Final user report must not say all real conditions passed when they did not.

Progress ledger: work/finish-solar-20261106, baseline local34168b8 plus already-published0.6.7 source patch; remote publication uses fresh remote-tree base so intervening documentation is preserved. Live baseline05:51UTC idle/healthy/automatictrue, SOC63,460Ah, sensor23.3kWh. Finance live with estimate quality and historical gaps.


Review ledger: independent reviewer solar_completion_review reported three important findings. Stale configured capacity was reproduced RED then blocked at600s (planning/control); intentional charging no longer causes false measurement alarms (RED→GREEN); missing house data now emits its own diagnostic (RED→GREEN). Monitor failure was regraded from minor to important because stale-ready hides a failed watchdog; sensor/UI error fallback was reproduced RED→GREEN. No deferred review findings.

Live test exposed a pre-write expired-buffer error when a request was made52s into the last minute before a5min boundary. Added RED→GREEN test and a common next_native_start with at least60 real seconds, used by plan and admission; no guard weakened. Final suite602 tests passed20 skipped; archive8 passed.

Ruling:460Ah at51.2V is configured nominal23.552kWh, not physical capacity proof; no battery settings changed. Canonical house history starts from real new samples; old raw Load is not relabeled.

Deployment blocker: latest host storage1.4GiB, mandatory backed-up restart requires2GiB. No backup deletion authorized/performed. Retention preview preserves newest3 and all protected; candidate00605e96 is793.65MB from5Nov19:44UTC, enough to pass preflight if owner authorizes exact deletion. Source and CAS plan will be prepared before asking.


Physical acceptance, 2026-11-06: bounded manual500W test (transaction1793945543348156055),07:15–07:20 Prague, SOC63 throughout. Real export500–520W was observed54 times. Native end was NOT observed: export continued after07:20 and HA protective stop ran at07:21. Restoration initially retried register167, then completed with original TOU/current175A/cap9300W independently read back. Latest06:30UTC runtime idle, healthy, automaticFALSE; owner-authorized automatic sales deliberately disabled after failed expiry. Do not re-enable or claim production acceptance. Native weekday mask33 matches Friday in installed profile; root cause remains unresolved.

Safety follow-up: reproduced RED that deadline failure retained battery_verified and automatic. Shared acceptance now marks failed native expiry, startup invalidates old proof and handler revokes battery verification/inhibits automatic. Supervision exposes cycle_failure. Full suite603 tests passed20 skipped; manifests/syntax and diff-check passed. Previous prepared plans finishsolar-core-plan-20261106 and finishsolar-root-plan-20261106 are SUPERSEDED by this safety follow-up and must not be applied; prepare fresh plans from latest source after exact backup deletion approval. No runtime source deployed. Backup deletion not attempted.

Activation ledger06:43UTC: owner independently removed backups; fresh3.8GiB. Core v2 apply wrote source and createdfcb10fc6, then timed out during slow startup. Reconciled with exact15-file readback and distinct unchanged-automations verification plan, active_verified for sales0.7.0/finance1.1.0/supervision1.0.0/archive1.2.3. Root v2 apply verified. No apply replay, second restart or device export. Physical native failure and1W->20W remain unresolved; automatic remains inhibited. See docs/evidence/2026-11-06-solar-completion-070.md. Overall five-item goal is only partially accepted.
