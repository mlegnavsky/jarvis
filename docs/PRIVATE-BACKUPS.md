# Private backups over HTTPS — deployment and acceptance

Native Home Assistant WebDAV (available since 2025.3) replaces the blocked external SFTP path. Green Core 2026.6.4 already includes this integration; no code upgrade or restart is needed. Compatibility tests use aiowebdav2 0.6.2, the exact version in Core 2026.6.4.

## Server layout

- Public endpoint: https://laborator.odladeni.cz/backup-dav/index.php/
- Credential generator: https://laborator.odladeni.cz/backup-dav/setup.php
- Existing private sibling directory: `ha-backups`, owned by jarvis_lab (confirmed in Plesk shell, where it is `/ha-backups`).
- Private credentials: `ha-backups/access.json` with `username` and `password_hash`, no plaintext password. chmod 600. No private files in Git or httpdocs.
- Archives and metadata: `ha-backups/objects/` (created only after authentication). Temporary uploads use hidden unique names and publish with atomic no-overwrite link. SHA256 checks make identical retry safe. A conflicting existing backup is never overwritten.
- Only flat names ending `.tar` or `.metadata.json`; no folders, traversal, arbitrary names, symlink access, MOVE/COPY, configuration writes or DELETE. Maximum archive 4 GiB, metadata 1 MiB; preserve 1 GiB free disk space. A private upload lock serializes our PUTs; another upload receives423/Retry-After rather than overcommitting the reserve. Other host processes and subscription quotas remain external constraints. Host/PHP/nginx quotas may be lower and must be verified with an actual backup.

## Bootstrap in owner's browser

1. Open setup.php once. It generates a fresh random password and downloadable access.json containing only a password hash. The page never writes private server configuration. Save the password privately; refreshing generates a different pair.
2. Upload access.json via authenticated Plesk file manager to the private ha-backups sibling of httpdocs. Set permissions 600. Do not upload it to public webroot.
3. Add native WebDAV integration on Green: endpoint above, username jarvis-backup, matching generated password, backup path `/`, SSL verification on. The current Jarvis Admin supports existing options flows, not new integration config flows; this bootstrap needs the owner's UI.
4. Select the new location in Backup settings. Keep encryption enabled and save the emergency kit away from Green. Deletion is disabled server-side; do not configure automatic expiry for this location until retention is separately agreed.
5. Transfer one encrypted backup, confirm HA completed upload and remote archive + metadata exist. Compare size and stream integrity before reporting verified. Test restore only in an isolated environment; never restore production just to test.

## Rollback and limits

To disable access remove/rename private access.json in Plesk; endpoint returns 503. Retain objects. Removing the integration does not delete server copies. Reverting public endpoint code does not modify private storage.

Until bootstrap and actual Green upload, status is `activation_pending`, not verified backup. Synthetic HTTP tests demonstrate protocol/auth/storage behavior, not disaster recovery. Port22 externally timed out before credentials were checked; local Plesk SSH uses127.0.0.1:22, and chroot has no /proc, no sftp binary. Do not repeat SFTP setup without new evidence.

Lab recreated under isolated jarvis_lab subscription site91. Git source bdd0de8 was live with catalog and both ZIP SHA256 checks verified after automatic /httpdocs deployment was saved. TLS works. Do not change Cloudflare routes for jarvis.legnavsky.cz; outbound WebDAV uses the lab HTTPS endpoint.
