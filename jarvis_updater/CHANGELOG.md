# 1.0.0

- Gateway public access can be disabled independently; increasing revoke_generation invalidates existing grants while retaining the registered client.

- Independent OAuth/MCP gateway retains the existing public hostname, client and tokens.
- Durable port handover, OAuth authority commit and rollback phases preserve recovery after restart.
- Authenticated sibling rescue, verified updates and outage-test restart obligations remain available independently of Jarvis and Home Assistant Core.
- Restore targets only the sibling from an explicitly selected backup; interrupted writes are never blindly replayed.

# 0.2.0

- Volitelné automatické spárování se sourozeneckým Jarvisem přes interní Supervisor API, bez ručního přepisování klíčů.
- Klíč vzniká pouze uvnitř Greenu a je uložen s právy 0600. Před konfigurací vzniká záloha.
- Párování zachová ostatní volby a odmítne cizí cíl, existující jiné klíče nebo později odebrané oprávnění.

# 0.1.0

- Fresh inventory through Supervisor Core REST and WebSocket.
- Authenticated REST API, disabled-by-default allowlisted actions, durable idempotency and local audit.
- Optional bridge to separate Supervisor updater with backup and post-update verification.
- Real Green deployment, restoration and ChatGPT connection remain unverified.

