# Managed workspaces and local rebuild acceptance — 2026-10-27

Main3.8.0 deployed through the independent gateway1.0.0. Update741295f155d64d8b9e19f508ef161f3b verified, backup5d05e82d. CI40483564172: tests and both build/startup jobs successful;159 tests passed locally and in CI. Manifest checks and diff checks passed. Independent review found self-rebuild protection and move-restore gaps; both were corrected before publication, re-reviewed and tested.

## Actual Green operations

-addons/share/media mounts all available. Native mount type local_apps is mounted at the stable internal /addons path; no host/Docker privileges added.
-Read all4 managed source files of local Jarvis Core0.1.0. Fingerprint d9a84484502dc4297ac0881c7ab8ede61d600dc4dfccb93717ca04be0885c4e0. Snapshot in managed_sources/jarvis_core/source.json matches original file bytes/modes/hashes and contains no private options.json or runtime credentials.
-ws-proof-write/move/move-restore/delete/restore/cleanup-20261027 all verified against share/jarvis_workspace/probe.txt. Both single-file restore and dual-snapshot move restore were exercised. Probe files removed afterwards.
-ws-upload-begin/chunk1/chunk2/finish/cleanup-20261027 exercised a real2-block PNG upload into media, verified published SHA256 and removed the file. No media playback requested.
-Created temporary local source project jarvis_management_probe with no API/hardware/network privileges and manual boot. Native store detected it.
-local-probe-install-20261027 verified stopped0.0.1; backup1647231c.
-local-probe-code-change-20261027 changed the Docker CMD in source. New managed-source fingerprint450cf0e677c4e8a873baf4802f2b91bcb7c36dbc621bee211944f890b90d545f.
-local-probe-rebuild-20261027 verified native rebuild after source change, version0.0.1 and stopped state preserved; backup bca27f68. It was never started. Application functionality deliberately remains application_functionality_verified=false.
-local-probe-uninstall-20261027 verified installed=false; backup8ea73c24. Both source files removed and store reloaded. Final installed count12; source inventory contains only the original4 Jarvis Core files.

No household device command, audio playback, Core stop or existing-app removal was used. Local Jarvis Core was inspected, not changed/rebuilt/uninstalled.

## Practical limits

Text edits256KiB, staged binary uploads8MiB with128KiB chunks. No recursive directory deletion, private credential-file access, host shell, writable system partition or universal firmware deployment. Managed source fingerprint excludes disallowed/hidden files; it is not a hash of arbitrary Docker context contents. A source rebuild is separate from a functional application test. Existing app/config backup and file before-images are different recovery scopes; both must be considered when returning a code change.
