# Native charging-button state feedback

Source65643f02734cddba273512cfbc5d205c05076a46 adds native conditional tiles driven by sensor.jarvis_spot_control. idle green/start allowed, starting amber/no action, running blue/no action, restoring amber/no action; any other state red/unverified/no action. Both tile and icon taps disabled outside idle; existing stop-and-restore remains available. No optimistic running state and no new custom component or backend/controller/restart changes.

Verified each of seven representative states selects exactly one branch; only idle can start. Python generation source compiles. Live view job charging-state-button-write-20261105 and parent refresh charging-state-parent-refresh-20261105 verified with exact full readbacks. Parent mtime refreshed to invalidate included-YAML cache. Live controller running at05:46UTC; physical test was started by owner, not by this UI task. Phone rendering unverified.
