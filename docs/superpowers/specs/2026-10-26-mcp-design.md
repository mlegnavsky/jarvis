# Jarvis MCP connector — implementation design

User asked to build the proposed ChatGPT connector now and account for future expansion. Technical choices below are the implementer's decisions; no deployment, production authorization or main merge is included.

## Intent and scope
Expose the existing fresh inventory, narrow actions and supervised maintenance to an authorized MCP client. Keep HA automations independent. Single-household owner initially. No model API calls or OpenAI API key are needed by this server.

## Approaches
- Static bearer REST: already available, but ChatGPT cannot supply arbitrary API keys to an MCP connection.
- External identity provider + MCP: mature identity management, but requires another configured service/account.
- Selected: stateless Streamable HTTP MCP in existing aiohttp app, with a narrow local authorization-code service for one pre-registered confidential client. This avoids another runtime/account and keeps deployment on Green. Experimental until real ChatGPT OAuth and Green tests pass. It is not a general identity provider.

## Boundaries
`/mcp` uses OAuth tokens, never the existing REST or Supervisor token. OAuth discovery, PKCE S256, exact resource/audience, exact redirect allowlist, client secret, short-lived single-use code, expiring opaque access tokens, rotating refresh families, revocation and restart persistence. Tokens/codes are stored only as hashes in a mode-0600 SQLite database. Changing OAuth configuration invalidates earlier grants. Login uses a separate high-entropy owner secret, browser-bound transaction/CSRF cookie, explicit consent, bounded persistent rate limiting and no access logs. TLS ends at Cloudflare; issuer/metadata URLs come only from configured HTTPS origin, never Host/forwarded headers.

Scopes: jarvis:read, jarvis:control, jarvis:maintain. Default only read; control also requires existing writes_enabled and entity/service allowlists. Maintenance requires existing maintenance_enabled and updater permission. OAuth grants cannot bypass those gates. Tool metadata includes securitySchemes and read/destructive/idempotent/openWorld annotations. Every mutation requires a stable request_id and shares the existing durable journal.

Tools: status, paginated inventory, allowed action, update check, update start, update job. No arbitrary shell/URLs/filesystem or Core updates. Stateless JSON MCP responses; GET/DELETE return 405, no SSE push stream. Protocols 2025-06-18 and 2025-11-25 only. March is not supported because it requires legacy batching. Initialization without a version header negotiates the supported protocol; subsequent requests require a supported protocol header. Validate Origin, media types, protocol header, JSON-RPC shape and arguments before effects.

## Future compatibility
Versioned tools and capabilities; paginated/minimized inventory; separate scopes allow adding household members/identity provider later without changing HA policy. Voice, proactive home automation, solar/heating optimization, multi-user roles and chat-history synchronization are roadmap items, not implemented by this connector. Mobile/voice availability depends on the actual ChatGPT client/account and requires real acceptance; do not promise native-app support before testing.

## Acceptance
HTTP integration tests for OAuth → MCP initialize/list/call, restart/expiry/replay/revocation, client/resource/redirect/PKCE/CSRF mismatch, disabled defaults, malformed requests and duplicate mutations. Existing tests continue to pass. CI arm64/amd64 builds and container startup. Real Green, Cloudflare and ChatGPT login remain explicit pending checks.
