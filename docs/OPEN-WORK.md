# Stav práce — 29.10.2026, po nasazení3.12.0

## Dokončeno a živě ověřeno

- Jarvis3.12.0: updater job fe80a464e071434aa44666c6c80c743c verified, backup20e5ace6.
- Schválené zálohy91ee007c/fd90919a/e7b028f1 odstraněny novým backup_delete API, všechny tři joby verified.36c1e560 dříve odstraněna přes již přihlášenou UI správu. Žádné další zálohy odstraněny nebyly. Protected9659c1f3 a94e01687 zachovány. Po úklidu3.8GiB volných.
- Původní heat101-activate-20261029 zůstává historicky unknown po odmítnuté přípravě; NESPOUŠTĚT znovu. Nahrazeno doloženým novým nasazením níže.
- Topení1.1.0 včetně opravy staré chyby: ops312-heating-plan-20261029 / ops312-heating-apply-20261029 dokončeno10:50:55UTC, phase active_verified, backup4bb0a0c2, Core2026.6.4. Oba runtime senzory potvrdily version1.1.0.
- Parametry bez restartu ověřeny: min_off_s300→301→300, oba joby verified a původní revize nastavení2e33ab6517018b1048706474a7b0d8c69a2db7095f6d48eeba3ecfc35040ecef obnovena. Výchozí dohodnuté podmínky zachovány.
- Živý test souběžného zápisu ops312-lock-conflict-proof správně selhal deployment_owned_by_another_work před zápisem.
- Živý návrat testovacího souboru ops312-rollback-proof-plan: apply verified/file_written (nikoli runtime active), rollback verified/rolled_back_files, soubor deployment-proof.txt opět missing. Produkční soubory tím nebyly vraceny.
- Hlasový smoke: Jarvis zvolen, mute off, satellite idle. Žádný akustický test ani nové nahrávání neproběhlo.
- CI commit724ec35ad0524d557d37697b32ccec1e92a7eebc: oba běhy40860262447/40860252736 success.203 addon testů,21 testů topení,5 firmware-native testů, kontejnerové buildy/startup. Zdroj implementaceb1e4d520d0383b3b9489017b3be04d4a78231afd.

## Zbývající skutečné hranice

1. Trvale hostovaný oddělený Home Assistant ještě není spuštěný. Připravený Docker Compose v testing/compose.yaml. Lokální a GitHub simulace fungují. Odladění konektor potvrzuje PHP správu, proc_open=false; žádný SSH/Docker/VM nástroj ani dříve ověřený samostatný HA runtime nebyl nalezen. Potřeba skutečný připojený kontejnerový/VM host, nikoli pouze subdoména. Nežádat uživatele o vložení hesla do chatu.
2. Retence vrací bezpečný náhled (keep_latest3 + protected); automatické mazání je vypnuté. Schválení čtyř přesných smazání není souhlas s neomezeným budoucím mazáním. Pro automatický úklid nejdřív určit a schválit rozsah/uchovávání.
3. Deployment lease chrání Admin operace, nikoli nezávislý updater, ruční UI ani cizí přímé zapisovače. Ti musí respektovat proces a CAS. Source_commit je deklarovaný operátorem; soubory jsou ověřeny přes konkrétní hash, nikoli vzdálené kryptografické ověření Gitu v Greenu.
4. TV/SledovaniTV/Discovery: funkční přímé URL ani celý kanálový povel stále neověřen. Řeší oddělený TV work; nespouštět souběžný Core restart bez koordinace.

## Pro pokračování

Čti AGENTS.md → WORK-MANIFEST → OPERATIONS-3.12.md → operations-manifest.json. Ověř deployment_status a aktuální runtime; nepřebírej staré hodnoty jako živé. Všechny další změny běžných parametrů dělej heating_settings, ne editací konstant a restartem. Pro nové zdroje používej připravený bundle + runtime checks. Doplňky/Core/OS neupgradovat hromadně jako vedlejší efekt údržby.

## Jarvis Lab na Odladění

Zdroj portálu: managed_sources/staging_portal; cílová cesta https://plaginy.odladeni.cz/jarvis/. Veřejné bezpečné testovací podklady, snapshot výsledků, odkazy na Git a CI. Není to spuštěný HA runtime; tato mezera výše trvá. Žádné produkční údaje ani veřejná zapisovací operace.

## Laboratorní pipeline

Implementace: scripts/build_release_archive.py, scripts/publish_lab_snapshot.py, testing/lab-public a publikační job Check Jarvis. Přesný kontrakt a zbývající aktivace: docs/LAB-AND-RELEASES.md. Webhook i automatické nasazení ověřeny: commit30348df692f92e6833a926254eba3a9e933669f7, push run40891692482 success; HTTP katalog i SHA256 obou ZIPů odpovídají. Soukromá kopie HA záloh mimo Green stále není zprovozněná. Žádné soukromé zálohy neposílat do public webroot ani public Git.

Vlastník vybral výhradně vlastní server pro HA zálohy. SFTP Storage je nativně podporovaná cesta; serverový účet/soukromá složka a dostupnost SFTP dosud neověřeny. Konektor nemá správu Plesk účtů a Admin neumí založit config flow. Přesný postup a přijímací podmínky: LAB-AND-RELEASES.md. Neukládat soukromé zálohy do veřejného webu.

## Own-server backups: HTTPS implementation (29.10.2026 evening)

SFTP external5.9.58.145:22 timed out from user Windows and native HA setup. Plesk terminal works internally127.0.0.1:22; restricted account has no /proc or SFTP client, reseller UI has no firewall. Private /ha-backups exists owned jarvis_lab and outside httpdocs. Stop repeating SFTP guesses.

Implementation path: native HA WebDAV to constrained PHP endpoint; docs/PRIVATE-BACKUPS.md is the bootstrap, acceptance, rollback and limits. Private credentials must be placed through owner Plesk session; no current direct tool can access this isolated subscription's private folder or start a new HA integration flow. Endpoint and passing CI are not proof of an actual Green backup. Keep status activation_pending until actual encrypted upload completes; no automatic deletion authorized.

## DEYE read-only dashboard — 29.10.2026 19:17 UTC

Production source 7c34a435639c6ccb1988608956adcf8f4ea02415, managed_sources/deye_dashboard/prepare.py. Existing authenticated jarvis_action supports service jarvis.admin, entity_id jarvis.system: data={action:read,query,target} or data={action:change,operation,arguments}. Do not mistake absence of separate admin tool for absence of deployment access.

Prepared deye-plan-20261029 and applied deye-apply-20261029: state verified, phase file_written, no restart. Live file jarvis_workspace/hlavni-prehled.yaml read back exactly, revision11b058ce1a3443083e3b0cc56dec1e74fb52cd30aa49c27c938be4b631470619. Prior image held in deployment plan for CAS rollback. New view deye-baterie and Energy navigation button; all27 prior views preserved. All57 entity references exist in fresh inventory; YAML/Jinja parse checks passed. No device settings changed. Native YAML view loads on opening/reloading dashboard. Visual browser verification remains unperformed: separate cloud browser is at HA login, not an authenticated session. Admin config_check timed out at gateway; subsequent status confirmed backend connected/version3.12.0; no restart attempted. No full inverter-settings backup created. Financial spot result intentionally unavailable pending verified tariff/fees. Dashboard shows live actual values, not lab sample values.
