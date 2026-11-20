# Four-minute synthetic dialogue, 3 November 2026

Owner requested a four-minute conversation simulation without anyone at home.
Baseline1.3.1 fingerprint4aaf4cb1a9b4ddf799ed061b039dce74acfc0ab8f203daae47cf3b8d61f6c2bc failed after17.77s; an instrumented reproduction failed after17.76s. The bounded stream reader requested49248bytes while17907validbytes were available, then treated5s of normal native playback backpressure as a stalled source. A partial-read-only candidate also exposed the producer-side5s full-queue timeout. These are preserved in attempt-1/attempt-2/attempt-3.json.

The final candidate1.3.2 fingerprint0188c6b6f946487e975cd7d7cdd8d7ec62610ed32202bc76717831b3b6b99750 permits bounded shortreads and distinguishes shared playback backpressure from upstream inactivity. Resume timestamps prevent an expired pre-pause reader deadline racing wakeup. True empty input and provider HTTP timeouts,256KiB limits, owner deadlines and abort cleanup remain. No echo/input decision changes.
It is a host real-time experiment, not a conversation conducted on the Green.

## Method

Generate two artificial English voices offline with FFmpeg/libflite. Feed
240 seconds of PCM in nominal10ms chunks through production PlaybackObserver,
RMS echo gate, Segmenter, Session, TurnBridge, TextEcho and HomePodOutput.
The output uses the production bounded MP3 pipes/reference decoder and the
actual miniaudio1.71/pyatv0.17.0 audio-source decoder. The receiver consumes
real decoded output at normal playback speed, with explicitly simulated1.5s
scheduling. Production Session's existing240s limit remains unchanged.

Seven human fixtures request long stories, stop once, and ask a different
question during speech. Echo bursts use the current generated reference,
gain0.37 plus a delayed55ms reflection of gain0.11, and200ms/1250ms transport
offsets. Two bursts deliberately inject an unrelated two-word ASR result.
That injection is a conditional regression scenario modeled on the observed
short mismatching transcripts. It does not prove a real recognizer will
produce these particular words or establish actual room echo parameters.

ASR uses a known synthetic-frame lineage table; VAD uses an RMS threshold;
identity and agent responses are scripted. Fixed550ms STT/150ms agent delays
are test parameters, not measured service speed. TTS is an offline fixture
MP3 stream; no OpenAI/Marin timing or recognition quality is inferred.
No real microphone, HomePod/network connection, identity decision or
household action is exercised. All generated audio is temporary; result.json
contains numeric observations and authored scenario text only.

## Reproduce

Use FFmpeg with flite and libmp3lame and Python with miniaudio1.71 and
pyatv0.17.0. The optional native-deps argument adds a preinstalled package
directory to sys.path; it is not a virtualenv executable.

```sh
python experiments/simulated-dialogue-20261103/run.py \
  --native-deps /tmp/jarvis-stream-native \
  --expected-source 0188c6b6f946487e975cd7d7cdd8d7ec62610ed32202bc76717831b3b6b99750 \
  --duration 240 \
  --output experiments/simulated-dialogue-20261103/result.json
```

An8s preflight validated codec playback, original-source EOF cancellation and
closed workers/readers before the full experiment. No production runtime
files, controls, recording state or device settings are modified.

## Interpretation

Historical attempt-2 contains an invalid vacuous
`all_seven_human_turns_accepted=true` check despite its early failure and one
human turn. Preserve that raw result, but never use that check as evidence.
The current harness reports null for this check on short controls. The
Event-only interim candidate has `source_unchanged=false` and is excluded
from final-candidate proof.

Read measured checks in result.json; a completed four-minute run is not a
passing acoustic result. A self-answer with an echo-origin lineage is a
reproduced conditional software failure. Real ASR, human voice identity,
receiver transport, room performance and one-second latency remain unverified.
No gate change or deployment follows solely from injected fixtures.

A parallel70s transport-control run keeps only the initial human request and the two exact-echo fixtures (--transport-control). It verifies a complete60s decoded answer, separately from planned interruptions in the main dialogue. Other than ordinary host background verification load, inputs are scheduled in real time.
