# Causal past-only AEC feasibility — 2026-11-03

**NO-GO for integration/deployment.** A frozen, past-trained subtractor differs meaningfully from classifying an entire mixed window: with a correct fixed linear model its current human component is preserved exactly. That favorable algebra did not establish eligibility for the actual room input or the entire self-interruption goal. The measured synthetic set includes bootstrap failures, weak future cancellation and amplification after changes that could arise upstream of the application.

## Reproducible bounded candidate

`run.py` uses the eight original flite clips and three original deterministic RIRs from `experiments/rejected-spectral-echo-20261103`, with the same gains, high-pass filters, 8-unit noise, 350-unit DC, .777–2.347 s delay and 0/±80 ppm drift. First four clips are development and last four distinct clips are held out. New scripts and outputs exist only in this temporary directory.

A 512-tap, 4 kHz causal FIR is fitted on the first 2.0 seconds of source-aligned microphone data. A subsequent .8 seconds validates it; delay search and 0/±80 ppm selection use only past microphone data. No future human/no-human label enters fitting. The current future burst starts at source time 3.5 seconds. The predictor remains frozen throughout it. Readiness requires past log-band trajectory/richness, sufficient reference Gram effective rank, and <=5% past held-out normalized prediction error. Unknown histories bypass subtraction. The model predicts and subtracts an echo waveform; it never discards a whole mixed window. A current energy guard bypasses if predicted power exceeds four times microphone power. That guard reads a completed test block (80–400 ms); its streaming latency has not been validated.

The fixture's true delay is used to place/scalar-score generated events and define a capture boundary containing 2.8 seconds of past echo, but the candidate's alignment comes from its past-only search. A production bootstrap readiness schedule and persistent adaptation loop are not implemented. This is one train/validate/freeze cycle representing the mechanism, not a complete MDF implementation or live pipeline.

96 fit attempts and 2,693 future/control scalar rows, generated audio only. Current stop-like bursts are 80/160/400 ms at .5 or 1 times local echo RMS. A zero-human version of every burst measures own-echo attenuation.

| Past history | Ready models | Consequence |
| --- | ---: | --- |
| Stable linear echo | 24/24 | Future cancellation available |
| Human continuously present at .5 echo RMS | 0/24 | Pass-through; zero echo cancellation |
| Human continuously present at 1 echo RMS | 0/24 | Pass-through; zero echo cancellation |
| Time-varying AGC throughout history | 0/24 | Pass-through; zero echo cancellation |

Thus the experiment does not assume that supervised clean training is available at runtime. It exposes the inability to initialize this candidate under the contaminated histories tested.

## Withheld future audio

The following ranges include all widths and .0/.5/1 human ratios using clean-past models. Full-band 16 kHz echo error is measured after a 4 kHz prediction is mapped back to microphone time; high-frequency echo left by the 4 kHz model counts against attenuation.

| Future channel | Echo attenuation, minimum / median / maximum | Current power-guard bypasses |
| --- | ---: | ---: |
| Same linear RIR | 1.34 / 14.35 / 26.34 dB | 0/216 |
| Gain becomes one quarter after validation | -5.54 / 0 / 0 dB | 212/216 |
| Gain doubles after validation | .91 / 5.24 / 5.97 dB | 0/216 |
| New envelope-dependent noise gate after validation | -7.52 / 3.68 / 17.98 dB | 51/216 |

A negative attenuation means subtraction increased echo error. The current energy guard mitigates many gain-collapse cases but does not make them safe universally. Some human additions change the bypass decision, introducing a prediction artifact: the worst paired human-component error energy is 7.46 times human energy after the gain drop and 17.70 after gating.

For the stable linear channel, compare `processed(echo + current_human) - processed(echo)` with the known current human waveform: maximum normalized component error is 2.1e-32; gain is 1 to floating-point precision. This is a measured check of the frozen linear subtraction identity, not proof of perceptual quality. Residual echo still contaminates the output: human projection gain spans .914–1.028 and human-target SNR spans -4.69 to 26.34 dB.

Of 36 clean-past, zero-human held-out future windows (four clips × three rooms × three widths), 34 reach 6 dB cancellation and 27 reach 12 dB; the worst is 5.26 dB. These statistics do not establish that residual echo stops triggering VAD or ASR.

## Fail-open controls

A stop burst from playback onset passes through unchanged before bootstrap (8/8). Echo-free independent speech, exact same 10 ms RMS-envelope human speech, and same-F0/different-phase periodic signals all remain unready (8/8, 8/8 and 3/3). Silence and DC histories also remain unready (1/1 each).

## Runtime and actual-room limits

Host training/search/validation costs 128–230 ms per fit; clean-past median 163 ms. Process peak RSS is about 205.5 MiB. `kernel-timing.json` separately benchmarks a native NumPy FFT predictor kernel; it excludes alignment, resampling, fitting, scheduling and device overhead. No Green performance was measured. The prototype uses SciPy for generated RIR/resampling/convolution; a runtime implementation would need suitable existing resampling support or a separately verified NumPy kernel. No dependency changes were made.

The single actual room capture has already been wiped. Its scalar correlations/coherences cannot validate a subtractor or determine the installed upstream XMOS stage. `channel_1_stage='NS'` is a schema default, not a verified installed setting. Upstream nonlinear processing remains possible even though local raw/enhanced scalar metrics matched. The gain/gate cases are controlled counterexamples, not reproductions of that room's DSP. They suffice to reject inferring physical eligibility from the favorable stationary linear cases.

No production files, Git state, live devices, raw microphone audio, or household actions were touched. No further model expansion is proposed from this spike. The original user goal remains open.

Files: `run.py`, `analyze.py`, `results.json`, `summary.json`, `kernel-timing.json`.
