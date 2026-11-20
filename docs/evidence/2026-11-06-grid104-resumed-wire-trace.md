# Resumed grid104 wire trace — 6 November2026

Owner clarified resume detailed inverter tracking and asked assistant to perform1W write. Source 86c592e2740c6903663f60e6e9dcf35e76dcba69, deployment resume104-apply-20261106 verified active_verified/reload only, exact15min bounded logger reset plus self-disable. Run began05:36:10UTC; scheduled reset/end/self-disable about05:51:10UTC (06:51Prague). Do not claim future reset observed yet. No device mode/sale setting change; assistant issued one guarded1W command resume104-owner-onew-20261106, inbox verified, physical proof failed.

First focused on-wire interval retained WITHOUT redacted lines:06:36:46.477–06:36:57.039Prague. Parsed Modbus request sequences0x42–0x56 are contiguous; only write is FC16 register104=1 at06:36:46.935. FC03 single104 returned1 at06:36:48.080,06:36:51.161,06:36:51.353; returned20 at06:36:56.425 and06:36:56.646. Bulk corroboration is in native proof. All other captured Modbus requests in interval are FC03 reads. Protocol heartbeat received06:36:55.786 and acknowledged06:36:55.787 is not a Modbus parameter write; proximity alone is not causal evidence.

This establishes reversion without a20W write ON THIS OBSERVED CONNECTION during the captured transition. It does not exclude another HA transport/library, another network client/cloud path or inverter/logger behavior. The bridge omitted36LATERlines after its character budget, but retained focused interval sequences are contiguous and unredacted. No attribution of exact cause yet.

Proof:
```json
{
  "supported": true,
  "verified": false,
  "target_w": 1,
  "before_w": 20,
  "actual_w": 20,
  "reads": [
    1,
    1,
    1,
    1,
    20,
    20,
    20
  ],
  "read_shapes": [
    {
      "captured_at": 1793943411.3540561,
      "single_before": 1,
      "bulk": 1,
      "single_after": 1
    },
    {
      "captured_at": 1793943416.6476386,
      "single_before": 20,
      "bulk": 20,
      "single_after": 20
    }
  ],
  "error": "Native zero target did not remain confirmed",
  "captured_at": 1793943416.6476579
}
```

Parsed request metadata (no private frames):
```json
[
  {
    "time": "2026-11-06 06:36:46.477",
    "seq": 66,
    "function": 3,
    "address": 0,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:46.578",
    "seq": 67,
    "function": 3,
    "address": 98,
    "count": 14
  },
  {
    "time": "2026-11-06 06:36:46.679",
    "seq": 68,
    "function": 3,
    "address": 130,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:46.780",
    "seq": 69,
    "function": 3,
    "address": 142,
    "count": 36
  },
  {
    "time": "2026-11-06 06:36:46.935",
    "seq": 70,
    "function": 16,
    "address": 104,
    "count": 1,
    "values": [
      1
    ]
  },
  {
    "time": "2026-11-06 06:36:48.013",
    "seq": 71,
    "function": 3,
    "address": 104,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:48.114",
    "seq": 72,
    "function": 3,
    "address": 586,
    "count": 123
  },
  {
    "time": "2026-11-06 06:36:51.082",
    "seq": 73,
    "function": 3,
    "address": 104,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:51.183",
    "seq": 74,
    "function": 3,
    "address": 98,
    "count": 14
  },
  {
    "time": "2026-11-06 06:36:51.284",
    "seq": 75,
    "function": 3,
    "address": 104,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:52.850",
    "seq": 76,
    "function": 3,
    "address": 62,
    "count": 3
  },
  {
    "time": "2026-11-06 06:36:52.951",
    "seq": 77,
    "function": 3,
    "address": 210,
    "count": 14
  },
  {
    "time": "2026-11-06 06:36:53.059",
    "seq": 78,
    "function": 3,
    "address": 500,
    "count": 59
  },
  {
    "time": "2026-11-06 06:36:53.260",
    "seq": 79,
    "function": 3,
    "address": 586,
    "count": 123
  },
  {
    "time": "2026-11-06 06:36:56.355",
    "seq": 80,
    "function": 3,
    "address": 104,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:56.456",
    "seq": 81,
    "function": 3,
    "address": 98,
    "count": 14
  },
  {
    "time": "2026-11-06 06:36:56.568",
    "seq": 82,
    "function": 3,
    "address": 104,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:56.698",
    "seq": 83,
    "function": 3,
    "address": 146,
    "count": 32
  },
  {
    "time": "2026-11-06 06:36:56.838",
    "seq": 84,
    "function": 3,
    "address": 340,
    "count": 1
  },
  {
    "time": "2026-11-06 06:36:56.939",
    "seq": 85,
    "function": 3,
    "address": 212,
    "count": 8
  },
  {
    "time": "2026-11-06 06:36:57.039",
    "seq": 86,
    "function": 3,
    "address": 98,
    "count": 14
  }
]
```

Final observed runtime05:37:15UTC healthy/automatictrue. Lease release verified; tracing left active as owner requested, bounded15min. Next isolate other writer paths before device/firmware attribution.
