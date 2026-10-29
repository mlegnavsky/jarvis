# Jarvis laboratory and archives

Production source: `feat/jarvis-addon`. Plesk source: `lab/plesk-bootstrap-20261029`, document root `/laborator.odladeni.cz`. Never deploy the production tree wholesale to the public webroot. Read AGENTS.md and WORK-MANIFEST.md before work.

## Automatic publication

`Check Jarvis` runs addon, heating and firmware tests and both container builds. Only a successful push of the trusted source branch enters `publish-laboratory`. It creates per-commit ZIP source packages with versions, full source commit and SHA256. These are not prebuilt images. Packages remain under `releases/<commit>/` on the lab branch; GitHub artifacts provide an additional 90-day copy. There is no automatic deletion of release history.

The public portal reads `catalog.json` from the fixed GitHub lab branch on each refresh. It labels evidence as source checks, never live device state. It exposes no device writes, shell endpoint, private config, voices, backups or credentials.

The publication job serializes lab changes and pushes without force. A concurrent external edit fails publication rather than being overwritten. To notify Plesk after publication, store the exact Plesk webhook as GitHub Actions secret `PLESK_LAB_WEBHOOK` in the user's own browser. The full webhook is a secret, not a value to put in docs/chat. Missing hook produces an explicit warning; publication to Git is not proof of live deployment. Existing Plesk setting "Automatically" deploys fetched commits; it does not itself prove that GitHub push triggers a fetch.

Verified activation, 29 October 2026: source commit `30348df692f92e6833a926254eba3a9e933669f7`, successful push run `40891692482`, publish job `123510752732`. Plesk accepted the HTTPS POST notification. Live HTTP checks confirmed index, portal.js, catalog latest commit, and both source ZIP SHA256 values against the manifest. The webhook is configured; never retrieve or print its secret. The notifier canonicalizes the Plesk alias to the verified TLS hostname and follows no redirects.

## Production deployment and rollback

Use the existing updater for addon versions and Admin deployment_prepare/apply for configuration bundles. Read storage, deployment_status and current versions first; acquire the lease; use CAS revision and explicit runtime checks. Preserve request IDs and reconcile unknown results. Release the lease. Ordinary heating settings use heating_settings with no Core restart. Restoration of a ZIP alone is not a runtime rollback: use the recorded addon restore/build or HA backup flow, then verify running versions. Never upgrade Core/OS incidentally.

## Backup status and remaining gap

29 October 2026 live check: existing Green backups list readable, 3.2 GiB free, backup preflight ready. This is a dated observation, not a live dashboard. Existing deployment backups and per-file before-images work. This change creates no extra large Green backup and deletes none.

Private off-Green backup export/upload is NOT configured or verified. The connected Admin API lists, creates and restores backups but exposes no backup-download/export or private remote destination configuration. The PHP webroot and public Git must never be used as a household backup target. Completing this requires an authenticated private destination (for example an HA backup location with suitable access), an actual export route, encryption/key recovery and a controlled restore test. Do not report this requirement complete from source archives alone.

## Owner decision: own-server household backups

Martin explicitly selected his own server on 29 October 2026. Do not propose Google Drive again. Git source archives are already stored on the server; private household backups are a separate, still blocked requirement.

Preferred supported route to evaluate: Home Assistant SFTP Storage, available since 2025.10 and therefore predating the installed Core 2026.6.4. Official setup: https://www.home-assistant.io/integrations/sftp_storage/ . This uses the native Backup manager for manual/automatic copies and restore; no custom public upload receiver is needed if the server offers SFTP.

Required one-time server provisioning: an SFTP account with write access to an existing private folder outside every domain document root; actual host, port, username and account-relative remote path; password or supported private key entered privately in HA. The server's SFTP capability and account are NOT verified. A Plesk FTP account is not proof of SFTP availability. Do not enable a shell or expose SMB/NFS publicly as a substitute. Current Odladeni connector manages permitted application files, not Plesk accounts or SSH/SFTP access. Current Jarvis Admin supports integration options, but not creating a new integration configuration flow.

Once provisioned, use the user's HA Settings > Devices & services > Add integration > SFTP Storage. Then Settings > System > Backups > automatic backup settings > Locations: enable that location, retaining encryption. Store the emergency recovery kit privately outside Green; never in Git/chat. Preserve existing backup schedule and backups. Do not enable new deletion/retention rules without an agreed scope.

Acceptance: authenticate; verify the remote directory is outside all webroots; upload one encrypted backup; confirm completed upload at the selected agent and the remote object exists with expected size; compare SHA256 if the transport exposes it; perform an isolated restore test before claiming verified disaster recovery. An accepted upload or source ZIP download is insufficient. Until these checks pass, status is blocked_destination_not_provisioned, not complete.
