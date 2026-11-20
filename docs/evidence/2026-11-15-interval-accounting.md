# 15 November 2026 — timed-meter accounting and all period charts

Owner requested a complete repair after Nov14's 6.2 kWh export was shown as 0.65 kWh / 2.35 CZK and period charts failed to refresh.

## Implemented
- Authenticated private archive materializes closed-day revenue from timestamped increments of the daily export meter, dated OTE publication rows and 0.30 CZK/kWh fee. Purchase uses the 5 CZK/kWh tariff.
- Coarse increments spanning differently priced quarters are not silently assigned an invented price. Missing prices, counter resets, missing initial export, and no near-midnight meter measurement keep final totals partial.
- Cached per-day results rebuild when raw samples/prices change; at most four cold days build per archive status. Original samples are unchanged.
- The hub loads accounting.js before hub.js, uses the archive daily ledger, caches period views, renders separate monetary graphs for day/week/month/year, and forces energy-chart redraw on selection.
- Unknown monetary values stay missing in chart grouping. Data before archive coverage stay explicitly partial. Historical whole-day revenue never falls back to the old partial monetary sensor if interval accounting fails.

## Deployment evidence
Production source 1ad2fb9ff4c66b5923c48e6979850ea447eb8b5d. Admin finance-accounting-prepare-20261115 / finance-accounting-apply-20261115 verified file_written, activation none; no Core restart or inverter/heating/sale-setting change. All three files independently read back exactly:
- www/jarvis-accounting.js fe0b930c6e5e1916af0bd7e7031cacbb179baf62dc5a3402816887c65d030c97
- www/jarvis-spot-hub.js 0f2f4a611611cf6b20381a9f999eb5765b70baa185f86d00e814ff4973e57566
- www/jarvis-spot-hub.html 8baa988ebc72b7cef21bf80bd1b57fa6fad1bd98074c0b23b7c881a379ea1601

Archive CI run43713239218 / job132809182915 passed PHP HTTP and JS accounting tests, published lab commit c195de0, and received accepted existing Plesk webhook response. Live finance.php HEAD200 and index.php HEAD401 confirm code-file presence and retained authentication; they do not reveal private day totals.

## Verification and limits
Local23 PHP/private WebDAV tests pass with native PHP8.2 + SQLite and pinned aiowebdav2; six targeted JS suites pass. Tests include time-matched revenue for6.2kWh, differing quarter prices/fee, incomplete pricing, archive fast path, missing days, null bars, midnight coverage, finance history, passive DOM and existing energy charts.

The new desktop/mobile browser acceptance uses explicitly synthetic ledger values; they are never actual household revenue. Executor Chromium launch is blocked by socket EPERM. Existing full CI at1ad2fb9 also fails due pre-existing Playwright1.58.2/ubuntu26.04 incompatibility and missing Python test dependencies (including voluptuous), plus test_accepted_autonomous_proof_restores_request_but_manual_or_failed_proof_does_not and test_inconclusive_pv_only_or_recovered_interruption_resumes_small_mode_with_bounded_cooldown assertions. No control policy was modified to silence them. Browser accounting verification runs separately on ubuntu24.04; see next source2115c2548863fad7a0f1d1a366e715fb8771a549.

Actual Nov14 recomputed total and production browser latency are NOT independently read back: the connector exposes only stripped state attributes, and the separate browser is signed out. Backend direct management remains functional; owner must not be told their permanent connection is missing. Existing open clients need refresh. Do not assert a measured exact total or measured latency from synthetic tests. A future private archive diagnostic snapshot would close this read-only observability gap without collecting credentials.

First supported-browser run43713738601 reached real DOM and found an ambiguous test selector (main period navigation and embedded graph both matched). The test now scopes selection to .trading-head; deployed product code unchanged. Retest pending.

Supported-browser retest PASS: source8585fb6529cd37009e6537697b942b6931d35ba5, run43713880010/job132811118869. Actual Chromium rendered synthetic yesterday6.2kWh/21.7CZK and week/month/year money+energy SVGs; each archive-backed selection completed under2seconds in this fixture;390px mobile chart visible, zero page errors/device writes. This does not benchmark production data latency or establish actual Nov14 revenue. Existing private server code unchanged; subsequent publish/hook job also success.

Final review0c54a70799f6ddb7d8aea653e460ad97633bdb03 corrected receipt-vs-measurement quarter timing, unknown revenue incorrectly shown as zero, native current-day unpriced coverage, and import-counter resets. All regressions observed failing before fixes;26 PHP+6 targeted Node suites pass. Independent review re-ran7 archive tests and2 accounting suites and confirmed all fixes. PHP materialization table v4 invalidates earlier cached calculations. Frontend accounting CAS write finance-accounting-reviewed-20261115 VERIFIED; exact independent readback ebf1ce0073be51e857cf23704ad9388242e286d95d72ea63219a1fac43e4a3f6.
