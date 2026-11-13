# Wake calibration and backup cleanup — 5 November 2026

Owner approved removing additional older unprotected working backups to provide
space for the previously approved firmware installation. Deleted individually
with fresh CAS revisions: 71b44763, 44658f15, d6d22db0. Each durable job
wake90-clean-<slug>-20261105 finished verified. Latest 8f98d4a5 and all protected
backups preserved. Fresh storage increased from 1.8 to 4.0 GiB.

The controlled household test on 4 November failed after disabling the second
wake word: the main Jarvis wake hint triggered a TV pause before STT returned
empty text. No accepted command or assistant response was observed. Private
runtime details and transcripts are not published here. The early TV pause
policy is unchanged; false-wake elimination is NOT established.

Custom Jarvis wake threshold changed from 0.8 to 0.9. Model binary unchanged;
short command vocabulary unchanged. Second wake word remains no_wake_word.
UI sensitivity remains Moderately sensitive; its standard-model handler does
not control this custom model. No firmware/reference overlay or Core update.

Compile wake90-compile-20261104 / a5c39a01429d finished exit 0 at
2026-11-04T23:17:05Z, activation false. Original lease expired before queued
release ran; that release failed deployment_lease_expired. Fresh read confirmed
unlocked before acquiring the new installation lease; no duplicate compile.

Install wake90-install-20261105 finished verified at 2026-11-05T05:13:51Z.
Mandatory ESPHome backup 6d032ebf created. Native compile 5b07e0603015 followed
by upload 57a9aac0955a, exit 0. Device online with expected and deployed hashes
both e4bd82b9. Firmware configuration revision
7be23fe495abb8beb437d726bc6c68a97266e241a07182df626f3465ca8b620a unchanged.
Post-install read confirms Jarvis primary, second wake disabled, mute on,
satellite idle, and 4.0 GiB free. Installation lease released verified.

Firmware activation is verified; acoustic acceptance remains OPEN. Microphone
kept muted until a controlled household TV/short-command test. Do not repeat
installation or claim the television trigger problem is fixed from hashes alone.
