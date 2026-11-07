# Light command switches implementation plan

Goal: independently enable standalone rozsviť and zhasni in the Automation view.
Scope authorized by owner: these two commands only; defer TV, heating and other commands.
Architecture: persistent input_boolean helpers gate new direct-wake runs before STT; explicit Jarvis conversation and existing media/identity guards remain unchanged. Firmware models remain loaded; disabling blocks handling, not acoustic detection. An already accepted run may finish.

- [ ] Test disabled/missing controls block only their own direct command; normal Jarvis and media protections unchanged.
- [ ] Add two helper entities and an Automation card, preserving surrounding live configuration.
- [ ] Publish source against fresh Git HEAD; deploy with CAS, backup and Core restart.
- [ ] Verify both helpers, versioned runtime gate, file hashes; household acoustic test remains deferred.
