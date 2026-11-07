# Solar history 1.1.2 Implementation Plan

> **For agentic workers:** Execute inline using superpowers:executing-plans; one fresh review before deployment.

**Goal:** Keep the owner-approved native 20W import offset, automatic PV surplus and weather-reserved scheduled battery sales; persist monitoring and daily evidence across restart.
**Architecture:** Reuse the existing permanent SQLite sales journal and private 10s remote archive. Add bounded five-minute daily snapshots and a read-only date query/UI; restore incidents from the same journal. Existing load/PV learning reads real archive days; do not fabricate old data or weaken reserve policy.
**Tech Stack:** Python, Home Assistant, SQLite, vanilla JS.
**Spec:** Owner request in this session, existing ENERGY-DATA-MAP and live WORK-MANIFEST.

## Global Constraints
- Native import target20W accepted; no negative target/firmware change/tiny-export mode.
- PV97%, battery owner minimum60% plus existing weather reserve, house floor30%, max9300W remain.
- Keep old data, gaps and partial-day labels; losses are an algebraic residual, not measured efficiency.
- Publish source; CAS deployment, backup and runtime verification before completion.

## Review Focus
- Restart must retain incidents without claiming current faults from old history.
- Missing/stale counters or finance must remain unknown; no zero fill.
- Date boundaries follow Europe/Prague including DST; bounded read-only API requires admin.
- Five-minute snapshots are instant readings/daily counters, not five-minute power averages.
- Automatic owner intent restored only after confirmed healthy idle profile; native104 must stay20.

### Task 1: Approved target and durable evidence
- [ ] Add regressions for20W target, incident restoration, journal interval idempotency, stale and partial daily evidence.
- [ ] Verify RED, implement minimal changes, run Python suite.
- [ ] Add authenticated daily summary view and UI using selected date; test malformed dates/missing days.
- [ ] Preserve existing planning learning and expand archive raw electrical evidence (internal/external/AC) for later audits.

### Task 2: Verify and deploy
- [ ] Run Python, Node UI and release checks; independent review.
- [ ] Publish isolated branch and deploy with current revisions and backup; verify running versions/files.
- [ ] Restore owner automatic request, verify20W native offset, no tiny-export branch, healthy profile and archived evidence.
- [ ] Update private live manifest/receipt; report actual limits and current reserve.

## Ledger
- Initial evidence: native10420; idle healthy1.1.1; owner OFF confirmed from isolation test; archive uploading after reconnect.

- Task1 implemented: target20, durable incident restore/events, idempotent300s summaries/read-only date API/UI, raw archive AC+internal+external additions. Existing weather/load learning unchanged.
- Review P2 native failed refresh falsely confirmed old20: added target_confirmed using last successful native_program.captured_at,90s parameter freshness vs unchanged30s electrical guard. RED then GREEN.
- Review P2 delayed midnight reset: daily nonzero counters require last_changed since local midnight and plausible elapsed-day totals, matching existing finance evidence. RED then GREEN.
- Ruling: five-minute records start with this release; existing10s remote archive and HA history remain intact. No old daily summaries fabricated; UI labels partial evidence.
