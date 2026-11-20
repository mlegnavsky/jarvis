# Owner-originated change during active tracing — 6 November2026

Owner said changing parameter, then confirmed changed at about06:41Prague. Assistant performed NO device writes during this observation. Originating interface/value was requested in commentary but not yet confirmed by owner; do not infer Solarman app vs physical inverter panel.

Baseline native104=20 at05:41:01UTC. Independent native bulk98..111 snapshot05:42:01.245730UTC returned104=1 while HA number state20 (source05:42:22.222507UTC). Next independent native snapshot05:43:01.134830UTC returned104=20; HA state20. Thus owner-originated change was actually seen natively and later reverted, not merely HA UI echo. Exact transition between native snapshots is unknown.

Returned wire/service logs collected around06:40:45–06:42:51Prague contain no observed FC06/16 or write services. These are bounded chunks with omissions, and absence cannot establish no HA write on every path. Trace remains active until approx06:51Prague reset. Need owner to identify interface used and confirmed target before attributing origin. No cause identified; cloud/firmware and other HA transport remain unproven.
