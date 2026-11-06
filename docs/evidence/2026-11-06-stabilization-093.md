# Energy stabilization 0.9.3

This release is a targeted stabilization of HA-controlled battery sales, separate from the planned broader refactor.

- Automatic HA sales preserve the inverter schedule, SOC floors and configured current limits; only export mode and cap are controlled.
- Automatic windows start inside the authorized business block without native five-minute alignment. Manual native commissioning retains its existing compatibility path.
- Structured read-only health reports identify missing, unavailable and stale measurements separately from temperature limits, active charging and device faults.
- Failure evidence retains the original sample, electrical timestamps and price. Only documented transient automatic battery measurement failures can recover after confirmed cleanup, no conflicts, stable healthy telemetry, valid owner intent and an independent idle-profile audit. Ambiguous legacy battery-health failures remain inhibited.
- A dated one-day business-window exception validates complete positive end-exclusive price coverage, preserves recurring policy and prevents a second scheduled battery block after its end on the same day. The next day ignores the exception.
- Existing SQLite schemas, event IDs, financial records, archive queues and saved-transaction cleanup remain compatible.

Validation: 704 tests completed with 20 optional skips and no failures. Regression coverage includes prompt HA start, short remaining windows, health evidence, original electrical timestamps, strict recovery-proof validation, end-exclusive prices and dated override expiry. Independent review findings were resolved and covered by tests. Release manifest and whitespace checks pass.

Private deployment receipts and operational history remain on the installation; no household runtime logs, backup identifiers, credentials or one-day production configuration are included here. Full physical end-of-cycle and subsequent outage-recovery acceptance are separate from offline regression success.
