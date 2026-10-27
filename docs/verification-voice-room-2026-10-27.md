# Voice terminal room correction — 2026-10-27

User clarified that the functional hall Voice PE was physically moved into the living room. Main3.5.0 adds native registry metadata updates with revision checks, a durable before-image and verified readback. No device identifiers, pairing, firmware or credentials are changed. The fixed automation reload operation requires the current file revision and calls only automation.reload.

-147 tests passed locally and in CI; manifests/diff checks passed.
-CI40477200605: tests and both container jobs successful. Source d0b8769986ca44cc1943240bbab639e7375540d5.
-Deployment623b2b6408024b9f915d7a1f4d553c09 verified; backup fc945301.
-voice-room-move-active-20261027 verified living-room area and display name.
-voice-room-move-old-20261027 verified removal of obsolete room assignment and distinct disconnected-device display name.
-voice-retarget-automations-20261027 verified two exact device and entity registry reference replacements. Durable file before-image retained under that job ID.
-voice-automations-reload-20261027 verified synchronous reload and unchanged target revision.
-Final registry map: functional terminal entities inherit living room, old device has no area. States: satellite idle, microphone mute off, Hey Jarvis selected, display names updated. Both existing automation states on.

The existing automation behavior (volume targets/delay) was preserved. No audio was played and no physical acoustic or volume-cycle test was induced from the office. The exact preferred speech pipeline and whether the legacy Core is needed are separate unanswered audit items. Neither legacy Core nor old device records were deleted.
