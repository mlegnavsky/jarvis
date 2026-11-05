# Simple sale policy: implementation and acceptance evidence

The owner approved a simple first version: release PV surplus according to measured power, and select a contiguous favorable daily price block for battery sales. Prepare native registers from three minutes before the block; at one minute before the block and continuously afterwards use actual SOC and configured23.5kWh capacity, preserve a fixed60% sale reserve, subtract estimated household consumption and conversion losses, and spread the remaining energy over the block. Recalculate during the block. The default block is120minutes; every quarter must have a positive net price after0.30CZK/kWh sale fee. Complex weather/history estimates are informational and do not gate this first policy.

Native hardware remains bounded by lower inverter/BMS/configured current and power limits. A programming acknowledgement does not prove physical export or termination. Register146 is a weekly weekday mask, not a one-shot date. SOC100 outside native export windows provides a local fallback; connected cleanup restores the ordinary house schedule. This fallback can require grid household supply until cleanup and does not eliminate weekly recurrence if Home Assistant remains unavailable.

## Observed hardware before integration

-0.5.2 SellingFirst pilot18:00–18:05 Europe/Prague: PV0W, grid export501–511W, battery discharge613–627W, SOC96%. This proves actual battery export under the500W pilot cap.
-At18:05:20 the native transition was still decaying: grid export120W and battery246W. Connected stop began before decay finished, so native independent expiry was **not proven**.
-Connected stop and full native restoration verified18:06:13; a delayed independent read confirmed ordinary houseSOC30 across all six slots, no charging flags, ZeroCT, SolarSell off, maxsell9300 and maxdischarge175A.
-0.5.3 extends only the bounded SellingFirst decay observer to60seconds. A passing source test is not a hardware expiry result.
-Read18:02UTC:0.5.3 idle, healthy, automaticoff, battery95%, inverter36.5C, battery16.5C, PV0W, grid13W import. Native register104 remains20W; the desired0W import baseline is **not physically confirmed**.

## Integration checkpoint

New native controller, daily-block sizing, RTC synchronization and PV battery protection are under integration and independent review. No production unlock follows merely from500W export. Full regression and fresh physical acceptance remain required before a completion claim.

Fresh combined validation2026-11-05:537 tests passed in35.332seconds with pinned test requirements and the real rootless PHP runtime. This validates the source and adapters, not physical acceptance of the new controller. UI included views and parent cache refresh have verified byte readback; direct phone visual acceptance is not claimed.
