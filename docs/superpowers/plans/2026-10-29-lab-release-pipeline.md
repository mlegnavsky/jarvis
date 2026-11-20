# Laboratory and release pipeline

Authorized scope: versioned source packages, checksummed archive, public test evidence portal, automated Git publication and bounded Plesk deployment notification, persistent operations guidance, assessment of private off-Green backups.

1. Build immutable per-commit source archives; reject secrets and symlinks; tests.
2. Publish successful Check Jarvis runs only, from trusted push branch feat/jarvis-addon, to existing isolated lab branch. Include test report, catalog and version links. Serialize publication.
3. Notify Plesk only when a private PLESK_LAB_WEBHOOK secret exists; never log it, never declare notification equals deployed. Confirm HTTP content externally.
4. Maintain read-only browser portal with escaped text and explicit source/runtime distinctions. No production data or control API.
5. Verify live backup capabilities and document unresolved private remote destination. Never send HA backup to public Git or webroot.

Ruling: archive source packages rather than claim these ZIPs are ready-built HA images. Green continues using verified updater/build path.
Ruling: missing Plesk hook and private backup destination are activation gaps, not reasons to create public command execution endpoints or weaken existing path restrictions.
