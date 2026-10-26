# První instalace — doma

Tato větev je experimentální. Nejdříve zkontrolujte CI a začleňte schválený kód do hlavní větve. Home Assistant instaluje repozitář z výchozí větve; otevřený pull request se sám nenainstaluje.

1. Na domácí Wi-Fi otevřete Home Assistant. Ověřte existující plnou zálohu a stáhněte ji mimo Green.
2. Nastavení → Aplikace / Doplňky → obchod → nabídka → Repozitáře. Přidejte `https://github.com/mlegnavsky/jarvis`.
3. Nainstalujte **Jarvis** a **Jarvis Updater**. První sestavení na Greenu může trvat. Dvě aplikace jsou nutné kvůli zákazu aktualizace sebe sama přes Supervisor.
4. Vytvořte dva různé náhodné klíče, každý alespoň 32 znaků (ideálně 32 náhodných bajtů v hex). Nevkládejte je do chatu ani na GitHub.
5. Jarvis: `api_token` = hlavní klíč, `maintenance_token` = druhý klíč. Nechte `writes_enabled: false`, `maintenance_enabled: false` a prázdné seznamy entit/služeb.
6. Updater: `api_token` = druhý klíč, `jarvis_api_token` = hlavní klíč, `updates_enabled: false`.
7. Spusťte obě aplikace a ověřte inventář podle acceptance checklistu. Jarvis poslouchá na portu 8099; používá HTTP v domácí síti. Nevystavujte tento port přesměrováním routeru.
8. Zprovozněte connector Cloudflare Tunnel na Greenu podle aktuálních pokynů jeho vydavatele. Token uložte jen do nastavení connectoru. Existující tunel Jarvis nemá zatím aktivní connector; DNS sám spojení nevytvoří.
9. Existující `jarvis.legnavsky.cz → http://192.168.1.157:8123` ponechte pro rozhraní Home Assistantu. Pro API přidejte samostatný hostname, například `jarvis-api.legnavsky.cz → http://192.168.1.157:8099`, a otestujte ověřování přes HTTPS. Updater port 8100 se nevystavuje.
10. Teprve po ověření čtení povolte konkrétní entitu a službu. Aktualizace vyžadují současně `maintenance_enabled: true` v Jarvisovi a `updates_enabled: true` v Updateru.

Změny možností vyžadují restart aplikace. Automatické aktualizace Jarvise v HA nechte vypnuté, chcete-li zachovat zdejší postup se zálohou. Updater se aktualizuje ručně přes HA UI po záloze.

Po prvním připojení bude další programování probíhat v GitHubu. Změny HA automatizací, libovolná úprava `/config`, instalace cizích doplňků a shell nejsou tímto API povolené. Pro každou takovou schopnost je nutné samostatné návrhové a testovací rozšíření.
