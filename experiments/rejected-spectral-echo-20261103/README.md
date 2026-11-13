# Rejected spectral/FIR echo decision candidates

Read REPORT.md and frozen scalar results. These are synthetic/Flite numerical
spikes, not runtime imports, recordings, identity proofs or Green timings.
Both fail short mixed-human preservation and must not be deployed.

Reproduce with FFmpeg/flite/libmp3lame, NumPy and SciPy on a host:

```sh
OPENBLAS_NUM_THREADS=1 python experiments/rejected-spectral-echo-20261103/spike.py
OPENBLAS_NUM_THREADS=1 python experiments/rejected-spectral-echo-20261103/fir.py
```

These commands regenerate authored speech locally and replace scalar results.
No temporary PCM should be copied into Git. helpers.py preserves the three
original numerical helpers; only import paths were made repository-relative.
