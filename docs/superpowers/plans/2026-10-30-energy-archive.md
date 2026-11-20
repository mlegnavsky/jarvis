# Energy archive implementation plan

Goal: private permanent server archive of ten-second energy snapshots and original spot/weather publications, queried through authenticated Home Assistant.
Architecture: native HA component with durable SQLite outbox; HTTPS immutable compressed batches on the existing laboratory server outside webroot; authenticated HA day proxy. Existing WebDAV credentials reused internally, never exposed to browser/Git. No retention deletion. Sensor reports backlog, server bytes/free space and measured annual estimate.
Tech: Python stdlib SQLite/gzip + HA aiohttp; PHP filesystem append-only archive.

- [ ] Test immutable batch idempotence, corruption rejection, UTC/day boundaries, outbox acknowledgement and source timestamps.
- [ ] Implement PHP append/status/day endpoint using existing private backup authentication; disallow redirects/deletes; keep raw publications and unavailable values.
- [ ] Implement HA collector, bounded durable queue, authenticated query view and restart-safe retries. Reject untrusted destination/credential ambiguity. Capture every10s; preserve fetched_at and forecast issue history.
- [ ] Publish endpoint through existing tested Git/Plesk pipeline; verify unauthenticated denial and private storage readiness.
- [ ] Install native component with CAS, configuration check, protected backup and one restart if required. Disk preflight currently1.8GiB vs2GiB floor; do not bypass or delete unapproved backup.
- [ ] Connect graph to archived measured rows/spot/weather; preserve hourly fallback and label forecast as forecast.
- [ ] Verify real append, duplicate retry, readback, disconnect/backlog/recovery, space accounting and runtime. Publish receipt with limitations.

Constraints: no fabricated historical measurements; old forecasts not backfilled as historical forecasts; no arbitrary URLs/paths; no secrets in logs/source; no Core/OS upgrade. Existing forecasts are predictions, not measured weather. Separate backup on same server does not protect against server loss.
