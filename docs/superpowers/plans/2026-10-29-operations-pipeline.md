# Reliable operations implementation plan

Approved spec: the user's full operations table and six improvement requirements, 29 October2026. Execute inline using executing-plans, TDD and final independent review. Existing linked worktree is isolated and clean. Existing core stays2026.6.4.

1. Bounded backup deletion with metadata CAS, protected/newest keep guards and verified absence; disk-space read and retention preview (never blanket purge). Pre-backup failures must be known failures, not ambiguous restarts.
2. Persistent SQLite deployment lease across chats; all Admin mutations honor it. Prepared bundle preview, source revision, expected file revisions, file diffs and restart requirement; durable apply/readback and explicit CAS rollback.
3. Heating parameters separated from code via validated persisted service, corresponding bounded Admin operation; maintain current safe defaults. Runtime version and model/source versions explicitly distinguished.
4. Simulator and repeatable tests; containerized HA test fixture plus deployment instructions. Check actual remote runtime support before claiming hosted HA. Odladeni currently exposes PHP only; proc_open=false, no authenticated container/SSH tool available.
5. Source publish/update, free approved backups, activate heating fix and current integration in one Core restart, then check bridge/voice/heating. Update manifest and checkpoint with deployed vs prepared status.

Constraints: no secrets or personal voice models in Git; no arbitrary shell/proxy, no security bypass; no extra Core/OS upgrades; preserve unknown request IDs and reconcile. Deleting four named backups already authorized; first36c1e560 removed through existing logged-in UI and confirmed absent. Browser then lost session; do not invent credentials. Remaining91ee007c/fd90919a/e7b028f1 should use new API after update.
