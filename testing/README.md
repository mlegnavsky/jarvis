# Isolated Jarvis test environment

Run `python scripts/simulate_heating.py` for deterministic cloud, battery, outage and manual-mode tests. It imports the exact production policy and HA adapter tests, writes a machine-readable report with source SHA256 and test result. No production connection or actual switch writes occur.

`testing/compose.yaml` supplies a pinned Home Assistant2026.6.4 container fixture for a host with Docker Compose. Run `docker compose -f testing/compose.yaml up -d` on that host. It binds loopback only, uses a separate blank config and contains no production credentials, devices or restored production backup. This is a reproducible fixture, not a claim that a remote container is currently running. Do not expose it publicly without separate authentication and TLS configuration.

A subdomain alone is insufficient. Current Odladeni connector confirms authenticated PHP storage and deployment, PHP8.4.27 and proc_open=false. It exposes neither container management nor SSH. Container hosting and its authenticated deployment path remain unverified; do not upload an HA config to the public PHP webroot and call it staging.

For fixture changes, review pinned Core compatibility before replacing the image tag. Real speaker, HomePod, TV and firmware OTA still require explicit hardware acceptance checks after simulation.
