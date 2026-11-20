# Aktualizace a obnova

Supervisor zakazuje aplikaci aktualizovat sebe sama. Proto oddělený **Jarvis Updater** s rolí `manager` aktualizuje pouze sourozenecký doplněk `<stejny_repo_prefix>_jarvis`. Veřejný klient nemůže zadat cíl, URL, příkaz ani skript. Role manager je přesto široké oprávnění Supervisoru; omezení cíle zajišťuje tento kód. Updater nemá veřejné mapování portu.

1. Hlavní API ověří klíč a povolení údržby, předá požadavek Updateru interní sítí s jiným klíčem.
2. Updater zjistí vlastní identitu přes Supervisor, obnoví repozitář a porovná požadovanou verzi s nabízenou. Supervisor instaluje nejnovější dostupnou verzi, nikoli libovolně připnutou verzi. Před spuštěním aktualizace se nabídka znovu kontroluje; případný souběžný posun nabídky bude odhalen následným ověřením a skončí jako neověřený výsledek.
3. Vytvoří **lokální částečnou zálohu Jarvise** se synchronním dokončením. Není to plná záloha domu ani kopie mimo Green. Selhání zastaví aktualizaci.
4. Trvale zapíše stav `updating`, požádá Supervisor o aktualizaci a vyčká na shodu verze, stav started a ověřené interní API se spojeným proudem událostí.
5. Úspěch je až `verified`. Výpadek nebo jiná verze vede k `failed`; po nejistém výsledku se aktualizace automaticky neopakuje.

Úlohy jsou atomicky ukládány do `/data/jobs.json`, přístup pouze vlastníkem. Po restartu se rozpracované aktualizace pouze ověřují; přerušená fáze před aktualizací končí chybou. Deník má limit 100 úloh a poté nové úlohy odmítá. Zálohy se automaticky nemažou — kontrolujte volné místo. Původní diagnostika ukazovala přibližně 8,5 GB volného místa; aktuální kapacitu ověřte před nasazením.

## Obnova

Automatický rollback není implementován ani ověřen. Při chybě nejprve zkontrolujte skutečnou verzi a log aplikace v HA. V Nastavení → Systém → Zálohy vyberte zálohu se zaznamenaným `backup_slug` a obnovte **pouze Jarvise**. Obnova musí proběhnout přes důvěryhodné HA UI; API nevystavuje libovolné obnovování. Při problému se samotným Greenem použijte dříve uloženou plnou zálohu mimo zařízení.

Před první produkční aktualizací musí proběhnout zkušební upgrade i obnova na skutečném Greenu. Schopnost Supervisoru obnovit přesnou předchozí verzi aplikace je třeba ověřit v tomto testu, nikoli předpokládat podle existence zálohy.

Odkazy: [Supervisor store API](https://contributors.home-assistant.io/apps/supervisor-api/store/), [backup API](https://contributors.home-assistant.io/apps/supervisor-api/backups/).
