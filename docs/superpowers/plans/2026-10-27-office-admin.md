# Správa Home Assistantu z kanceláře

Uživatel chce vzdáleně instalovat doplňky a upravovat stávající konfiguraci/kód bez dalšího ručního přenášení příkazů. Výslovně ponechal technické rozhodování asistentce a již povolil plnou vzdálenou správu.

Volba: rozšířit stávající Jarvis, ne další doplněk ani veřejný shell. Jarvis dostane hassio_role=manager a pouze homeassistant_config:rw mount. Updater zůstává samostatná cesta aktualizace Jarvise. Docker API, ochrana hostitele a síť se nemění. Oprávnění maintain/writes a trvalý deník se uplatní na každý zápis.

Rozhraní: systémový přehled, nainstalované/dostupné doplňky, podrobnosti a redigované options, stav HA a zálohy; instalace/aktualizace/start/stop/restart a změna options cílového doplňku; restart/aktualizace Core; záloha a cílená obnova. Změny běží jako trvalé úlohy, úspěch až po readback. Před změnou doplňku/Core záloha. Jarvis sám a jeho Updater jsou chráněni proti správě přes tuto obecnou cestu.

Soubory: textové konfigurační a zdrojové soubory v explicitních kořenech HA; žádná .storage, secrets.yaml, databáze nebo libovolný hostitelský soubor. Relativní cesty, odmítnutí symlinků/hardlinků, atomický zápis a SHA-256 revize. Syntax YAML/JSON/Python se ověří bez spuštění. Původní obsah trvale uložen před změnou; obnova je samostatná úloha. Zápis se automaticky nespouští ani nerestartuje HA.

Postup:
- [ ] Testy cesty/symlinky, validace syntaxe, atomické zápisy a revize.
- [ ] Implementace bezpečného přístupu k souborům.
- [ ] Testy úloh: záloha před efektem, idempotence, chyba zálohy, neznámý výsledek po restartu, přesné cíle a obnova souboru.
- [ ] Implementace Supervisor administrace a deníku; redakce options a výsledků.
- [ ] MCP + kompatibilní jarvis_action most s control i maintain oprávněním.
- [ ] Manifest manager + homeassistant_config mount, výslovná testovaná permission gate.
- [ ] Nezávislá kontrola, kompletní testy/CI, vydání a upgrade přes Updater.
- [ ] Živě ověřit Supervisor přehled, mount, vytvoření/úpravu/obnovu/odstranění izolovaného testovacího souboru a kontrolu HA. Instalaci cizího doplňku neoznačit za živě ověřenou, dokud není skutečně požadován konkrétní doplněk.

Limity: připojení zůstává závislé na internetu/napájení. Žádný automatický slib, že již neexistuje žádná překážka. Deník uchovává výsledky; přerušené úlohy se nikdy znovu nespouštějí. Změna mountu/oprávnění musí být ověřena na skutečném Greenu, ne pouze z manifestu.
