# Jarvis 3.1.0 — ověření 27. 10. 2026

- Zdrojový commit: 26b75fc31a56c49b586cd7b09447e99196024f7f, instalační větev feat/jarvis-addon.
- Lokálně 90 testů OK; manifesty, verzování a diff --check OK. Nezávislá kontrola kódu bez blokujících nálezů; limit deníku a omezení ověřování běžící automatizace zdokumentovány.
- GitHub Actions run 40455219155: tests, containers (jarvis), containers (jarvis_updater) success; sestavení arm64/amd64 a kontrola spuštění.
- Updater požadavek jarvis-3-1-0-management-20261027, úloha c08b164c50f043b0846330461934a28b: verified, backup_slug 1f914b10, error null.
- Živý Jarvis hlásí 3.1.0, stream_connected=true, capabilities_version=2, writes_enabled a maintenance_enabled=true.
- Živá kontrola konfigurace HA 2026.6.4: result=valid, errors=null, warnings=null.
- Přes již připojený jarvis_action a dodatečně ověřené oprávnění maintain načten přehled automatizací.
- Nová testovací definice jarvis_management_probe_20261027: před testem missing; uložení verified; skutečná automatizace měla state=off. Pouze event trigger a 1ms delay, žádná akce na zařízení.
- Editace testovací definice včetně vynechání polí verified; obnova z původního before-image verified a výsledná SHA-256 revize shodná s původní.
- Testovací definice odstraněna verified; následné GET config=null/revision=missing a seznam znovu obsahuje pouze dvě původní automatizace.
- Zálohy konfigurace a idempotentní výsledky jsou pouze na Greenu; do repozitáře se neukládají soukromé definice ani tokeny.

Toto potvrzuje skutečné vzdálené aktualizace se zálohou a správu editorových automatizací. Nepotvrzuje libovolné úpravy souborů HA, instalaci cizích doplňků, fyzické výsledky akcí ani dlouhodobou stabilitu OAuth.
