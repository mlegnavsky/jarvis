# Spoty loader correction

The first deployment appended the new class only to www/jarvis-energy-weather-v2.js. Fresh configuration.yaml names /local/jarvis-energy-weather.js?v=1.0.0 in frontend.extra_module_url; that entry point did not register Spoty. No storage resource registration was verified.

Regression test fails against the freshly read configured entry point. Appending the isolated Spoty card makes registration and empty-telemetry rendering pass; duplicate card inclusion is guarded. Existing weather source remains unchanged. Preparation script now rejects the wrong entry point.

Deploy target: www/jarvis-energy-weather.js, CAS on fresh revision. No inverter writes, HA restart, or authentication changes. Live visual verification remains blocked by the cloud browser login screen; do not claim it passed.
