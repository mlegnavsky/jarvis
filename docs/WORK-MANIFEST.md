# Pracovní manifest Jarvise

Verze dokumentu 1; stav zjištěný 29. 10. 2026. Vlastník Martin Legnavský. Záměr: práce přes kód, Git a přímé rozhraní, bez opakovaného hledání přístupu a bez přenášení technické práce na uživatele.

## Jednoznačné zdroje

| Oblast | Autorita / cesta |
|---|---|
| Repo | mlegnavsky/jarvis |
| Nasazovaná větev | feat/jarvis-addon; main není zdroj aktuálně instalovaného doplňku |
| Jarvis | b4b773b1_jarvis, naposledy ověřeno 3.12.0 |
| Stabilní brána a updater | b4b773b1_jarvis_updater; OAuth a rescue nezávislé na Core |
| Green | HA Core 2026.6.4; neupgradovat v rámci běžných oprav |
| Přímý vstup | Jarvis plugin: jarvis_action, jarvis_inventory, update a rescue |
| Správa | service jarvis.admin, entity_id jarvis.system |
| Zdroj nativních integrací | managed_sources/<součást> |
| Nasazené integrace | custom_components/<domain> přes HA config mount |
| Živý dashboard | jarvis_workspace/hlavni-prehled.yaml |
| Doplňky a sdílené soubory | admin workspaces addons/share/media |

Autentizaci používej z připojených nástrojů. Repo přístup není automaticky SSH, root ani přístup k libovolnému API Greenu. Secret nikdy nepřenášej do manifestu. Ověřený přístup k firmwaru není automaticky přístup ke správě záloh.

## Schopnosti a skutečné hranice

Strojový soubor operations-manifest.json generuje `python scripts/export_capabilities.py` přímo z povolených polí v kódu. Je to kontrakt implementace, ne důkaz dostupnosti a oprávnění v běžící instalaci.

| Schopnost | Stav a ověření |
|---|---|
| Inventář, služby, registry a diagnostika | Přímý plugin; čerstvé čtení, žádné staré stavy při výpadku |
| HA konfigurační soubory | file read/write/restore/delete, CAS revision a předchozí obsah |
| Změny integrací | Nativní options/reload a revize; podporované rozsahy podle kontraktu |
| Automatizace | YAML úprava + automations_reload, potom kontrola entity a výsledku |
| Aktualizace Jarvise | update_check/update/update_job; úspěch až verified |
| Zálohy | Výpis, vytvoření, obnova a cílené mazání s CAS implementovány; tři živá mazání verified ve 3.12.0 |
| Firmware a soukromé wake modely | Přímé compile/install/model_install/restore; živý OTA ověřen 29.10.; cíle výslovně povolené |
| Mikrofon a hlas | Stav/diagnostika a výslovně aktivované záznamy; nejde o neomezený permanentní přenos |
| Volné místo, retence a cílené mazání záloh | Čtení místa, preflight a bezpečný náhled retence ve 3.12.0; automatické plošné mazání vypnuté |
| TV / Discovery | Otevření konkrétního kanálu SledovaniTV neověřeno; nezaměňovat obecnou podporu deep links za funkční odkaz |
| Libovolný shell, root, DNS/router a účty všech služeb | Neověřeno / tímto manifestem se nezřizuje |

## Přesný způsob nasazení

- Před editací stáhni aktuální obsah a revision; neposílej celý starý konfigurační soubor z paměti.
- Zdroj nejprve ověř a ulož do Gitu. Při publikaci použij aktuální parent a očekávaný HEAD. Při konfliktu znovu načti cizí změny, nepřepisuj je silou.
- Kód doplňku vyžaduje konzistentní verzi runtime/config/changelog a updater. Nativní integrace má vlastní manifest a aktivaci. Dokumentační změna nepotřebuje restart ani update.
- U file_write polluj admin job a potvrď revision. Pokud je třeba aktivace, proveď reload/restart odpovídající součásti, pak živé ověření. Neukončuj úkol na pouhém uložení souboru.
- Před velkou zálohou ověř prostor, pokud existuje povolené čtení. Když neexistuje, eviduj tuto mezeru; nehádej volné místo.
- U selhání bez začaté mutace odliš chybu přípravy od neznámého výsledku. Pokud stávající rozhraní vrátí unknown, respektuj ho a proveď reconciliaci pomocí úlohy, logu a aktuálního stavu.

