# Rejected source verifier

Not imported or deployed. Native2k coarse/16k fine matching passes5direct-source/control regressions but only1/15causal voiced room/highpass positives;30/30independent/mixed-human negatives pass. This fails the intended echo-rejection goal. Thresholds were not weakened. No real microphone audio, no recordings, no live source change.

Reproduce with host NumPy/SciPy:

```sh
PYTHONPATH=experiments/rejected-acoustic-verifier-20261103:managed_sources/local_duplex python -m unittest discover -s experiments/rejected-acoustic-verifier-20261103 -q
PYTHONPATH=experiments/rejected-acoustic-verifier-20261103:managed_sources/local_duplex OPENBLAS_NUM_THREADS=1 python experiments/rejected-acoustic-verifier-20261103/controls.py
```

controls.jsonl records the rejection run. This is not a proposed production fix.
