# Reliable operations implementation plan

Approved spec: the user's full operations table and six improvement requirements, 29 October2026. Execute inline using executing-plans, TDD and final independent review. Existing linked worktree is isolated and clean. Existing core stays2026.6.4.

1. Bounded backup deletion with metadata CAS, protected/newest keep guards and verified absence; disk-space read and retention preview (never blanket purge). Pre-backup failures must be known failures, not ambiguous restarts.
2. Persistent SQLite deployment lease across chats; all Admin mutations honor it. Prepared bundle preview, source revision, expected file revisions, file diffs and restart requirement; durable apply/readback and explicit CAS rollback.
3. Heating parameters separated from code via validated persisted service, corresponding bounded Admin operation; maintain current safe defaults. Runtime version and model/source versions explicitly distinguished.
4. Simulator and repeatable tests; containerized HA test fixture plus deployment instructions. Check actual remote runtime support before claiming hosted HA. Odladeni currently exposes PHP only; proc_open=false, no authenticated container/SSH tool available.
5. Source publish/update, free approved backups, activate heating fix and current integration in one Core restart, then check bridge/voice/heating. Update manifest and checkpoint with deployed vs prepared status.

Constraints: no secrets or personal voice models in Git; no arbitrary shell/proxy, no security bypass; no extra Core/OS upgrades; preserve unknown request IDs and reconcile. Deleting four named backups already authorized; first36c1e560 removed through existing logged-in UI and confirmed absent. Browser then lost session; do not invent credentials. Remaining91ee007c/fd90919a/e7b028f1 should use new API after update.

## Execution ledger

Task1 complete: backup/delete metadata guards, storage and preparation diagnostics; three live deletions verified.
Task2 complete: lease/preview/apply/rollback, live activation and file rollback proof verified.
Task3 complete: persisted validated heating configure, CAS under decision lock,300→301→300 live without restart.
Task4 simulation/CI complete; persistent hosted HA blocked by missing host administration. Compose fixture prepared; no fabricated hosted success.
Task5 complete:3.12.0 updated, heat1.1.0 activated, voice/heat readback and settings restored.
Ruling: retention remains preview-only because authorization names four exact deletions, not future arbitrary backup purge.
Ruling: deployment ownership coordinates Admin routes; independent updater/manual UI remain outside the lease and are documented.
Ruling: no claim of arbitrary Python hot reload; ordinary parameters use configure, code uses real activation.
Independent review: operations_review; all important findings addressed, final fixes covered by regression/scenario tests,203 addon+21 heating passing and CI green.
Deferred infrastructure: actual Docker/VM host access is unavailable through current PHP-only Odladeni connector; no extra authentication or arbitrary shell proxy introduced.
