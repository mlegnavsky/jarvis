# Automatic Sale Request Ordering Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; the owner authorized completing and activating the existing automatic-sales workflow.

**Goal:** Prevent a new automatic enable overtaking an earlier physical stop.

**Architecture:** Keep settings persistence and physical cleanup inside the existing sales lock. Preserve numeric confirmation, reserve60%, price and native conflict guards.

**Tech Stack:** Python asyncio, Home Assistant YAML integration, unittest.

**Spec:** docs/evidence/2026-11-05-auto-sale-concurrent-stop.md

## Global Constraints

No Core/OS upgrade; no unverified inverter outcome; backup preflight2GiB before restart; user authorization covers activation but not arbitrary backup deletion.

## Review Focus

Concurrent enable while stop queues; persistence failure must still stop; repeated stop remains idempotent; incomplete cleanup remains blocked; no numeric readback or reserve guards removed.

## Task: Serialize requests

- [x] Add a test using the actual nested HA handlers; observe an enable overtaking physical cleanup.
- [x] Run `python -m unittest tests.test_sale_request_order -v`; observe expected failure.
- [x] Introduce `_configure_locked(changes, valid_until=None)` and acquire the existing lock once across disable and cleanup.
- [x] Run regression and controller suites; inspect final diff. Full pinned suite:580 tests,20 skips, no failures; independent request-order review found no blocking issues.
- [ ] Publish, prepare exact CAS deployment, activate after backup preflight, verify runtime and automatic state.
