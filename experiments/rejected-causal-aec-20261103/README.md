# Rejected causal echo subtractor

NO-GO. Read REPORT.md and summary.json. All fixtures are authored synthetic
speech; no actual microphone recording is included. Production imports none
of these files. The full2693 scalar cases/96 past fits are losslessly stored
in results.json.gz. Python gzip.decompress reconstructs the original JSON.

Host reproduction requires NumPy/SciPy/FFmpeg/flite:

```sh
OPENBLAS_NUM_THREADS=1 python experiments/rejected-causal-aec-20261103/run.py
python experiments/rejected-causal-aec-20261103/analyze.py
```

Only import/output paths changed from the measured spike. Mathematical
operations and frozen scalar values remain unchanged. Reproduction writes
a new uncompressed results.json and authored text fixtures locally.
