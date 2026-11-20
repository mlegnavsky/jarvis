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


## Reference candidate published; physical activation blocked —3Nov2026

Supersedes the publication-pending notes above. Public source
54e9bce5d634e34197528ec565d1ed10b98dd01a/tree746ed1ff5d27a67f0f9dd1547842ef33287c5e06
exactly matches local322a390072d8708f17aa81d3ba1d71071849733f. Push CI41646159996
completed13:43:08UTC; all8jobs passed including both firmware fixtures, both
containers and publish-laboratory125954034069 (immutable package/catalog steps
not skipped). No live update, firmware install or microphone test was performed.

Fresh live report13:39:16UTC: native1.3.5/d98/configured/adapteractive/Core2026.6.4,
no active dialogue and room isolation false. Storage still1.6GiB versus2GiB
mandatory backup minimum. Source/proof and exact proposed two cleanup candidates
are in docs/evidence/2026-11-03-reference-bridge-proof.json. Cleanup authorization
remains missing for ba75b0ef and9edc3711; none deleted. Preserve newest3 and
protected27122c9a. Ask only this concrete destructive scope; existing Git/update
consent persists. After approval recheck retention/CAS/space, delete only named
backups, then update addon3.12.3 to read safe installed-package metadata.
Stock_sendspin is explicitly NOT supported for staging; legacy needs exact
private-target compile before install. Native1.3.6 and silent device probe still
not activated; timed physical alignment and acoustic acceptance remain open.
Do not repeat old room134 consent, old135 apply, or the frozen240s experiment.

Ruling: owner freed backups/explicit free hands; fresh6.7GiB/unlocked. Addon3.12.3 verified updatef1471f98971d4b7eb4636dba7065e58a/backup0996fed9; fresh3.12.3connected. No more cleanup needed.
Ruling: actual official no-ref package discovered in user's earlierfile; narrowparserfix3.12.4 RED→GREEN allows absentref asnull. Officialdefaultdev d4e6fa43 inheritsstock, top_level_sendspinfalse is insufficient. Legacyduplicateplayer failure reproduced; no blindstage/install.
Ruling: preserve stock by listener delegation gated by compile-time PUBLIC reference-server identity, known before anyconnection/reboot. Host creates stableprivateidentity onGreen, exposespublicid only; fixedstageinjectspublicid. This avoids extra nativeprovisioning/NVS and prevents unarmed referencePCM being mistaken fornormal. Existing4nativeactionsunchanged. Newbounded firmware compatibility task can runparallelto independenthost/admin changes; root retains deploymentownership. Cost: onefocusedreview andfreshcompile required beforeenablingstockstage.


Stock compatibility continuation: owner says backups deleted/freehands; fresh6.7GiB/unlocked, no assistantdeletion. Jarvis3.12.3 updatef1471f98971d4b7eb4636dba7065e58a submittedonce andverified, backup0996fed9, freshversion3.12.3connected/storage6.6. Native1.3.5/d98 untouched; nofirmwarewrite/leaseyet.
Actualuploadeddeviceconfig hasofficialURLwithout@ref; optionalrefparser bugfixedRED→GREEN for3.12.4candidate. Officialdefaultdev d4e6fa43 inheritsstock; legacyduplicateplayer reproduced, so do notstagelegacy. Newfirmwarestockrouting fixedpublicreference_server_id atboot, preservesnormalstockcallbacks/codecs/delay/unpairedpolicy/32bitnormalmixer; staticidentity avoidsunarmedreferencebecomingaudible.
Roothostcandidate1.3.6 addsreference_identity control120s (noendpoint/network/mic) tocreate/loadprivatekeyonGreen andreturnpublicid; stage3.12.4 requiresreference_server_id43base64url andsupportsstock. Root317duplex/249addon20skip GREEN; stage7testsGREEN; updatedCIrunsstock_adapter_test.py/hub_config_test.py. Newcriticalgoalproofstillnotperformed.
Agentreference_stock_coexistence ownsfirmwareonly; bothminimalbuildsPASS, fullimmutableofficialpackagebuildrunning; sourcecounterfixafterself-review pendingtoavoidmetadata-callback teardownwaitonownstack (endmustwaitPCM-only; allcallbacksblockarm). Agentreference_stock_review found0Critical/Important ininitialfrozendelta andwillcheckonlynewcounterfix; report .superpowers/sdd/2026-11-03-reference-bridge/stock-integrated-review.md. Fullbuild+finalbuild-proof.json mustcompletebeforepublish.
PublicHEADstill54e9bce (all8CI41646159996passed,labpublished); localHEAD2e7041d containsUNPUBLISHEDdocumentationcheckpoint. Current3.12.4+stock+nativeidentity changesuncommitted. NoextraapprovalneededforGit/update/deploy. Nativepayload /tmp/reference-native-deployment/prepare-call.json fromhelperisSTALE after3hostsourcechanges; preserveitsfreshCASbeforeimages, regeneratefromfinalpublishedsourcebeforeapply. Agentreference_deploy_preflight canrebuildit; nolease acquired. Expectedold8filelist __init__,control,manifest,5reference*.py; oldpostfingerprintdbbe575...NOT currentnewcandidate.
Next: finishcounterfix/fullbuild/targetedreview, finaladdonchecks/manifest/diff, commitallownedchangespluspublicproof, GitCASpublish against54e9bce (exacttree), waitCI; updateaddon3.12.4once/newrequestid andverify. Thennative1.3.6 viaexistinglease/bundle/core_restart andfreshfile/hash/runtime/nativeproof; runreference_identity(nohardware) toobtainPUBLICserverid; freshmetadata/sourceCASstageSTOCKoverlaywithexactpublishedSHA+publicid; compileprivateGreentarget, onlythenbackedupinstall/hashreadback; silentreference_probeonfreshnonce. No oldroommicrophone grant replay/clearing. Acousticmeasurement/fastbarge and1sgoal remainunproved.

Stock compatibility candidate complete for publication:317duplex and249addon(20optional skips) testsPASS. Bothminimalfixtures andFULLimmutableofficialVoicePEpackage compile PASS onfinalsources, includingreentrantcounterfix. All7compiledcomponentfiles byte-match inall3builds. Fullconfig91263d25/RAM149883/flash2847423; finalproofdigestda75271e24914d56a473972dcf245d03bc8bc96f0f6856829d4cf0e01b9833c3. Focusedintegratedreview0Critical/0Important, counterdeltaaccepted; allreviewlimitsretained. New3.12.4/1.3.6 source ready, NOTactiveyet. Nativepublicidentity mustbe preparedbeforestockstage. Existing3123active/0996fed9backup,6.6GiBfree. No furtherdeletionneeded; userfreehandsauthorizationpersists.
