# Owner1W experiment — 6 November2026

6 November 2026 — 1W experiment, persistence failed before sale

Owner requested1W target and confirmation across sale/return. Source b1db6c052d9ebb848577faab6e4e5871904d25f1, runtime0.6.7, deployment grid1-apply-20261106 active_verified00:10:18UTC, backup5a64fb3e; seven files exact readback. All shared targets/button/restoration1W; no guard/price/SOC/cap changes. Full580 tests pass20skipped. Guarded probe owner-grid1-native-20261106 at00:10:38UTC returned seven1W reads and immediate verified proof, but independent native snapshot00:11:15UTC returned20 and HA telemetry00:11:25UTC20. grid_target_confirmed correctly becamefalse. Reversion occurred in idle without any sale or mode transition; no export test was started after initial persistence failed. Automatic sales remains enabled/healthy, no active transaction/controller error. Leave owner1W config, do not claim persistence or confirmed sale-cycle. Actual writer/firmware mechanism remains OPEN. Evidence docs/evidence/2026-11-06-grid-target-1w.md.


Native short proof:
```json
{
  "supported": true,
  "verified": true,
  "target_w": 1,
  "before_w": 1,
  "actual_w": 1,
  "reads": [
    1,
    1,
    1,
    1,
    1,
    1,
    1
  ],
  "read_shapes": [
    {
      "captured_at": 1793923845.8917427,
      "single_before": 1,
      "bulk": 1,
      "single_after": 1
    },
    {
      "captured_at": 1793923851.1710804,
      "single_before": 1,
      "bulk": 1,
      "single_after": 1
    }
  ],
  "error": null,
  "captured_at": 1793923851.1717696
}
```

This is parameter acceptance followed by loss of persistence, not successful sustained1W operation. No second writer has been identified by this evidence; do not attribute it to Solarman, HA, firmware, or the sale mode without tracing. Existing ordinary automation only triggers on start/idle guard entry; no recurrent retry was added. No extra battery export or sale-mode change was performed because idle persistence already failed. Lease release verified.
