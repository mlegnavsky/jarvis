# Confirmed interruption implementation plan

> For agentic workers: execute inline with superpowers:executing-plans, then one independent whole-change review.

Goal: own/rejected microphone transcripts do not chop HomePod; accepted human turns still interrupt without closing capture.
Architecture: Session owns an independent completed-utterance confirmation task while the existing answer plays. TurnBridge's current transcription filter runs before stop; accepted text is reused, never transcribed twice.
Tech stack: existing Python/HA2026.6.4 native HomePod transport.
Spec: docs/superpowers/specs/2026-11-02-confirmed-interruption-design.md

## Global constraints
Preserve all authority/TV/input guards, Marin/own volume and no raw recordings. No failed AEC experiment, firmware/provider/Core upgrade or one-second claim. Human interruption is endpoint/STT confirmed, disclosed in runtime/report and owner response. Git publication now explicitly authorized by owner.

## Review focus
- Echo rejected after onset must leave original playback alive and capture open.
- Human confirmation must use one STT result and existing fresh identity/service guards.
- Source EOF, explicit stop/mute and late provider results cannot rearm speech or actions.
- Playback finishing during confirmation cannot lose the new human sentence.
- Multiple candidates are bounded, serialized and newest completed correction wins.

## Task1: confirmation before cancellation
- [x] RED real Session regressions for rejected own echo, pending STT, accepted human/one STT, EOF/explicit cancellation, provider failure, natural output completion and superseded candidate.
- [x] Implement in managed_sources/local_duplex/session.py; add safe scalar counters/policy to snapshot. Existing TurnBridge interface unchanged; _turn optionally accepts pretranscribed text, only from its own confirmation.
- [x] GREEN focused/session/full duplex, adjacent identity/companion/diagnostics and addon suites, manifest/diff.
- [x] Independent whole-change review, one RED/GREEN fix pass for material findings; commit.

## Task2: publish and activate
- [x] Fresh Git HEAD, publish reviewed observer+repair through production branch without overwriting concurrent changes; verify CI.
- [x] Read current files/storage/deployment lease, prepare CAS bundle and mandatory backed-up activation; poll same job.
- [x] Verify hashes/running version/fresh native probe, report/source policy and mic state. Record evidence/open limitations and release lease. Ask only for actual household acoustic acceptance that remote tests cannot establish.

## Ledger
Baseline146duplex passed. Ruling: narrow ordering repair replaces the next unpassed AEC experiment; immediate first-syllable interruption remains open. Existing isolated fix/echo-measurement-20261102 worktree retained.

Review found two P1 pending-correction races and one P2 explicit-interrupt cleanup ordering gap. All three independently reproduced RED then fixed in one pass: pending correction can be confirmed during old playback; pending rechecked after stopping; output is stopped before awaiting slow candidate cleanup. Final159duplex green. The real TurnBridge/TextEcho integration test also failed against the prior active Session and passed with this repair. An earlier slow-stop stale-age regression was independently RED/GREEN. Review's declined acoustic/provider/activation judgments remain acceptance checks, not inferred from unit tests. Publication/deployment still pending below.

Activation: echo-stutter-apply-20261102 verified/active_verified22:18:17UTC, backup86b20d21. Runtime604e6b84 matches reviewed source, nativeVAD77frames/TTS2.8316875s fresh probe passed. New fixed HomePod test1complete/0stop/0skip/0error/own45%, cleanup0; microphone remained off-mute and idle. Physical household acceptance remains pending. Evidence docs/evidence/2026-11-02-confirmed-interruption-active.json and private matching receipt. Lease release is verified separately at completion.

Publication: initial automatic approval rejected deployment consent as insufficient public-code consent. Owner then explicitly reconfirmed in the named-repository context. Git CLI lacked credentials; connected GitHub API published01ef3ece7ba7112356d6b90ebe303857d33376fe with expected parent75accdf and identical treee9442be48b80ac6df5bc59b45c2242d1edb23239 to localcd8a8d4. Both CI41535664685/41535672715success, including laboratory publication. No code was sent through an alternate route before renewed consent.