## Historické požadavky — implementace a hranice ve 3.12.0

1. Cílené `backup_delete` pouze pro explicitně schválené slugy; nejprve načíst metadata, blokovat protected a chráněné poslední zálohy, CAS, trvalý request_id, ověřit nepřítomnost po smazání. Žádný plošný příkaz „smaž vše“.
2. Čtení diskového prostoru a velikostí záloh přímo přes podporované Supervisor API. Vrátit potřebné minimum dat.
3. Prostorový preflight před zálohou; příprava nesmí nesprávně vypadat jako provedený restart.
4. Jednoznačný stav nasazení: source_published / file_written / activation_pending / active_verified / blocked, včetně důvodu a potřebného dalšího kroku.
5. Cílené a testované reloady dalších součástí, kde je podporuje HA; neslibovat obecný hot reload libovolného Pythonu.

Stav implementace a konkrétní hranice popisuje docs/OPERATIONS-3.12.md. Nativní hot reload libovolného Pythonu ani trvale hostovaný testovací HA nejsou hotové. Implementace dalších bodů potřebuje skutečnou dostupnou nasazovací cestu. Je-li nová verze blokována místem a povinnou zálohou, nejprve vyřeš tento bootstrap přes již dostupnou autorizovanou správu. Neobcházej ochranu a nevytvářej další vrstvy kódu bez možnosti je aktivovat.

## Ověřování a rychlost

- Bugfix: reprodukce → cílený test → nejmenší oprava → relevantní suite → živý výsledek.
- Topení: PYTHONPATH=managed_sources/solar_heating python -m unittest discover -s managed_sources/solar_heating/tests -q
- Addon: PYTHONPATH=jarvis:jarvis_updater python -m unittest discover -s tests -q (potřebné závislosti z projektu).
- Release: python scripts/check_manifest.py; git diff --check.
- Nepouštěj stále znovu stejné kompletní kontroly bez změny. Čtení nezávislých údajů dávkuj. Opakování závislých mutací neparalelizuj.
- Čekání na úlohu nesmí blokovat krátkou pravdivou informaci o práci. Neposílej prázdné sliby „už skoro“.
- „Hotovo“ znamená konkrétní ověřenou funkci. Akustické rozpoznání hlasu, spuštění TV kanálu a fyzické výsledky nepředstírej pouze podle přijetí příkazu.

## Aktuální postup od3.12.0

Používej storage a backup_retention před údržbou, deployment_acquire/prepare/apply/read/release pro související změny, explicitní CAS rollback pro soubory a heating_settings pro běžné parametry bez restartu. Testovací simulace a kontejnerové smoke testy běží v GitHub Check Jarvis. Detailní kontrakt: docs/OPERATIONS-3.12.md.

## Laboratoř a archiv vydání

Aktuální provozní postup: docs/LAB-AND-RELEASES.md. Laboratoř laborator.odladeni.cz používá pouze větev lab/plesk-bootstrap-20261029; produkce feat/jarvis-addon. Publikace do Gitu, nasazení souborů a aktivní runtime jsou oddělené důkazy. Zálohy domácnosti nikdy nepatří do veřejného archivu. Plesk webhook a živá publikace ověřeny commitem30348df692f92e6833a926254eba3a9e933669f7 / run40891692482. Privátní HA zálohy musí podle vlastníka na vlastní server. Cílový SFTP účet a soukromá složka dosud nejsou připojené; tato mezera trvá. Podrobnosti v LAB-AND-RELEASES.md.
