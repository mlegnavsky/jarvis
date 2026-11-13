# Voice repairs and room commands Implementation Plan

Goal: deploy the authorized collision repairs and deterministic Czech light commands relative to the microphone room.
Architecture: preserve the existing Green/Voice PE/HomePod stack and permission exposure. Native command routing runs before the model, without enabling HA interception that would steal companion followups. Diagnostics observes pipeline configuration and never changes it.
Constraints: HA Core 2026.6.4 remains installed; no new hardware, no invented household profiles, no audible tests while user is away. A new trained wake model and acoustic echo cancellation cannot be substituted with text rules. Actual wake phrase stays Hey Jarvis.

## Task 1: Remove diagnostic configuration mutation
- [x] Reproduce boot test rewriting prefer_local_intents; remove mutation and make actual companion cloud tests explicitly invoked, not automatic after every restart.
- [x] Add descriptions and report statuses for the explicit companion test. Preserve synthetic native local regression probes.

## Task 2: Room-relative commands
- [x] Add pure parser/resolver regression tests: rozsviť/zhasni with optional to/světlo/světla; explicit room overrides microphone room; no room never means whole house; unknown/missing/ambiguous area never falls back; only exposed lights.
- [x] Implement room_commands.py and HA registry adapter. Resolve entity-level area before device area and use source satellite/device area. Execute a single light service with original HA context; verify states or acknowledge only submission. No model call for supported commands.
- [x] Test actual conversation boundary and native startup dry-run with fictional service transport; never switch household lights in verification.

## Task 3: Cancellation and deployment
- [x] Add tests and ownership-scoped cancellation when another activation starts on the same managed satellite, preserving other playback.
- [x] Verify existing volume migration/services are deployed, re-read revisions, deploy files with before-image backups and verified jobs, restart once with backup.
- [x] Run full suites, independent review, live readback/config verification and same-boot readiness reports. Record physical/wake-model limits truthfully.
