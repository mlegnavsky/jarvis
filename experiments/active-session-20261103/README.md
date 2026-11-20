# Accepted-turn lifetime host replay

Final source1.3.3 was held fixed for300.1915s. Eight scheduled synthetic human
inputs were accepted, including the275s input; the answer active at240s
continued until273.989s. The300.2s synthetic source EOF deliberately cancels
the final answer (StreamAborted on the reference reader is expected cleanup).
No provider failure, all workers/readers closed, both pipes <=256KiB.

Two injected mismatching-ASR echo events still produce two unwanted agent
turns. This is a known failed acoustic check, not an acoustic repair claim.
VAD/ASR/identity/providers/receiver/room are scripted; actual runtime Session,
turn bridge, output, MP3 codec and bounded pipes run on this host. No real mic.

Reproduce from the repository root with ffmpeg/flite and the pinned native
Python dependencies miniaudio1.71/pyatv0.17.0 in NATIVE_DEPS:

```sh
python experiments/simulated-dialogue-20261103/run.py --native-deps "$NATIVE_DEPS" --expected-source 183cec10cdf60ea7bab2c685104e9b102bd749b35eeebc8946aa3a4cba40f70f --extended-conversation --duration 300 --output /tmp/jarvis-active133-replay.json
```

No generated PCM or real microphone audio is retained in Git.
