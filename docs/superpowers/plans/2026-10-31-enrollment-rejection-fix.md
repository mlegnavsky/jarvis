# Enrollment rejection fix

Owner-side second-sample cancellation exposed destructive handling of one
inconsistent embedding. Reject the sample, preserve accepted progress, retain
the .65 consistency gate, three-sample requirement, .75 identification threshold,
.12 ambiguity margin and300s session expiry. Do not enroll household fixtures.

Regression tests: accepted anchor + outlier + two matching samples enrolls only
anchor voice; repeated other-speaker samples never enroll; coordinator reports
rejection and retained count without names/vectors. RED observed,23tests GREEN.
Report version2 includes policy marker and pending counts/deadlines. Independent
review precedes publication. Deploy source and recovery copies through CAS
bundle, backup/restart; verify file readback and running report policy marker.
Physical enrollment still requires owner acceptance; no profile may be invented.

Scope note: logs contain additional English speech but do not establish its
source. This fix does not claim acoustic TV rejection or a full-duplex pipeline.
