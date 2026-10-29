# Jarvis laboratory and archives

Production source: `feat/jarvis-addon`. Plesk source: `lab/plesk-bootstrap-20261029`, document root `/laborator.odladeni.cz`. Never deploy the production tree wholesale to the public webroot. Read AGENTS.md and WORK-MANIFEST.md before work.

## Automatic publication

`Check Jarvis` runs addon, heating and firmware tests and both container builds. Only a successful push of the trusted source branch enters `publish-laboratory`. It creates per-commit ZIP source packages with versions, full source commit and SHA256. These are not prebuilt images. Packages remain under `releases/<commit>/` on the lab branch; GitHub artifacts provide an additional 90-day copy. There is no automatic deletion of release history.

The public portal reads `catalog.json` from the fixed GitHub lab branch on each refresh. It labels evidence as source checks, never live device state. It exposes no device writes, shell endpoint, private config, voices, backups or credentials.

The publication job serializes lab changes and pushes without force. A concurrent external edit fails publication rather than being overwritten. To notify Plesk after publication, store the exact Plesk webhook as GitHub Actions secret `PLESK_LAB_WEBHOOK` in the user's own browser. The full webhook is a secret, not a value to put in docs/chat. Missing hook produces an explicit warning; publication to Git is not proof of live deployment. Existing Plesk setting "Automatically" deploys fetched commits; it does not itself prove that GitHub push triggers a fetch.

Initial activation without a configured hook: in Plesk select the existing lab branch, Pull now, then Deploy now. Verify HTTP index, portal.js and catalog.json against the lab tree. After hook configuration, publish a marker commit and verify it arrives without UI actions before claiming unattended deployment.

## Production deployment and rollback

Use the existing updater for addon versions and Admin deployment_prepare/apply for configuration bundles. Read storage, deployment_status and current versions first; acquire the lease; use CAS revision and explicit runtime checks. Preserve request IDs and reconcile unknown results. Release the lease. Ordinary heating settings use heating_settings with no Core restart. Restoration of a ZIP alone is not a runtime rollback: use the recorded addon restore/build or HA backup flow, then verify running versions. Never upgrade Core/OS incidentally.

## Backup status and remaining gap

29 October 2026 live check: existing Green backups list readable, 3.2 GiB free, backup preflight ready. This is a dated observation, not a live dashboard. Existing deployment backups and per-file before-images work. This change creates no extra large Green backup and deletes none.

Private off-Green backup export/upload is NOT configured or verified. The connected Admin API lists, creates and restores backups but exposes no backup-download/export or private remote destination configuration. The PHP webroot and public Git must never be used as a household backup target. Completing this requires an authenticated private destination (for example an HA backup location with suitable access), an actual export route, encryption/key recovery and a controlled restore test. Do not report this requirement complete from source archives alone.
