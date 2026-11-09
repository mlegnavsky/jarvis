# Coupled manual heating and grid charging

Owner requirements: explicit button bypasses only50% radiator admission. Grid supplies heaters and simultaneously charges battery approximately1000W. Never lower native30% minimum. Stop at shared child sensor>=24C or owner'soff; lastmanualheateroff restores all prior native settings. Two rooms share one charge session. Keep nativeBMS/temperature protections and existing175A standalone test untouched.

Implementation: extend existing owned charge Controller with separate heating purpose; persist snapshot before nativewrites, ~19A from livebatteryvoltage, temporary active-slot goal>=90/Grid (raising a charging target rather than lowering30% reserve), handle slotrollover. Share existing sale/charge mutual exclusion, CASrestore only touchedvalues (GridDisabled before restoringhighercurrent), preserve conflict for reconciliation. Heating ChargeLink requires fresh physical gridimport and negativebatterycharge before ON, independentwatchdog, diagnosticreport. Fix faulty exact30SOC gate; noinstantstartup-power trip.50%ordinarymanual remains protected.

Tests: policy bypassSOC30–49/risingSOC/24/stop/cooldown; chargingwattplanning/durability/partialfailure/rollover/targetreached/sharing/CASconflict/recovery; adapterchargefailurebeforeON/sharedlaststop/cancel-before-arm/stale watchdog; measurementlinkfreshness. Independentreview beforedeploy. Publish throughGit expectedHEAD and CASbundle with backed-upCore restart. Verifyruntime1.3.1/charger0.6.7, exactfiles, then inspect diagnosticreport/physicalproof without falsifying temperature.

State: implementation prepared; deployment pending. Original exact tripcause was not recorded in1.3.0; do not pretend historical cause confirmed. Newlaststop/report preserves it. Native charging target is temporary and restores original30% programme; no promise exactly1000W or safe operation during HAoutage.

Implementation and review complete:778root tests/20skips,59heating,4UI passed. OFF-save/externalOFF/watchdog-blocking/flowproof regressions fixed. Deployment and physicalacceptance next.
