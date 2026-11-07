# Actual host-module integration check — one attempt

**PASS for SDK/API, resampling, and orchestration integration**, in 7.571352 seconds. This was not a hardware, electrical, or acoustic experiment.

The harness imported the actual repository `reference_probe.py`, `reference_writer.py`, `reference_native.py`, `reference_timing.py`, and `reference_tap.py` directly. It ran the actual `GeneratedReferenceProbe.run()`, including its interrupted first generation, complete second generation, TaskGroup cancellation, writer, and stop helper. Source hashes were captured and all five files remained unchanged during the run.

The actual NativeReferenceEndpoint schema validation, execute-service calls and response parsing ran against a **simulated native API facade**. Its queue, DMA counters, physical-stopped flag, and stop/empty acknowledgement were software simulation. No aioesphomeapi wire connection, ESPHome firmware, I2S, microphone, HomePod, or household endpoint was used. Synthetic keys created by the probe were removed after cleanup and are not in the evidence.

The Sendspin server and client were the real official `aiosendspin==10.3.0` implementation, connected only through localhost and real Pairing PSK → authenticated long-term Noise. The client advertised only PCM48k stereo16. The imported probe generated exact 44.1k stereo16 big-endian packets; the imported writer converted byte order and the official SDK performed the 44.1k → 48k conversion.

Measured results:
- 181 received chunks / 217,200 output frames, all PCM 48,000 Hz stereo16.
- Recovered tone: 700.0 Hz; RMS 1979.784 S16 units, consistent with the authored 700 Hz source.
- Timestamp continuity error: 0 microseconds; late chunks: 0; reported violations: none.
- Generations 1 and 2 both armed and cancelled; first phase interrupted, second phase completed.
- Two stream starts and two stream ends; no remaining producer, monitor or ReferenceWriter TaskGroup children after the probe returned.
- Actual reference-queue peak 1408 bytes in both phases, within its 11,264-byte bound.
- Simulated receiver queue peak 60 chunks within its 96-chunk bound.
- Final simulated status was stopped, empty, stream closed, generation 2.

Instrumentation limitation: `server_queue_peak: 0` in raw results was an unused initialized field, not a measurement. Do not cite it as observed queue size.

The actual probe report sets `electrical_output_observed: true` after trusting native counters. In this harness those counters were simulated. The enclosing results explicitly mark `probe_electrical_claim_is_simulated_only: true` and `physical_electrical_proof: false`; the nested probe value must not be extracted as physical evidence.

The official SDK logged one WebSocket-closed warning during final teardown; there was no exception or retained probe child. No retry or production-source edit was made.

Execution environment: Python 3.12.14 x86_64 in the existing isolated environment, official aiosendspin10.3.0, AV16.0.1, NumPy2.3.2, Pillow12.2.0. This is not execution on Python3.14 aarch64; the earlier dependency-wheel audit covers availability there.

Frozen 240-second result hash was rechecked and remains unchanged:
`fa69a54634c141cf4ddb3557afc11f8e1e4dba15457c4d4a1860d8ed6cb916c5` (original FALSE verdict).

The `run.py` harness has an exclusive attempt marker. Reproduction requires a new experiment directory and the same recorded source snapshots and isolated dependency lock; the original evidence should not be overwritten.

