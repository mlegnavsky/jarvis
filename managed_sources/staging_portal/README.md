# Jarvis Lab portal

Published at https://plaginy.odladeni.cz/jarvis/ using the authenticated Odladění managed-file connector. Static files only: no production credentials, household states, recordings, server-side execution or public write API. Links to GitHub retain repository access controls.

Deploy index.html, style.css, status.json and heating-report.json after Git publication. Use file_create for new files; for changes read current SHA and file_write with expected_sha256. Verify each saved SHA and HTTP route. Keep evidence snapshots explicitly dated. The report comes from scripts/simulate_heating.py, not a separate rewritten policy.

This is an evidence portal, not a running Home Assistant. Container hosting still requires an actual authenticated container/VM deployment capability. testing/compose.yaml remains the isolated fixture.
