# 0.2.3 — nové vydání pro Green

- Nové číslo vydání v manifestu i programu; zahrnuje opravu původu přihlašovacího formuláře a diagnostiku z verze 0.2.2.
- Nastavení a klíče se nemění. Zbývající chybu OAuth je nutné ověřit po instalaci; změna čísla verze sama neopravuje nesoulad údajů aktualizační entity Home Assistantu.

# 0.2.2 — experimental diagnostics

- Distinguish missing form transaction, unknown/consumed transaction, expiration and invalidated configuration during browser consent. Token endpoints retain generic invalid_grant responses.
- Synchronize the runtime version with the add-on manifest.
- Does not claim to fix the remaining Green consent failure; the next fresh attempt supplies evidence without exposing credentials or transaction values.

# 0.2.1 — experimental

- Fix browser OAuth consent rejected as invalid_origin: use same-origin referrer policy so form POST retains its Origin, without sending referrers to other origins.
- Keep exact Origin, cookie and CSRF checks; missing, null and foreign origins remain rejected.
- Regression tests cover the login response policy and denied origins. Actual ChatGPT completion still requires verification on Green.

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
