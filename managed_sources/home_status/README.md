# Home status and heating 1.2.0

The source label describes the shared household supply, not a measured assignment of electricity to either heater. PV plus positive battery discharge is `Solár + baterie` for both automatic heaters. A high battery SOC only permits heating; it does not prove battery discharge. Keep inverter power losses visible separately; measurements are not necessarily simultaneous.

Manual OFF holds that heater until an explicit ON or the next Europe/Prague midnight. The existing `Jarvis solární topení` automation evaluates every 15 seconds, including after midnight. Persistence survives Core restart. Existing manual-on temperature and SOC safety limits remain unchanged. Explicit switch commands outside this integration are treated as user overrides, including other automations; don't attach competing heater-control automations.

Deploy card.js to www/jarvis-home-status.js and register a versioned JavaScript module resource before patching the dashboard. Run prepare.py against a freshly read private dashboard; preserve !include, actions and CAS revision. Never commit the private dashboard. New Python integration code needs one Core restart with backup and deployment lease. Roll back through the deployment plan's saved before-images.

Battery warning threshold is strictly below 25%; unknown is not zero. Lock click opens details only. Long press keeps the existing history navigation. Device battery overview excludes the household storage battery.

Checks: heating engine/adapter unit tests, Node device-status checks, generator idempotence and include/action preservation; live verification required after activation.
