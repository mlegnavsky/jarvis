# 1.0.1 — ordinary tiny export is not commissioning

Root cause: production policy and adapter both required persisted bias_verified, while owner disabled commissioning. This prevented the explicitly requested ordinary20W fallback from ever starting.

Remove the historical admission gate in both layers. Do not set bias_verified or manufacture acceptance evidence. Rolling measurements still determine observed export; health, profile, SOC30/resume31, owner intent, power and time guards remain unchanged. No commissioning is run. Policy regression reproduced hold before fix; adapter test confirms ordinary bias starts with proof still false. Full local suite is rerun after updating obsolete commissioning admission expectations; PV-only tests explicitly disable the independent tiny-export fallback.
