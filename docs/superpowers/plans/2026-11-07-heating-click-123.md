# Heating click1.2.3

Owner request: clicking radiators off must mean stop until Prague midnight, with no immediate false control error.
Evidence: both live switches off but room sensors only cooldown; current1.2.2 adapter can swallow an owner state report matching an automatic pending command. It immediately declares a control error before asynchronous switch confirmation. Explicit set_mode(off) already persists day hold, independently verified live for both rooms via bounded one-shot native automation; remove the temporary helper after confirmation.

Plan: reproduce user-context/pending collision and delayed confirmation; call explicit room set_mode from radiator floorplan buttons; persist explicit intent before physical command;15s acknowledgement grace and bounded retries without relaxing safety; owner user context takes precedence. Label hold Stop pro dnesek. Preserve all heating thresholds/settings/manual holds, tomorrow automatic return and unrelated click actions.

Tests RED→GREEN:31 heating tests and new JS owner-intent test. Run project suite, independent review, publish source, CAS install and one backed-up Core restart. Verify both Stop pro dnesek/off after restart, solar1.1.2 preserved and owner sales intent restored if maintenance stop needed. No physical on test.

Resource cache: startup updates only the existing /local/jarvis-home-status.js resource to?v=heat123 through the official HA2026.6.4 ResourceStorageCollection API. No raw.storage editing. Dedicated status sensor exposes success/error; failures do not block heating control. Two RED→GREEN helper tests check idempotency and preserving other resources.
