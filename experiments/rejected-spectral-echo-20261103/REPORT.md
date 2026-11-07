# Playback-recording identification feasibility, 2026-11-03

Outcome: **no tested conservative candidate separated room echoes while preserving every tested short human mixture. Do not deploy these candidates.** This does not rule out every possible acoustic method; it is a negative result for these measured candidates.

Temporary files only; no production, Git, live audio, household or network changes.

## Log-band trajectory candidate

32 mel-spaced log-power bands, 512-sample Hann STFT, 160-sample hop (16 kHz); search ±3 s with channel/temporal normalization, then ±6 ms refinement at 1 ms spacing. Per-band median subtraction estimates a stationary log-spectral channel. Richness is temporal spectral-shape RMS plus covariance effective rank, preventing constant-F0 phase-independent harmonics from serving as identity. Optional veto is maximum sliding 80 ms RMS log-spectral residual.

Eight different actual FFmpeg flite clips, voices slt/rms/awb, natural timing, six-second excerpts. First four training clips and four different held-out clips. Three deterministic RIRs (86–200 ms), gain .2/.7/1.2, 0/150/300/500 Hz high-pass, 8 PCM-unit noise, DC 350, delays .777–2.347 s, 0/±80 ppm drift. Twenty-four own-echo cases.

| Cases | Count | Trajectory correlation | Max 80 ms log-band residual |
| --- | ---: | ---: | ---: |
| Own recording through rooms | 24 | .799–.939 | 2.485–5.296 |
| Independent different words | 8 | .104–.248 | 7.524–13.058 |
| Independent same words, different voice | 8 | .128–.295 | 6.773–9.220 |
| Exact same 10 ms RMS envelope, different words | 8 | .164–.300 | 5.538–10.668 |
| Exact same 10 ms RMS envelope, same words/different voice | 8 | .136–.333 | 5.058–11.156 |
| Echo plus brief independent speech | 288 | .749–.936 | 2.474–7.081 |
| Same-F0, different harmonic phase | 3 | .936–.970 | .550–.610 |

Mixtures cover 80/160/400 ms, human/echo RMS .5 and 1, two positions per clip and three rooms. Constant-F0 controls have shape richness .465–.466 and rank 1.098 versus own-echo richness 1.865–2.439 and rank 2.245–5.740. A richness floor can reject these tone controls, but cannot reject human mixtures because their reference is rich speech.

A transparent candidate with correlation >= .75, shape richness >= 1, rank >= 1.5 and residual threshold set from training echoes (4.9085) accepts 9/12 held-out own echoes, rejects all 35 independent-human/tone controls, **but calls 222/288 human mixtures echo**. Raising the residual threshold to cover all own echoes (5.2963) accepts all 24 own echoes and **271/288 human mixtures**. More restrictive axis-aligned thresholds using all four extrema accept all own echoes and still accept 260/288 mixtures. Room/onset mismatch dominates the local residual, hiding many additions.

## Bounded held-out causal FIR candidate

4 kHz, 384 causal taps (96 ms), 16 ms alignment lead, ridge 1e-5 times average Gram diagonal. Fit output on alternating disjoint 80 ms blocks and predict the other fold; reverse folds, so every scored output sample is held out. Drift hypotheses 0/±80 ppm are selected by global held-out error. No same-window fitted error is represented as independent validation.

Same 24 own echoes and 144 mixtures (all widths/ratios, one position, three rooms). Mean held-out normalized residual on echoes is .00151–.03303, but the maximum 80 ms relative residual ranges .146–1.618. Threshold 1.618 accepts all 12 held-out own echoes and falsely calls 133/144 mixtures echo, including 22/24 mixtures at 80 ms and .5 RMS. Combining worst own-echo limits on mean residual, max 80 ms residual, and 95th-percentile residual still calls **67/144 mixtures echo**. The measured worst-block errors overlap mixtures despite low global error. Limited voiced excitation, room truncation, transient regions and quiet-block normalization are possible contributors, not separately established causes; global low fit error does not prove the absence of a brief human.

## Runtime and limits

Host only, OPENBLAS_NUM_THREADS=1. Log-band full alignment roughly 0.2–0.3 s per six-second clip; known-lag mixtures roughly 0.06 s. FIR bank with cross-fitting: median .156 s, range .144–.186 s per six-second clip. FIR materializes about 145 MB of float64 design/fold matrices; this is a feasibility implementation, not a Green-ready memory design. No Green timing or physical room/ASR acceptance was measured.

Raw evidence: `results.json` (347 cases), `fir-results.json` (168 cases); reproducible scripts `spike.py`, `fir.py`. Strong clean-echo versus independent-human trajectory separation is encouraging for locating candidate playback, but the observed short-mixture false rejection rate prevents using either candidate as an echo-suppression decision.
