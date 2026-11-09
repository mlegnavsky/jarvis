# Manual grid heating implementation plan

Goal: three-second hold starts a temporary manual radiator mode below the normal battery limit; stop at shared child-room temperature >=24 C or explicit off. Standard 21/22 C automatic settings remain intact.

Architecture: retain live 1.2.3 fixes; new grid_manual engine state and read-only admission/continuous guard. No inverter settings are written. Admit only with connected grid, normal nonexport mode, all six native programme reserves >= actual SoC, current measurements and no meaningful battery discharge. Above the native reserve the operation is rejected instead of claiming a grid-only source. Fail closed on loss of proof. This specifically supports the owner's actual 30% SoC / 30% native reserve case.

1. Import exact live 1.2.3 adapter/resource/UI fixes missing from remote; preserve existing tests and 21/22 settings. Baseline suite expected green (update stale off-label assertion to actual live copy).
2. Add failing policy tests for SoC30 admission, exact24 termination, missing temperature/grid, persistent manual off, restart state and unchanged ordinary manual limits. Implement Controller.request_grid and optional evaluate(grid_ready,grid_reason) with independent grid_manual state.
3. Add failing read-only guard tests covering source loss, stale data, reserve mismatch and battery discharge. Implement grid_guard.check(states, now) and adapter wiring without inverter writes; publish status and version1.3.0.
4. Add fake-timer DOM tests for3000ms/no early call/cancel/movement/suppressed click, ordinary click and offline state. Implement host-held gesture surviving hass render updates; retain nonheating navigation.
5. Run Python and JS suites/compile/diff validation, independent review, publish with expected remote HEAD. Prepare exact CAS bundle. Activate only through supported backed-up Core restart after disk preflight passes. Observe runtime1.3.0, matching files and retained settings; do not fake24 C physical telemetry.

Deployment blocker found:0.9 GiB free, minimum2.0. No deletion or bypass authorized. Before final activation offer exact obsolete unprotected backups for owner's deletion approval, preserving newest backup. Do not write half a live deployment while restart is blocked.

Execution: tasks1–4 complete,46 Python and3 JS suites green. Review fixes: independent15s watchdog and held-button error render. Disk blocker resolved by owner, fresh3.4GiB; task5 activation in progress.

Task5 complete: supported backed-up restart, active_verified receipt20:07:45UTC; runtime1.3.0 forboth rooms/UI ready, all7files exact and unchanged21/22settings/native30reserve. No physical24C test.
