# Stav ověření

## Automaticky ověřeno lokálně

- Čerstvé stavy, kompletní i částečný inventář, timeout, výpadek, WebSocket a opětovné připojení.
- Autentizace, vypnuté zápisy, povolené cíle/služby, validace parametrů a trvalá idempotence.
- Simulovaný Supervisor: záloha před aktualizací, její chyba blokuje update, zákaz jiných cílů, shoda verze a zdraví, obnova úlohy po restartu bez opakování aktualizace.
- Kontrola manifestů, syntaxe a připnutých přímých závislostí.

## Před instalací

- [ ] CI testy i sestavení obou kontejnerů pro arm64/amd64 jsou zelené.
- [ ] Provedena zkouška spuštění sestavených kontejnerů. Lokální prostředí při vývoji nemělo Docker; samotné lokální testy tuto zkoušku nenahrazují.
- [ ] Kód zkontrolován a schválen k začlenění do hlavní větve.

## Na Greenu — DOSUD NEPROVEDENO

- [ ] Instalace a restart obou aplikací; žádné tokeny v logu.
- [ ] Autorizovaný čerstvý inventář odpovídá HA UI, registry i systémové verze.
- [ ] Odpojení a obnovení Core; žádné staré stavy vydávané za aktuální.
- [ ] Bez klíče HTTP 401, s prázdným klíčem uzavřený přístup.
- [ ] Jeden výslovně povolený bezpečný povel, jeho opakování nevyvolá druhou akci.
- [ ] Zakázaná entita a služba neprovedou nic.
- [ ] Částečná záloha Jarvise, zkušební aktualizace a kontrola verze i proudů událostí.
- [ ] Restart během úlohy a následná kontrola bez opakování update.
- [ ] Praktická obnova zálohy v HA UI a kontrola předchozího nastavení/verze.
- [ ] Aktivní Cloudflare connector, samostatný HTTPS hostname API, mobilní data mimo Wi-Fi.
- [ ] Samostatně implementovaný a autorizovaný konektor pro ChatGPT; skutečný dotaz na stav i povel z mobilu. REST API samo nestačí.

Dokud nejsou odpovídající kroky provedené, neoznačovat nasazení ani chatové ovládání za funkční.
