# Energy and Žitenice forecast

User requested deployment to existing Energy and Weather tabs, with reliable data and source discovery. Read-only monitoring; no device or export policy changes.

1. Use OTE 15-minute day-ahead JSON directly; validate requested delivery date and all intervals, including DST. Convert with published CNB EUR/CZK, preserve negatives. Distinguish wholesale from an unconfigured contractual settlement price.
2. Fetch documented Open-Meteo forecast for Žitenice, hourly 48-hour display and seven daily summaries. Astral provides actual solar elevation, independently of forecast irradiance.
3. Add a custom HA YAML component and a dependency-free dashboard card. Preserve all 27 existing views. Poll with visible timestamps, mark fetch failures unavailable, reject stale display.
4. Verify parser with negative prices, normal/DST days and wrong delivery date; compile Python/check JavaScript. Write via revision-protected Jarvis administration, check jobs, backup/check/restart HA, verify live sensors. Keep deployed source under Git.

Alternative considered: embedding EnerSpot and In-počasí pages. Direct documented sources avoid advertising, iframe restrictions and scraping-dependent data collection.
