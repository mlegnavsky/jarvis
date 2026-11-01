# Shared Apple TV/HomePod response volume

> Use superpowers:executing-plans for this targeted fix.

Goal: the clock question actually captured at20:41:36 must not be silently discarded when Jarvis pauses Apple TV and the idle HomePod RAOP volume is zero.
Architecture: an explicit shared_volume_source option binds this household's confirmed Apple TV→HomePod route. Only a currently owned, fingerprint-matching paused TV session supplies its freshly observed volume and mute setting. Unknown values fail rather than inventing a louder default. Standalone HomePod, user zero/mute, unrelated/replaced TV sessions and silent light commands retain their policies. Report skipped output separately from completed playback.
Sources: HA Core2026.6.4 apple_tv/media_player.py and its pinned pyatv0.17.0. No microphone/firmware threshold change in this patch.

- [ ] Reproduce actual pause→RAOP0→skipped answer via the real nested play hook, TVSession and volume helper; add mute/zero/source ownership and skipped-counter regressions; run RED.
- [ ] Add validated optional shared_volume_source, fresh guarded TV volume, routing selection and accurate skipped diagnostic; runtime/manifest1.1.2; run GREEN and relevant full suites.
- [ ] Review source independently, publish through connected GitHub with expected HEAD, preserving all unrelated remote files.
- [ ] Read live source/config/recovery revisions; enable only the owner-confirmed shared source, backed-up CAS deployment and restart. Verify current source, runtime, microphone and no recording. Acoustic wake quality and audible owner acceptance remain separately unverified.
