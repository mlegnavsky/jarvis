# HA autonomous solar operation —6 November2026

Source44370be7904b6a31647bb6258ac20a954e56d58c, sales0.8.0/heating1.2.1. Scoped ten-file deployment solar080-prepare-20261106/solar080-apply-20261106 active_verified08:55:05UTC; backup70dcbfb2; Core2026.6.4 unchanged. Ten SHA256 file readbacks matched before activation; native runtime checks salesidle/version0.8.0 and heatingversion1.2.1 passed. No backup deletion, no forced PVlimit, no Core/OS upgrade.

Owner heating values21/22 saved by verified heating21-22-child-20261106 and preserved throughrestart (revisionf74ff1d369b4b74ea5fb120bdb70876c78c1b28435d90e443d64d4d39a89f4d4). Both heaters already use common child-room temperature sensor; strict below21ON/above22OFF, holdboundary and existingSOC/solar/load/manualoff/stagger/cooldown preserved.

Durable requested_automatic separates ownerON/OFF from operationalpause. OwnerOFF clearspendingresume. HA5s loop owns boundedbias3min and battery2000W5min verification, completecleanup, proofgates and resume. Restartorphan independently audits ordinarynativeprofile+freshstoppedgrid, preserves unverifiedflags, cools30min; failedrestoration pauses/reports. Maximum2attempts/day. Battery admission requiresPV<=1700stable120s, SOC>=63, nominalenergyabove60>=0.3kWh, healthyfreshdata/capacity, safeclock/preparation and positive uniquequotes throughend. No claim of autonomous fullbatteryproofyet.

0.7.3 successfulbiasprobe later lost continuousproof and stopped08:10UTC despite actualtinyexport under changingPV. Reproduced strict20Wmean/timeout-since-start defect.0.8 measuredmean acceptance−50<=mean<0 aligns unchangedsustained>50W20s andinstant>302Wguards; noexport180s since lastconfirmedmean, not start. Requestedcap remains2W; exactphysical2W cannot be guaranteed.

Verification:638tests pass20skip,28heatingtests pass, manifest/syntax/diffchecks pass. Independent finalreview found no blockingissues; ownerintent/restartorphan, lateimportwindow and30Wregulation regressions RED→GREEN. No repeatedmass-test runs after finalsuccess. Archiveunchanged.

OwnerON inbox solar080-enable-owner-request-20261106 filewriteverified08:56:44UTC and consumedconfirmed. HA itself started biasprobe1793955407940399361, no manualtestcommand.08:57:32UTC healthytrue/phase running/observedtrue, requestedtrue/operationalautomaticfalse solely duringprobe/resumetrue, measuredmean−5.75W, noerror. Fullprobecompletion and latercontinuousstate recorded below whenobserved. StrongPV~6.1kW prevents meaningful boundedbatteryproof; HA will wait autonomously for suitableconditions. Large battery production remains gated byactual fullcycleproof, not an acknowledgement.

Existing today observer task Automation_261c3703fea08191a85ada33d0058245 updated to0.8.0 read-onlystatus/proofrules; existing14:45–18:45hourlyscheduleEurope/Prague retained. It must not enable/reset/starttests or substitute forHAoperations.

## Confirmed autonomous completion

HA biasprobe1793955407940399361 completed09:00:01UTC: reasondeadline, observedTRUE/sustainedTRUE/stop_verifiedTRUE,2Wcap/30floor, noconflicts/failures/error. HA itself restoredbaseline and then enablednormalautomaticbias;09:00:17UTC requestedTRUE/automaticTRUE/inhibitedFALSE/bias_verifiedTRUE/resumeFALSE, healthyTRUE/error empty. No additional command was sent toresume; only theoneownerON initiated thewholeflow. Currentnewbias wasawaitingfreshsamples, notyetlatchedobserved atthatinstant. Pendingbattery_verifiedFALSE with explicitwaitingreasonPV<=1.7kW; currentPV~6.1kW/SOC75. This is working HA-ownedverification/resume, not completedbattery-nativeacceptance. Existing scheduledobserverwillreportactuallaterresults withoutmutations.


Final09:01:07UTC continuousautomaticbias1793955603470585401 phaseRUNNING/observedTRUE, rollingmean−8.9W, requestedTRUE/automaticTRUE/inhibitedFALSE/resumeFALSE/healthyTRUE/error empty. Both physicalboundedtestcompletion and actualautomaticallyresumedcontinuousoperation are now observed. Batteryproof remains waiting. Deploymentlease releasedverified09:00:19UTC.
