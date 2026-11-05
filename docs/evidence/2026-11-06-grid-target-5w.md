# Owner5W grid-target experiment — 6 November2026

Owner explicitly requested changing the normal grid-import target to5W everywhere and deploying together. Source27f4256a05b3df7f3c0cba3f5b8cc5ede78aca0b introduces GRID_TARGET_W=5 in native_zero_target.py. Existing guarded command/function names are preserved for compatibility but now write only104=5. Baseline expected readback, snapshot target, confirmation and policy use5. Old0W proof cannot confirm5. Ordinary idle/start automation now restores5; existing entity ID jarvis_bezny_odber_0_w is intentionally preserved and its friendly label is5W. Other power caps, reserve60%, mode/charge controls, delays and historical records were not changed.

Full pinned suite580tests passed,20skipped; diff and release checks passed. Independent review found one stale test expectation0, corrected to5 before publication; no blocking production issue found.

Combined deployment grid5066-plan-20261106/grid5066-apply-20261106 verified active_verified2026-11-05T23:25:35.668761UTC (6November00:25:35local), backup263a3f4e, Core2026.6.4. Four source files and automations.yaml were CAS-bound in one restart bundle. Other automation entries were preserved semantically.

Guarded command owner-grid5-native-20261106 was accepted by the inbox and FAILED its physical proof: before20, requested5, native reads[5,5,5,5,20,20,20]. First delayed single/bulk/single group at1793921160.9698215 returned5/5/5; second at1793921166.2645447 returned20/20/20. Thus5 was briefly observed and did not remain. No retry/rewrite storm and no negative value were used.

Independent native program snapshot23:26:26.014670UTC confirmed register104=20. Runtime23:26:55UTC: requested target5, grid_target_confirmed=false, automatic=true, inhibited=false, healthy=true, empty controller error. Actual grid14W, batterySOC71. State inventory23:27UTC: ordinary5W automation on, automatic-sale switch on. It is incorrect to claim sustained5W operation, or to claim all issues solved. This evidence alone still does not identify the writer or firmware behavior responsible for returning20. All known inspected HA target/restoration paths now request5.

Deployment lease released via grid5066-release-20261106, verified. Keep the owner-requested5W configuration for the experiment; do not silently restore0 or relabel actual20 as5. Existing scheduled sales stay enabled.
