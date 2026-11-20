# Live verification — resilient administration, 2026-10-27 UTC

Final application versions: Jarvis 3.3.1, independent Updater gateway 1.0.0. Home Assistant Core 2026.6.4 was not upgraded or stopped. No physical device commands were issued during acceptance.

## Automated verification

- 143 unit/integration tests passed locally and in GitHub Actions.
- Manifest/release/source-parity gates and git diff --check passed.
- Both apps built for amd64/aarch64 and passed container startup checks.
- Initial release source: 0e3dbabf05536de5f949795169036bf160c9ef00; CI run 40465085786.
- Installation correction: 0c3386ea9d2035c0487565dd80fd644511dd9683; CI run 40465740792, all three jobs successful.
- Independent reviews covered gateway authority handover, rollback races, recovery durability, admin lifecycle and bounded diagnostics.

## Actual deployment and acceptance

| Check | Observed result |
| --- | --- |
| Main upgrade to 3.3.0 | Update job 0502e8df62b34402939f9657dd6ad4b4 verified, backup 6992ce73 |
| Updater upgrade to 1.0.0 | Admin job resilient-updater-100-20261027 verified, backup 50522fdd |
| Same-address gateway activation | gateway-activate-20261027 reached active; authenticated external status returned gateway_version 1.0.0 and healthy backend |
| Existing authentication | Existing connected plugin continued without reconnecting or entering credentials |
| Real Main outage | rescue-outage-proof-20261027 stopped Main; public status returned backend_connected=false, recovery_available=true and concrete rescue route |
| Automatic recovery | Same outage job became verified; Main status returned stream_connected=true |
| Real backup restoration | rescue-restore-proof-20261027 restored Main-only backup c4cfb66f; restore_confirmed=true, repair_required=false, verified |
| Configuration proof | A temporary nonexistent entity had been added to policy; restoration removed it and reproduced exactly the original options revision and allowed-entity list |
| Main upgrade through gateway | 3.3.1 job fcda3f41bce04630b0b0a0a48c100016 verified, backup a3a1c346; external status confirmed 3.3.1, stream connected, gateway 1.0.0 |
| New app installation | probe-install-proof-331-20261027 verified version 0.0.1, stopped, manual boot; backup 342e445c |
| App removal | probe-uninstall-proof-20261027 verified installed=false; backup d06d917e |

The temporary probe had no Supervisor/Core access, ports, mounts or hardware permissions and was never started. Its two source files were removed after uninstall; only the two existing permanent Jarvis apps remain in the repository.

The first installation attempt failed before backup or mutation because Supervisor reports version=null for an uninstalled store entry and its offered release in version_latest. This was reproduced as a failing regression test, corrected in 3.3.1, and the new request completed successfully. No unknown mutation was blindly replayed.

## Diagnostics actually read

- Core, Supervisor, OS/disk information, Core/Supervisor resource statistics, resolution, repairs and integration health were available.
- Supervisor reported healthy/supported; resolution had no unhealthy/unsupported entries, repair list was empty, and no errors were reported among 28 integrations.
- Permission map included 469 entities, 48 devices and 16 areas, without truncation. Registered entities without states are represented separately.
- Both bounded Core and Supervisor log reads succeeded with redaction applied. Actual logs, credentials and full home inventory are deliberately absent from this evidence.
- Host resource statistics endpoint was unavailable. Diagnostics correctly reported partial=true instead of treating this missing measurement as healthy data. OS/disk and Core/Supervisor resource measurements remained available.

## Scope of proof

Real operations above prove installation/removal, updates, Main outage isolation and Main backup restoration. Repository-add, general Core updates, arbitrary other app options restoration, failed-image migration rollback and OAuth revocation were covered by automated contracts/reviews; they were not deliberately induced on this live household.

Gateway survives a Main app failure. Green hardware, power, network and Cloudflare tunnel remain shared infrastructure. See rescue-and-diagnostics.md for the authenticated fallback procedure; never substitute stale home states or label queued/running/unknown as verified.
