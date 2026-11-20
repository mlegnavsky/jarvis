# TV noise and question follow-up investigation

Owner observations: Jarvis wakes during TV silence but not loud playback; after an assistant question the terminal stops accepting an answer. Treat these independently from the shared-volume repair. Preserve silent successful light actions, explicit activation during TV playback, private recordings/models, and device mute.

- [x] Finish and verify the already-running shared-volume deployment; do not replay it.
- [x] Add bounded read-only diagnostics of the single allowed firmware YAML (audio channels/gain, wake VAD and sensitivity overrides, assistant lifecycle action names); never expose YAML, lambdas, URLs, credentials or recordings. Capture whether an intent asks a question and whether continuation was actually enabled.
- [ ] Verify diagnostic filtering with secret-bearing fixtures and install it through the normal revision-bound release path. Compare actual firmware configuration with pinned native behavior before changing wake parameters.
- [ ] Reproduce the specific follow-up failure with deployed source and tests before changing behavior. Preserve no-speech timeout, explicit stop, quiet light success, permission checks and conversation identity.
- [ ] Publish and deploy only demonstrated repairs. Read back active runtime, configuration, output completion and follow-up events. Record acoustic and user acceptance limits in OPEN-WORK; release the deployment lease.
