# Local stateless speaker inference backend

Managed extension of existing local `jarvis_core` addon. Copy main.py, engine.py and fetch_assets.py to `jarvis_core/app/`, and Dockerfile to its root. Preserve original config.yaml, options/credentials and status endpoint. The addon manifest remains installed version 0.1.0 for the guarded local rebuild; the new inference service reports feature version 1.0.0. Original source snapshot remains in `managed_sources/jarvis_core/source.json` for rollback.

Uses Debian Python 3.12, sherpa-onnx 2.0.1 with its native aarch64 wheel and one inference thread. Build assets are downloaded from upstream release and checked against pinned SHA256 values. Model: `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx`, SHA256 `aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2`.

Published existing port 8765 serves only the pre-existing status UI. Inference port 8766 has no host port mapping and is reached only through addon container DNS `local-jarvis-core`. It provides bounded PCM `/embedding` and a public-fixture-only `/health` report. It has no household identity database, credentials endpoint, transcript logging or raw audio storage. No external speaker-recognition service receives audio. Existing STT/TTS services are unchanged.

Reference discrimination check: same speaker A 0.8088, same speaker B 0.6664, largest cross-speaker 0.3279. Conservative identification threshold 0.75 will intentionally reject the weaker genuine match rather than lower the bar. Initial English-only candidate was rejected after poor cross-speaker discrimination; its model/hash was not deployed.

Backend build job `speaker-backend-build-v1` verified started state, backup `1283c884`, source fingerprint `92bc9147b555b09811985c95f5634179f57f2d670eb7ccb481943057768dcc6f`. Independent native startup log proved the real ARM inference/reference probe passed (four fixtures in 5051.4ms), beyond merely a successful container build.

Upstream implementation/API: https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/speaker-identification.py
Model/reference assets: https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models
