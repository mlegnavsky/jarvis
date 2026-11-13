# Paired room calibration — recording consent pending

The owner reports persistent stutter and17s response delay. Scalar logs establish three application cancellations and complete-TTS waiting, but not the actual echo path or the acoustic source of each candidate. The prior RMS/text rules, native AEC experiments and a new source matcher do not satisfy both echo rejection and human preservation. Another acoustic rule needs actual paired room data.

This is a concrete proposal, not authorization to record. No recorder or new capture has been enabled. Existing source/Git/deployment consent is not treated as microphone-recording consent.

If the owner explicitly agrees, prepare one admin-armed capture for the next normally initiated Jarvis conversation. The arm expires after120s if unused. Record at most30s of the already-open microphone stream, with raw and enhanced representations of those same samples, plus the corresponding generated playback reference and numeric timing/ownership metadata. Do not open another microphone, change the wake service allowlist, run an automatic wake or enroll a voice profile.

Store at most3MiB of paired PCM and bounded metadata in a private0700 directory under jarvis_workspace/local_duplex/calibration, files0600. Do not include transcripts, credentials, profile vectors or device log text. The capture must stop at30s, source close, mute, external stop or cancellation, whichever comes first. Default remains disabled; repeated arming requires another explicit instruction. Reject stale/replayed requests.

Use the data only for this acoustic repair, in private analysis. It must never enter public Git, a release archive, a shared page or extra speech-recognition/model requests. Derived scalar evidence may be published. Delete raw samples after analysis, and enforce a maximum24h retention if work is interrupted. Confirm deletion on Green and any temporary analysis copy.

Analyze actual playback/capture alignment, codec/resampling and front-end changes, room transfer, own-only periods and independently identified human input. A proposed echo correction then needs held-out human/same-envelope/mixed-speech negatives as well as echo positives, source/ownership regressions, native checks and new room acceptance. Current first-syllable human interruption and one-second total response remain unproved.
