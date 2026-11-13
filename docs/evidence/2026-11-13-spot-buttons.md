# Spot controls — 13 November 2026

Owner requests white inactive buttons, clear Play/Stop state, working controls and repair of standalone grid charging.

Fresh installed charge adapter/engine match production Git sources. Reproduced the exact reported failure offline: while the first standalone charge write is awaited, an ordinary sales poll holds the sales lock; permitted() treats it as competing activity and aborts the charge at the next step. Heating sessions already had an exception. Extended that exception to all owned charge transactions, retaining actual sales-controller and native-clock exclusion and all measurement/temperature/charge guards. Runtime charge adapter version 0.6.10.

Frontend reconciled against the newer installed hub1.3.0 before editing, preserving reserve/forecast/daily monitoring. Hub1.3.1: inactive white, active blue with Stop labels and aria-pressed from fresh backend states; charge status distinguishes starting/running/observed/restoring. Explicit surplus starts PV sale rather than merely enabling the price scheduler. Active PV/manual sale and charge buttons stop the corresponding controller. Stop all attempts both stop_sale and stop_restore even if one fails. No passive rendering writes to devices.

Regression reproduction failed with the exact original ValueError before the fix; 63 charge/poll/heating tests pass after it. Focused pure and DOM frontend tests pass, including real handlers, charge stop and both stop attempts after a failure. Release manifest/syntax and diff checks pass. Full suite initially blocked by missing voluptuous (742 tests,132 errors,20 skips); dependency installation/retry tracked separately. No physical test or native protection bypass.

Deployment preflight: only0.3GiB free, mandatory Core backup requires2GiB. Do not attempt the blocked restart or delete backups without explicit authorization. Existing unprotected partial backups:6c1d23a9 (9Nov21:01 Prague,885.83MB),6a95d478 (9Nov21:55,889.8MB),ea7c8526 (10Nov07:39,868.13MB); keep newest4e460172 (10Nov16:03,914.44MB) and both protected SSH backups. Deleting all three older partial backups would free about2.64GB; fresh metadata/CAS and owner approval required before deletion. This is a concrete proposal, not a deletion instruction.

Frontend deployment and backend activation receipts are recorded below when available. Git publication/file writes are not runtime activation. No successful physical charge/sale claimed.

Deployment receipt: source182d9a4761e4b7491ec371e15853cdb2f08aee83 published on feat/jarvis-addon. spotfix-ui-apply-20261113 VERIFIED/file_written; all three independent readbacks exactly match; HTML loads versioned JS/CSS. Browser/iPhone visual acceptance remains pending refresh. Backend plan spotfix-backend-prepare-20261113 VERIFIED/prepared, revisiona6e8f157cf8071bbeb5ff637772d9dbf770c5d48f1475114d509bbff8d7b1534; NOT applied, no Core restart or backend file mutation. Private receipt jarvis_workspace/spot-buttons-20261113-receipt.json.

Final validation: installed missing test dependencies and set source PYTHONPATH; full suite819 tests OK/20 skips. Updated report-version expectation0.6.9→0.6.10. Targeted174 tests OK; frontend pure/DOM tests OK, including fallback stop after failure. Earlier missing-dependency failures are resolved. No physical start or stop commands issued.
