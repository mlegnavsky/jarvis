# Resilient administration implementation plan

User explicitly requests all five remaining foundations together, automatically resolving obstacles: diagnostics, independent recovery known to the assistant, complete app lifecycle, change history/rollback, device/permission map. Prior authorization delegates technical choices and implementation without more manual commands.

## Architecture

Keep two existing apps. Upgrade Updater into a stable OAuth/MCP gateway plus independent Supervisor recovery controller. Keep the SAME public URL, OAuth issuer/client/redirects, and port8099 used by the remotely-managed Cloudflare tunnel. The normal Jarvis app becomes an internal backend. Gateway owns OAuth state, proxies authenticated validated operations to Jarvis, and locally handles update/recovery if Jarvis is down. This isolates a Jarvis process/image failure, not loss of Green, power, Internet or Cloudflared.

Gateway migration: new Jarvis provides authenticated internal catalog/invoke and OAuth snapshot endpoints. Updater initializes from trusted sibling options and imports SQLite OAuth state. Activation is executed by Updater: final OAuth sync, remove Jarvis host port8099 and restart it internally, map Updater port8100 to host8099, restart Updater. Persist migration phases; do not announce complete until an authenticated external call reaches gateway and backend is healthy. Pre-arm a bounded recovery/rollback for activation failure. Never mutate the Cloudflare tunnel token or claim an unavailable Cloudflare API exists.

Gateway scopes: local verification of all OAuth tokens, same scope checks and extra maintain for reserved jarvis.* action services. Backend uses existing REST credential only on internal network, additionally validates name/argument schema/scopes and feature gates. Credentials and SQLite migration data never printed or committed. Copy OAuth implementation into updater/gateway package with a source parity check to prevent drift; normal Supervisor builds use per-app contexts.

Recovery controls: status, restart sibling Jarvis, verified update, restore only the sibling from explicitly selected known backup, and a short outage test that always schedules/restarts Jarvis in finally. Durable IDs and no blind replay. Existing jarvis_status/update_* work from gateway independently; existing jarvis_action service=jarvis.rescue exposes rescue control even when a chat's cached tool catalog has not refreshed. Backend failure returns recovery_available and the concrete route.

## Independent tasks and ownership

1. Updater/gateway implementation and focused tests: jarvis_updater/**, tests/test_gateway*.py. Does NOT edit main app files or shared release scripts.
2. Admin diagnostics/lifecycle enhancements: jarvis/app/admin.py, diagnostic helper module, tests/test_admin*.py, HA transport helpers as coordinated. Add bounded redacted logs, timings/core-supervisor-resource diagnostics, repository add, uninstall with backup/readback and protected connectivity targets, explicit auditable change metadata and permission/device map. Do NOT edit main MCP/server or updater.
3. Primary: main app gateway contracts, migration safety hooks, release gates/docs, integration/CI, deployment and live acceptance. Main release3.3.0, Updater1.0.0 (subject to final verification).

## Contracts

- Main GET /v1/gateway/catalog -> {tools:[MCP definitions]}; POST /v1/gateway/invoke -> body{name,arguments,scopes}, returns MCP CallToolResult. Existing REST Bearer api_token boundary applies. Validate scope, catalog, schema and feature flags before invoking.
- Main POST /v1/gateway/bootstrap -> bounded SQLite backup bytes as base64 in {oauth_database:<base64>}; must set a durable OAuth migration pause first (only authorization mutations pause; read calls continue). A rollback/unpause endpoint/hook restores old route if gateway activation fails.
- Updater authenticated POST /v1/gateway/activate with Idempotency-Key -> queued migration state. GET /v1/gateway/status -> durable state. Main reserved action jarvis.gateway delegates these through narrow MaintenanceBridge.
- Gateway proxies internal HTTP to sibling host prefix-jarvis:8099 with jarvis_api_token and rejects arbitrary URL/target.

## Acceptance

- OAuth grant and refresh survive authority migration; anonymous/insufficient-scope calls rejected. Backend failure still permits authenticated recovery; stale home values never substituted.
- Existing complete suite, arm64/amd64 builds and startup checks pass. Independent code review of control-plane migration before live activation.
- Upgrade main, upgrade Updater via main Admin (Updater cannot update itself), verify gateway internally, activate same public endpoint, verify external access. Then stop Jarvis briefly through a recovery test with guaranteed delayed restart and verify gateway survives the outage; restart/readback verified.
- Diagnostics and lifecycle API contracts tested; real uninstall tested only on an explicitly created harmless test app if feasible. Never remove existing user apps for a test. Record which operations were simulated vs actually executed.
- Final evidence and fallback instructions stored in Git; no tokens, actual logs or private configuration inventories.
