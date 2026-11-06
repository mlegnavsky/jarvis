# Energy1.0.6 — next best daily sale readiness

Adds a read-only tomorrow price-plan state, retaining completed-day proof separately. Ready means all published Prague-day quarters are present, unique and finite and the best configured contiguous positive-net window has been chosen. Missing/stale prices mean waiting; a complete day without a qualifying positive window means no eligible window. This is price-plan readiness, not a promise of battery energy or hardware readiness; all existing actual-start guards remain.

The prepared plan is persisted for midnight, and revalidated against the complete current-day optimum before promotion. A corrected or incomplete old plan invalidates an earlier autonomous selection too, allowing the ordinary chooser to use current data. Explicit one-day overrides retain priority and completed days cannot reenter. The read-only report computes fresh readiness even while execution is paused or another sale is active. Calendar-day logic covers23/25hour DST days.

The Spot hub shows next-day start/end and average net CZK/kWh after fee, waiting/no-window and automatic-off/inhibited status. Existing inverter/SOC/BMS/current protections, archive and watt accounting are untouched. House/battery/grid meter reconciliation remains a separately requested batch.

Verification:772 Python tests run,752 passed,20 existing optional PHP skips,0failures. Pure/DOM hub, power formatting and Czech diagnostic Node suites pass. Added red-green tests cover incomplete and duplicated prices, optimality after corrections, midnight promotion of an already-selected day, stale read-only report and completed-day preservation. Installation and actual operational observations are private receipts. No forced surplus or planned battery sale was started for testing.
