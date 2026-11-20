# Conversation stability and enrollment trigger repair

User reports false wakes, output interruption closes listening, and no voice
profile after explicit enrollment attempts. Live report confirms profiles0 and
no pending enrollment after a short initiation phrase. Coordinator wrongly
required usable embedding even to BEGIN registration, although it never counted
that phrase among the three samples. Remove that prerequisite; retain three
consistent samples and all matching thresholds. Missing-name and status commands
must receive deterministic local replies, never invented model success.

On native ESPHome abort during owned active HomePod playback only, stop output,
await native task cleanup, then resume once with native silent announcement.
Preserve current conversation ID; the HA internal start_conversation service
would intentionally create a new one. Guard same owner/conversation, current
pending continuation, confirmed stop, available/unmuted/running device, no new
pipeline or announcement. Errors/generic cancellation/replacement/explicit end
never reopen listening. Not an acoustic arbitrary-speech detector.

Temporary device settings: legacy Jarvis wake slot disabled; other slot was
already disabled. Wake sensitivity Very→Slightly. Begin by physical button.
Do not label existing weights as Aničko or claim false-wake rates measured.

Verification: short enrollment command and missing-name/status regressions RED
then GREEN;26 speaker tests. Six abort/resume regressions plus existing HomePod
tests32 pass. Untouched migration test missing local Jinja2; full CI with project
dependencies must pass before activation. Independent review no findings; actual
native resume/audio is owner-side acceptance. Deploy source+recovery copies via
CAS/backup/restart; verify runtime markers and no fabricated household profile.
