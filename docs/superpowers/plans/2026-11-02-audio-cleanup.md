# Single HomePod output cleanup

Owner requests cleanup of intermittent HomePod output, not more parallel rules. Actual active1.1.1 last session generated speech32chars but skipped it because shared AppleTV volume0. Fixed operator test was heard at sharedTV50%. configuration.yaml enables jarvis_local_duplex only; old jarvis_homepod_output report is stale since1Nov22:00UTC and its domain is absent.

Keep one active output: local_duplex native RAOP local WAV. Read current HomePod RAOP volume/mute only; TV ownership pauses/resumes TV and never supplies speech volume. Preserve intentional HomePod0/mute, target/ownership/busy/resource cleanup and microphone privacy. Move pure TVSession into active component and remove unused legacy output source/wrappers/test-only composition. Historical trace decoder remains for old logs. Update operational manifest output pointer to live report; tombstone stale report so old connector cannot report staleconfigured as current.

- [x] Reproduce sharedTV0/mute suppressing nativeHomePod45 with red test.
- [x] Remove shared-volume callbacks, consolidate TVSession and delete retired source.
- [x] Full tests and independent review; preserve all TV safety/ownership and HomePod zero/mute guards.
- [x] Publish then backed-up CAS deploy/restart once; verify source/report/native fixed output and leave selected wake/pipeline unchanged.
- [x] After successful activation remove exact inactive legacy runtime files with CAS; write retired-report marker; preserve history/private rollback and audit.
