# Spot UI1.2.2 — compact mobile plan and full-width graph

The main control card keeps today's completion and the next sale window visible. Price detail, limits, running-state detail and actions move into a closed disclosure. A brief live problem/recovery alert remains outside, and action failures from the visible automatic toggle also remain outside. The current-price card is hidden on screens<=700px and stays available on desktop.

The daily mobile plot left gutter shrinks42to6SVG units. Power-axis labels are drawn inside the plotting region with a contrast halo above curves. Other scales, series, history gaps, touch zoom, panning and slider behavior are preserved. No watt formula or backend export behavior changes. Cache version1.2.2 covers HTML/CSS/JS/chart and the owned iframe view.

Validation: Spot hub DOM/pure, daily graph math and gesture suites pass; release-manifest and whitespace checks pass. Regressions cover brief errors and visible toggle rejection outside collapsed content. Actual Chromium launch is blocked by environment socket/ptrace EPERM; no browser screenshot acceptance claimed. Deploy as static files with activation none, no HA restart and no sale-stop command.

Operational observation during review: runtime1.0.6 documented another native_controls read TimeoutError around21:43local, followed by safe cleanup and automatic recovery around21:46. No evidence of a permanent latch in that observation. Inspection confirms optional direct control reads and normal polling share Solarman's semaphore; timing evidence does not yet distinguish queue wait from a slow/lost wire response. Do not state a proven network or contention root cause. No third-party transport code or safety thresholds changed in this UI release.
