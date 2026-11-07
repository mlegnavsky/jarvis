# One-call light toggle — live verification 2026-10-27

Jarvis3.4.0 resolves light.toggle from a fresh on/off state inside the existing serialized action executor, sends an explicit turn_on/turn_off once and confirms the target locally. Both underlying service permissions and an allowed light entity are required. Nonbinary/unavailable states and extra parameters fail closed. The original toggle request is fingerprinted before resolution; durable replay returns the historical response without another physical command, including after restart.

Automated:145 tests passed, including both directions, denied permissions, unavailable/nonbinary states, extra data and retry after process recreation. Release manifest checks and diff checks passed. GitHub Actions40474606050: tests and both container builds/startup checks succeeded. Source commit3e0967982a4cdcb89bb1390e180b385b68207bca.

Deployment job c517b7664ba4452e872e373e22227731 reached verified; backup592dbefc. Status confirmed Main3.4.0, connected to HA, independent gateway1.0.0.

Live acceptance using the existing connected plugin, without a preceding inventory:

- light.toggle off→on: tool round trip734ms, Jarvis request208ms, confirmation140ms; target_state_verified=true, replayed=false.
- Same request_id replay: replayed=true, no second toggle.
- Separate deliberate toggle on→off to restore initial state: tool round trip1139ms, Jarvis request270ms, confirmation207ms; target_state_verified=true.

These are tool-call measurements to HA state confirmation, not Enter-to-photon measurements. Client input timestamp and independent physical-light sensing are unavailable. No sub-500ms end-to-end guarantee is claimed. Normal explicit turn_on/turn_off commands also need no preceding inventory for a known entity. Physical state can change concurrently outside Jarvis; HA confirmation is an observed state, not a permanent guarantee.
