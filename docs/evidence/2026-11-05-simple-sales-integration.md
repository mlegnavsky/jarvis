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

##0.6.0 deployment and first new-controller attempt

Release0.6.0 source94351fe9a3e0be28e5985d4931f68837088ae2ec/tree285f3c83ac81b91861c059fd709233353ea34192 deployed with backup61794d32 and runtime checks verified18:28:58UTC. A transient Solarman timeout18:22 cleared after the restart; new controller was ready and healthy with SOC94%, PV0, house battery demand around300–400W.

Command owner-native-battery-v060-500w-20261105 at18:30:18UTC was rejected before actuator preparation: the BMS maximum exceeded the helper's200A input validation. No new-controller export occurred. Automatic mode was off afterwards. The manufacturer200A physical cap must be a minimum against valid BMS reports, not a reason to reject a larger reported BMS maximum.

The installed deye_p3 profile identifies213 as BMS discharging-current limit and219 as BMS maximum discharging current, both1A scaling. Revised controller requires both raw fields, rejects0/65535, and uses min(213,219,200) consistently for native preparation, periodic audits, current writes, restoration and final proof. User175A and commissioning20A remain additional lower caps. Native diagnostics now expose both raw values for independent acceptance before another physical attempt.

The same maintenance release adds only fixed native104=0 bias maintenance (no mode/export-limit changes). Ordinary ZeroCT/ENoff/uniform house program and exclusive fresh healthy control are checked before and after the durable audit inside the transport lock. Three native readbacks, including delayed independent reads, must confirm0. Generic HA optimistic0/1 acknowledgements were previously insufficient. Negative/wrapped register values are not used.

Automatic battery segments are now clipped at23:40 local to leave recovery slots before midnight; an unrepresentable short remaining window waits instead of inhibiting the next day. The sale-energy budget still uses the full selected price block.

## Verified0W bias and final operating ceiling

Release0.6.1 activation verified18:43:02UTC with backup6af0a621. Raw213=250A and219=270A confirmed as reported ceilings, not actual current. The physical pack cap200A and selected175A remain lower. First native-zero maintenance expired before its profile snapshot during a Solarman timeout; no write intent occurred. Following recovered healthy measurements, retry2 confirmed register104=0 with three native reads[0,0,0] at18:46:48UTC (previous20W). Current instantaneous grid values can still fluctuate; the configured native target is physically confirmed0W.

The final operating export ceiling is9300W, below the9500W contract. No new mutable automatic-power setting was retained. Commissioning remains GRID500W/5minutes/SOC90; its battery ceiling is now min60A/prior/BMS and min3000W/prior/current×voltage, to accommodate measured ordinary house demand around1923–1987W without switching household appliances off. Normal operation retains user175A/manufacturer200A/10kW and lower BMS caps. Actual current and DC-power guards remain active. Battery commissioning must still prove export, native end and complete restoration before automatic acceptance.
