# Solar0.7.0 deployment and physical limits —6 November2026

Source:07371e8bcb4da707ce59ed9fc82dc9b7a669c400 on feat/jarvis-addon. Owner removed backups independently; fresh preflight3.8GiB and no deployment lease. No backup deletion performed by this work.

## Actual activation
Core bundle finishsolar-v2-core-plan-20261106, apply finishsolar-v2-core-apply-20261106 created backup fcb10fc6, wrote13 files and passed configuration validation before restart. The apply timed out upstream during slow Core startup (job unknown, plan activation_failed). Do not replay it. Supervisor log confirms one restart; Core remains2026.6.4. Independently read fresh runtime0.7.0/finance1.1.0, then a distinct verification plan reloaded unchanged automations.yaml without another restart:
finishsolar-v2-runtime-verify-plan-20261106 / finishsolar-v2-runtime-verify-apply-20261106 = verified, active_verified,06:43:13UTC.
Checks: sales idle/version0.7.0, finance balance1.1.0, supervision1.0.0/error (expected unresolved alerts), archive1.2.3/ready.
Root plan finishsolar-v2-root-plan-20261106 / apply finishsolar-v2-root-apply-20261106 verified/file_written. All15 original deployment files independently read back byte-for-byte, including root/Spoty/sales/shared cash cards and expired diagnostic automation cleanup. No authenticated rendered UI check available.

## Active capabilities
- Shared configured nominal capacity460Ah*51.2V=23.552kWh. Reported sensor23.3kWh separately shown. Physical47kWh/SOH/usable capacity not verified; no capacity setting changed. Reject stale configured capacity (>600s).
- Canonical fresh house measurement used for control/planning and private10s archive; native Load0 in ExportFirst is not relabeled as house0. Fresh06:43UTC house200W.
- Energy totals and cash balance (sale receipts minus purchases) on dashboards; partial/gaps remain visible, no whole-investment profit claim. Finance1.1.0 archive_loaded=true/history_error empty; historical gap2285.86s remains, estimates not final billing.
- Supervision publishes native deadline/failed cycle, stale measurements/missing house, no export, stuck cleanup, control failure, invalid capacity and requested/actual grid mismatch. Deduplicated persistent notifications delivered (pending0,error empty).
- Failed native deadline now revokes battery_verified and inhibits automatic, also on restart. Latest idle/healthytrue, activefalse, automaticfalse, inhibitedtrue, battery_verifiedfalse; no charging transaction active.

## Actual failed native acceptance
Manual transaction1793945543348156055,07:15–07:20 Prague,500W/minSOC60. Export500–520W sustained54 samples; SOC63. Export continued after native07:20 boundary. HA protective stop at observer deadline07:21 restored full native program; an initial register167 restore needed retry, then all originals independently confirmed.
Proof observed=true, native_expiry_observed=false, stop_verified=true. This is NOT an accepted full autonomous cycle. Automatic sales deliberately disabled and remain blocked. Current175A, restored cap9300W and ordinary Zero Export To CT unchanged.
Near-full PV>=98% positive-price policy remains implemented, but conditions did not occur and automatic is paused; do not claim live near-full PV acceptance.
Native requested normal grid target1W still reads20W. No exact origin/cause established; read-only discrepancy alert active. Do not claim fixed firmware or a competing writer.

## Verification
Full603 tests passed,20 skipped; archive8 passed; manifests/syntax and diff-check passed before source publication. No source changes since passing verification. New native timing regression and failed-native-end regression had RED-to-GREEN evidence. Three independent review findings plus monitor-error visibility fixed before deployment.

## Remaining work
Identify why correct native schedule does not terminate battery export; manufacturer manual expects TOU/SOC limits, installed profile time HHMM/mask and capacity mode match, no proven cause yet. Preserve guards; no production unlock without another successful bounded native acceptance. Investigate1W->20W reversion separately. Physical capacity47kWh and near-full PV behavior remain unverified.
