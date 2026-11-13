# Playback source discrimination and active conversation lifetime

Owner requests completion of the remaining self-interruption repair; nobody
is home. Preserve inline implementation, prior deployment/public Git consent,
and one fresh whole-change review. No repeated design questionnaire.

The current completed-transcript rule accepts unrelated short ASR results
from playback. Replace reliance on words alone only when acoustic source
evidence can distinguish generated playback from independent and mixed human
speech. Pure log-band similarity/coherence is insufficient: narrow periodic
signals and brief human additions are explicit negatives. A numerical spike
must demonstrate held-out room positives and preserve all tested human/short
stop mixtures before its classifier is eligible for production integration.
Unknown/ambiguous/too-short/error/budget cases keep human input available.
Do not recycle rejected RMS widening, Speex/AEC3 or80ms waveform-only rules.

The current240s hard wall timeout closes active speech. Keep the240s budget
as a watchdog since the last accepted nonempty transcript, resetting it for
each valid new turn/confirmed interruption. Rejected echo, empty ASR and
truncated input do not refresh it. Remove the duplicate absolute wall timer;
retain5s input stalls,8s normal idle,30/60/100s provider-stage and3s stop
deadlines and mute/external/source-close rules. Count accepted turns, including
interrupted answers, against the existing24-turn ceiling so false accepted ASR
cannot keep renewing provider work without a finite bound.

No new microphone activation, recording/export, authority/profile changes,
provider/model/voice/volume/firmware/Core updates. Acoustic signal processing
uses only existing dialogue bytes/generated references in bounded RAM, with
numeric diagnostics. Host tests are not actual room acceptance, identity or
one-second latency proof. Verify fixed-source native paths before activation
claims; preserve all rejected candidates, review rulings and remaining limits.
