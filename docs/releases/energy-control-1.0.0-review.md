# Řízení FVE 1.0.0 — připravená revize, NENASAZENO

Základ produkční větve: 7eba6deae0faaa5ce5f32020da760c16369e1f1f. Zahrnuje dosud nenasazenou stabilizaci 8722cc3b2b3e3b58e9c1051c88c6b6addc11311c. Běžící domácnost nebyla v rámci této práce změněna.

## Výsledek

Čistá produkční pravidla jsou oddělena od HA adaptéru. Priorita je dnešní plán, PV přebytky, malý trvalý přetok. Aktuální výchozí politika zůstává PV97 %, prodejní rezerva60 %, domácí rezerva30 %, obnovení31 %, malý přetok20 W a strop9300 W. Existující platná uložená nastavení se zachovávají. Skutečný export není garantován jen cílovým výkonem.

Běžný prodej mění pouze pracovní režim a exportní limit, nikoliv nativní SOC, proud či šest časových programů. Domácí nativní profil se kontroluje pouze čtením; neshoda je vysvětlena, nikoliv potichu přepsána. Staré automatické commissioning větve jsou odstraněny. Historický engine je zachován pro bezpečné dokončení dříve uložených transakcí.

Plán nese vlastní přesnou identitu dne/začátku/konce. Dokončení při rezervě či konci celého obchodního bloku se ukládá atomicky s vymazáním aktivní transakce. Změna vybraného plánu během prodeje nemění identitu původní transakce. Dokončený blok se při odrazu SOC či restartu znovu nespustí; skončený denní výběr není nahrazen druhým ekonomickým blokem. Staré transakce bez identity nevytvářejí smyšlený doklad dokončení jiného plánu.

PV a pozorovaný malý přetok mohou prodloužit HA okno bez zápisů do měniče. Stará/nezdravá data, neplatné ceny a skutečné konflikty nadále zastavují prodej. OFF ruší obnovu. Refaktoring neodstraňuje ochrany ani nezaručuje nepřetržitý export při závadě.

## Historie a diagnostika

SQLite tabulky, ID událostí, časy, finance a archiv zůstávají zachované; žádná destruktivní migrace ani mazání historie. Diagnostika odděluje původní příčinu od problému při obnově, HA stop od nativní expirace a měření od historického commissioning důkazu. Chyby nativních hodnot uchovávají očekávanou i skutečnou hodnotu. Hlášky mají české vysvětlení.

Read-only API vyžaduje přihlášeného administrátora:
- `/api/jarvis_spot_control/sales/diagnostics`: strukturovaný snapshot, health a poslední stop.
- `/api/jarvis_spot_control/sales/history`: původní odpověď posledních1000 událostí zachována.
- `/api/jarvis_spot_control/sales/history?after=0&limit=100`: stránkování, vrací until_id/next_cursor/has_more; další stránky používají stejný until_id. Volitelné filtry kind a sale_id; limit nejvýše1000. Neplatné dotazy400, neadministrátor403. API nic nemění.

## Aktivace po povelu majitele

Nejdříve čerstvě načíst živý stav, aktuální revize a aktivní transakce. Nenasazovat přes probíhající prodej nebo nevyřízené stop/restore. Uchovat návratovou kopii zdrojů i runtime úložišť a historie. Všechny změněné moduly spot_control a související UI instalovat společně z této revize. Aktivace integrace může vyžadovat jeden řízený restart Core, pouze po autorizaci. Po aktivaci ověřit čtením verzi, načtení modulů, zachovaná nastavení, historii a stav; nespouštět commissioning ani hardware test.

Rollback: obnovit konzistentní předchozí zdroje po potvrzeném klidovém stavu. Zachovat runtime data a completed_blocks; nevracet starý snapshot přes novější prodejní historii. Starší kód nezná dokončené bloky, proto při návratu nepovolit automatický prodej bez kontroly aktuálního plánu. Nikdy neobnovovat starou aktivní transakci proti dnešnímu měniči.

## Ověření

Místní Python suite, topení, tři DOM/české zprávy kontroly a kontrola release manifestu. Nezávislá kontrola odhalila a oprava pokryla crash mezeru a záměnu identity plánu. Žádné fyzické měření, test měniče ani restart HA. DOM kontrola není pixelová kontrola mobilu; místní Chromium v tomto prostředí nelze spustit.
