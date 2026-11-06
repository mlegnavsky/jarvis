# HA sale reserve 0.9.1

Owner explicitly requested that automatic battery sales preserve the inverter's ordinary 30% SOC schedule. HA alone stops export at sale_soc (60% by default) or the segment deadline. Automatic production no longer writes TOU times, powers, SOC, weekly mask, charge flags or configured discharge current; it only controls export mode and cap. Commissioning/manual native-window behavior is unchanged. Automatic admission reads the native clock without synchronizing it.

Live sales0.9.0 at15:49UTC was idle/inhibited after start_failed with `_Guard: native_mismatch`, with stop_verified=true. The generic translated message concealed that specific reason. All six ordinary SOC values were30. This does not prove which native register produced the original mismatch.

Two regression tests failed on old behavior: automatic preparation changed SOC30 to100/60, and did not issue a stop at the HA deadline. Both pass after the change. Targeted44 tests pass; full pinned test environment682 tests pass,20 optional skips. Earlier runs in the generic runtime failed because native modules/dependencies were absent; rerun used the pinned dependencies plus voluptuous and explicit native-module paths.

Deployment and physical export verification pending; source publication alone is not deployment. A loss of HA can allow export to continue down to the unchanged inverter reserve30; the HA60 threshold is not a native fallback.
