# Energy1.0.2 — reconciled installation candidate

The owner authorized installation of the prepared refactor. Live preflight found concurrently installed1.0.1 rather than0.9.3. This candidate reconciles the prepared0.10.0 implementation with the newer running behavior; it is not a downgrade. See ENERGY-REFACTOR-0.10.0.md for architecture and safe installation/rollback.

Preserved: small20W export no longer depends on the obsolete bias_verified flag; exact native profile, measured health/electrical limits, owner intent and observed export remain mandatory. Existing completed_blocks entries suppress the entire completed business day even if the selected block is truncated at23:40 or later reselected. New battery proofs retain business_block. Existing history until_id snapshot paging and authenticated diagnostics URL remain available. Editable home_soc stays fixed30, preserving live policy.

Added safeguards from the reviewed refactor: export-only write boundaries, fresh native30 admission at each start, exact typed transient recovery stable30s with cancellation by newer stops/manual operations, permanent detailed diagnostics and old-schema history retention. Legacy in-flight cleanup and explicit maintenance remain available.

Verified749 Python tests run,729 passed and20 existing PHP-dependent skips;11 Node unit/DOM suites previously passed and affected suites rerun. Independent reconciliation review findings have regression tests. Visual Chromium acceptance remains blocked by environment EPERM. Real-device acceptance is pending installation, not inferred from source tests.

Manifest with exact source hashes: docs/releases/energy-1.0.2-candidate.json. The live backup and deployment plan receipts remain private. No household database, credentials or one-day override is published. No Core upgrade and no backup/history deletion is part of this change.
