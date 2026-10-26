# 0.2.0 — experimental

- OAuth-protected MCP connector with separate read/control/maintenance scopes.
- PKCE S256, exact audience/redirect, persistent hashed opaque tokens, rotating refresh families and revocation.
- Paginated inventory; actions share existing allowlists and durable idempotency.
- Disabled by default; actual ChatGPT/Green/mobile authorization remains unverified.

# 0.1.0 — experimental

- Fresh inventory through Supervisor Core REST and WebSocket.
- Authenticated REST API, disabled-by-default allowlisted actions, durable idempotency and local audit.
- Optional bridge to separate Supervisor updater with backup and post-update verification.
- Real Green deployment, restoration and ChatGPT connection remain unverified.
