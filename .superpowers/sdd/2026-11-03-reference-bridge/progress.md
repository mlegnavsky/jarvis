# SDD ledger — plan: docs/superpowers/plans/2026-11-03-reference-bridge.md

Base localab276d43/public9e1d4a2831ba8b784158dfe2058f6167ce7ecd46 exacttree53390687. Existing linked worktreefix/echo-measurement-20261102 verified. Native1.3.5 remains unchanged.
Ruling: owner accepted concrete synchronizedbridge proposal and previously opted out of repetitive design questions; continue inline without anotherapproval — implementation/deploy consent persists — cost: local implementation choices recorded here.
Ruling: nativeprotocol sender timeline doesnotboundactualHomePod DAC offset; calibrationunknown isexplicit and cannotenablefastinterruption — primarypyatv/receiver evidence — cost: acousticactivation waitsforrealproof.
Preflight: Task1timedPCM/clockbounds consumedbyTask2endpoint; protocolrate andepochmustagree. Task3cannotactivatebeforeTask2compileandDMAfaultproof.

Task1 core complete: actual nativepyatv0.17 StreamClient/RaopStream+miniaudio verified bigendian352frames, finalpartialpadding andEOFsilence, ownerCASrestore/unknownsend/queuebound.10timing+7taptests REDmissing->GREEN; full282duplex tests9.062sGREEN. No runtimebinding/deployyet.
Ruling: use official Sendspin2026.10.1/sendspin-cpp0.9.3 andaiosendspin[server]10.3.0 fortransport+drift insteadinventingnativePCMclockprotocol — maturepairedNoise channelwithpublicPushStream explicitPTS — cost: fixedtargetfirmwareendpoint andstrictmute/ownership+timingfaulttelemetry stillrequired. OfficialCore2026.6.4 constraints compatibleall23CPython3.14muslaarch64wheels; noCoredependencyupgrade requiredbyranges. Receiverphysicaloffset remainsunknown; noPCM/microphone opened.

Task2 implementation complete for review: pinned ESPHome2026.10.1 / SendspinCPP0.9.3 / aiosendspin10.3.0; silent I2S gate with DAC-confirmed mute, amp off, generation ownership, discard-vs-DMA accounting, actual native stop/empty/stream-closed ACK. Both fixtures compile; UBSAN and actual overlay-codegen checks pass. Final hashes/memory/limits in firmware/reference_bridge/build-proof.json. Installed full package and physical DMA remain untested.
240s transport run preserved FALSE (clear coalesces into end); 9541 chunks, zero mismatch/late/stale. Separate clear-only proof passes but local drain is not receiver ACK. Actual-module encrypted SDK integration passes7.571352s/181chunks/217200frames,44.1→48k; native endpoint/counters/ACK simulated. No new mic/HomePod/house operation.
Task3 code complete for review: fixed firmware_reference_stage with source-CAS/allowlisted repo/profile and exact private-byte preservation; encrypted native endpoint; bounded generated-only probe with two generations and cancellation cleanup; control one-shot; default production reference remainsOFF. Added four HA binding tests. Native1.3.6/addon3.12.3 candidates only.312duplex pass9.602s;246addon pass20optional skips7.438s;manifest/diff pass. Whole-change read-only review running once; no deployment.
Ruling: prepare/publish/CI before requesting the one missing destructive action. Fresh preflight:1.6GiB<2GiB backup threshold; no active lease/jobs, native1.3.5 unchanged. Local manifest permits deletion only explicit approved slugs. Preview candidates ba75b0ef708.05MB and9edc3711710.38MB are oldest eligible large backups; latest3 andprotected27122c9a retained. No new deletion authorized or performed. Single removal insufficient for subsequent required backups.
Remaining: review findings, exact Git CAS publication/CI, explicit approved cleanup, addon update to read safe installed-package facts, profile compatibility/compile, backed-up native+firmware activation and one silent electrical probe. Acoustic alignment, receiver latency, human barge-in and one-second dialogue response are still open. Do not claim the original stutter solved.

Review correction: stock_sendspin staging is now explicitly rejected before any
write because its experimental listener replacement silences normal Sendspin
media. Its YAML/fixture remains a build-only experiment, not a deployable profile.
Only legacy staging is allowed, and exact installed-package compatibility remains
a required compile gate. Review also found and corrected zero-progress callback
busy-loop and HA initialization/probe ownership race. Full review/rulings are in
docs/evidence/2026-11-03-reference-bridge-review.json.

Final host checks after the review fixes:314duplex tests10.259s PASS;247addon tests7.562s PASS(20optional skips); manifest and diff checks PASS. No live activation.
