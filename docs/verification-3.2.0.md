# Ověření správy z kanceláře — 27. 10. 2026

- Zdrojový commit f9f74dc6f040d0cc16abe8c0a2a82cdd80de8aa0, instalační větev feat/jarvis-addon.
- Lokálně 107 testů OK; manifesty/oprávnění, syntax a diff --check OK. Nezávislá kontrola bez blokujících nálezů. Opravena a otestována smlouva Supervisor options/validate (raw options, valid=true), validace backup ID a typů argumentů.
- CI run 40459390225: tests, containers (jarvis), containers (jarvis_updater) success, včetně arm64/amd64 sestavení a kontrol spuštění.
- Updater úloha 99a4c1347e964f648e4f58722f0eed1e: verified, záloha 5e873a4a, error=null.
- Živý Jarvis: verze 3.2.0, capabilities_version=3, stream_connected=true, writes/maintenance enabled.
- Živý Supervisor přehled funguje; 12 instalovaných doplňků, připojený HA konfigurační mount dostupný. Souborový inventář funguje a správně hlásí truncation při množství frontendových assetů HACS.
- Izolovaný jarvis_workspace/office-probe.yaml před testem missing. Úlohy office-file-save-20261027, office-file-edit-20261027, office-file-restore-20261027 a office-file-delete-20261027: všechny verified.
- Obnova vrátila přesnou SHA-256 revizi původně zapsaného obsahu. Následné čtení po úklidu: content=null, revision=missing. Soubor není součástí aktivované konfigurace.
- Skutečný patch vlastních options přes Supervisor: office-enable-known-lights-20261027 verified, záloha 40992308, activation_performed=true. Rozšířena pouze povolení známých světel; klíče a připojení zachovány, žádné fyzické ovládání neproběhlo. Options čteny pouze v redigované podobě.
- Supervisor kontrola konfigurace HA: valid=true.

Instalační/update/start/stop/Core operace jsou implementovány a otestovány s modelem Supervisoru. Není zde tvrzená živá instalace zbytečného cizího doplňku ani nevyžádaný restart/upgrade Core. Tyto konkrétní cíle se ověří při jejich skutečně požadovaném použití. Cílená obnova systémové zálohy záměrně vyžaduje následné ověření obsahu a nehlásí úspěch pouze z dokončení HTTP požadavku.

Rozsah a provozní omezení: office-administration.md. Soukromé konfigurace, before-images, inventáře a přístupové klíče se do tohoto repozitáře nekopírují.
