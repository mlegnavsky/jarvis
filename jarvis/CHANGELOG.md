# 3.12.0

- Add guarded backup deletion, disk-space read and retention preview.
- Add persistent deployment ownership, revision-bound bundles, activation readback and explicit file rollback.
- Distinguish failed backup preparation from unknown outcomes of the requested change.
- Add bounded heating settings updates without restart for compatible heating integration.

# 3.11.1

- Include required ESPHome minimum version in private model manifests and their content address.

# 3.11.0

- Nativní integrace Home Assistantu pro explicitně delegovanou správu firmwaru vybraných terminálů. Můstek používá vlastní omezený příkaz HA, nikoli zakázanou větev Supervisor proxy. Přístup nepotřebuje browserovou relaci ani udržování přihlášení.

# 3.10.1

- Aktivace explicitního seznamu firmware_targets zachovává ochranu přihlašovacích a spojovacích údajů. Rozlišení fází nativního připojení bez výpisu tokenů nebo serverových odpovědí.

# 3.10.0

- Přímá správa ESPHome firmwaru přes existující můstek: nativní sestavení, OTA instalace, trvalé úlohy a ověření připojení i hashů. Přihlašování přes web není potřeba; používá se oprávněná relace Supervisor ingress, bez vypínání autentizace.
- Výslovný seznam firmware_targets, kontrola revize před sestavením a instalací, sledování dokončení obou částí compile/upload. Nejasný výsledek se neopakuje pod novým klíčem.
- Soukromé modely s kontrolou SHA256 a formátu, obsahově adresované soubory, výměna pouze existujícího ID modelu. Wi-Fi, šifrovací klíče a OTA konfigurace se zachovají beze změny; zdroj ani tokeny se nevracejí do odpovědí.

# 3.9.0

- Správa hlasových nastavení přes můstek: aktuální options, výběr asistenta/probouzecího slova/citlivosti a ukončení řeči, mikrofon, číselné nastavení, hlasitost a zastavení přehrávače. Každé zařízení i služba vyžadují explicitní allowlist; hodnoty se ověřují proti aktuálnímu stavu.
- Hlasová diagnostika bez přepisů a zvukových dat; testy a dočasný místní záznam jen na explicitní požadavek. Záznam vyžaduje confirm_recording=true, nikdy se nezapíná čtením stavu.
- Trvalá idempotence a ověření cílových hodnot pro hlasová nastavení; kompatibilní route jarvis_action service=jarvis.voice pro stávající konektory.

# 3.8.0

- Správa zdrojů lokálních doplňků a sdílených souborů/médií přes explicitní mounty addons/share/media. Čtení, zápis, přesun, smazání a obnova jednotlivého souboru s kontrolou revize, trvalým before-image a zachováním executable oprávnění zdrojů.
- Nahrávání binárních médií po blocích do privátního stagingu, maximálně8MiB na soubor. Ověření velikosti/SHA256 a cílové revize před atomickým zveřejněním; odmítnutí symlinků, hardlinků a citlivých cest.
- Řízené přestavění již instalovaného lokálního doplňku se zálohou, kontrolou verze a fingerprintu spravovaných zdrojů. Ověření image/stavu není samo o sobě funkční test aplikace.

# 3.7.0

- Správa samostatných agentů/služeb integrace pomocí nativních subentry formulářů (například konverzace, STT a TTS OpenAI). Každý formulář má trvalou vazbu na odpovídající nativní route a revizi.
- Existující options flows zůstávají platné při migraci databáze. Přehled subentries nevrací přihlašovací data.

# 3.6.0

- Nativní správa integrací: přehled s podporou options a revizemi, bezpečné otevření a odesílání konfiguračních formulářů, znovunačtení konkrétní integrace s ověřením loaded.
- Options flows jsou svázané s Jarvisem a trvalým deníkem, cizí/uzavřené flows a změněné formuláře jsou odmítnuté. Před otevřením flow záloha HA; citlivá data a výchozí hodnoty formulářů se nevracejí do chatu.
- Přehled hlasových pipeline a jejich výchozího výběru. Dokončení formuláře znamená potvrzené uložení HA, nikoli fyzickou funkčnost zařízení nebo nezávislý readback všech nastavení.

# 3.5.0

- Správa místnosti a uživatelského názvu zařízení přes nativní registr Home Assistantu: kontrola revize, ověření oblasti, trvalý before-image a readback. Nemění identifikátory, párování, firmware ani přihlašovací údaje.
- Čtení konkrétního zařízení včetně souvisejících entit a oblastí pro ověřené přesuny a návazné úpravy automatizací.

# 3.4.0

- Přepnutí známého světla přes light.toggle proběhne v jednom volání: aktuální stav, konkrétní zapnutí/vypnutí a ověření cílového stavu. Vyžaduje povolené zapnutí i vypnutí; nepřijímá další parametry ani neznámý stav.
- Trvalá idempotence zachovává původní výsledek přepnutí i po restartu. Opakovaný request_id světlo znovu nepřepne. Odpověď obsahuje resolved_service a měření request_ms/confirmation_ms.

# 3.3.1

- Instalace dosud nenainstalovaného doplňku porovnává nabízenou version_latest; prázdná version označuje chybějící instalaci, nikoli změnu nabídky. Kontrola před i po záloze a ověření instalované verze zůstávají zachované.

# 3.3.0

- Dokončená správa doplňků: přidání GitHub repozitáře, odinstalování s předchozí zálohou a ověřením nepřítomnosti, obnova options z privátního before-image. Připojení a řídicí doplňky jsou chráněné proti odinstalování touto obecnou cestou.
- Diagnostika odděluje dostupnost jednotlivých vrstev a měří jejich odezvu, čte omezené redigované logy, systémové zdroje, integrace a opravy. Mapa oprávnění zahrnuje i registrované vypnuté/nenačtené entity a jejich přiřazení.
- Historie úloh obsahuje korelační request_id, časy a metadata změněných polí bez hodnot klíčů a konfigurací.
- Interní kontrakt pro nezávislou bránu Updateru: ověřené předání katalogu/volání, serializovaný přenos OAuth databáze, pozastavení mutací při migraci a nevratné potvrzení přesunu autority.
- Trvalý hlídač návratu původní veřejné cesty přežije restart či nespustitelnou novou bránu; po potvrzení nové OAuth autority se stará databáze nesmí znovu aktivovat.

# 3.2.0

- Správa z kanceláře: Supervisor manager a jediný zapisovatelný mount konfigurace HA /homeassistant. Bez Docker API, host network, shellu nebo vypínání ochrany hostitele. Vyžaduje existující povolení údržby a zápisů.
- Přehled doplňků, obchodu, redigovaných options s revizí, záloh, konfiguračních souborů a trvalých úloh. Instalace/aktualizace a start/stop/restart doplňků, změny options, restart/aktualizace Core a cílená obnova přes výslovné operace.
- Systémové změny probíhají v úlohách se zálohou a readback. queued/running/unknown/unverified není úspěch. Přerušené úlohy se znovu nespouštějí. Samotné přijetí obnovy se neoznačuje za ověřenou konfiguraci.
- Atomické textové úpravy konfigurace/vlastního kódu: revize SHA-256, trvalý before-image, obnova, kontrola syntaxe YAML/JSON/Python bez vykonávání. Explicitní kořeny, odmítnutí symlinků a hardlinků; nečte .storage ani secrets.yaml. Zápis sám neaktivuje kód ani nerestartuje HA.
- Živé aktualizace Jarvise dál výhradně přes samostatný Updater; vlastní připojení a přihlašovací klíče jsou chráněné. Povolené entity/služby lze změnit přes vlastní options a projeví se bez restartu.

# 3.1.1

- Světla se po povelu ověřují přímo v Jarvisovi: nejvýše 1,2 sekundy se čeká na cílový stav v HA. Při target_state_verified=true odpadá další volání inventáře z chatu.
- Přidáno měření request_ms a confirmation_ms. Jde o čas uvnitř Jarvise, nikoli celkovou latenci chatu nebo důkaz fyzického osvětlení.
- Při timeoutu nebo výpadku se úspěch cílového stavu netvrdí a povel se znovu neodesílá. Trvalá ochrana proti opakování zůstává zachována.
- Regresní testy opožděného zapnutí, vypnutí a neobdrženého potvrzení.

# 3.1.0

- Vzdálená diagnostika vybraného nastavení HA, kontrola konfigurace a přehled automatizací přes MCP.
- Čtení a revizemi chráněné ukládání, mazání a obnova editorových automatizací. Před zápisem se trvale uloží původní definice; výsledek se ověřuje zpětným načtením. Neověřuje se vykonání ani fyzický stav.
- Nové/obnovené definice mají initial_state=false. To není potvrzení vypnutí již běžící nezměněné automatizace. Aktivace je samostatný povel.
- Kompatibilní přístup přes jarvis_action pro již otevřené chaty vyžaduje současně oprávnění control i maintain. Běžné povely si ponechávají své seznamy povolených entit/služeb.
- Lokální deník má limit 1000 změn a po naplnění odmítá další změny včetně obnovy; diagnostika ukazuje zbývající kapacitu. Deník se automaticky nemaže.

# 3.0.2

- Obnova přihlášení přijme vynechaný parametr resource pouze u platného refresh tokenu svázaného s tímto Jarvisem. Klient nemusí při obnově opakovat již udělenou adresu API.
- Výslovně chybná adresa, neplatné či odvolané tokeny a opakované použití refresh tokenu se nadále odmítají. Doba platnosti a rozsah oprávnění se nemění.
- Regresní test obnovy přes skutečný HTTP endpoint po restartu a test zachování kontroly adresy API. Oprava neprokazuje příčinu všech odhlášení na straně konektoru.

# 3.0.1

- Podpora výslovně povoleného zamknutí lock.lock bez předávání kódu. Odemykání zůstává nepodporované.
- Test ověřuje stav před a po zamknutí a zabránění opakování stejného povelu.

# 3.0.0

- Sjednocené vydání Jarvise 3.0.0: stejné číslo v manifestu, běžícím programu a seznamu změn.
- Automatická kontrola vydání odmítne nesoulad verzí a nadpisy seznamu změn, které Home Assistant neumí správně vybrat. Regresní testy ověřují skutečné odmítnutí vadných balíčků.
- Obsahuje opravu OAuth CSP přesměrování z 0.2.4 a podrobnou diagnostiku autorizace. Nastavení a klíče zůstávají kompatibilní.
- Živé připojení ChatGPT je třeba potvrdit po instalaci; aktualizace neřeší obnovování uložených údajů aktualizační entity Home Assistantu.

# 0.2.4

- Oprava přesměrování přihlášení do ChatGPT: CSP formuláře dovoluje vlastní server a domény předem nastavených návratových adres. Chromium tak neblokuje návrat po prvním potvrzení.
- Přesná kontrola návratové adresy, Origin, CSRF, cookies a PKCE zůstává zachována. Domény návratových adres jsou ověřené před sestavením CSP.
- Ověřeno testy HTTP hlaviček a OAuth; dokončení skutečného spojení ChatGPT vyžaduje nový pokus po aktualizaci.

# 0.2.3

- Nové číslo vydání v manifestu i programu; zahrnuje opravu původu přihlašovacího formuláře a diagnostiku z verze 0.2.2.
- Nastavení a klíče se nemění. Zbývající chybu OAuth je nutné ověřit po instalaci; změna čísla verze sama neopravuje nesoulad údajů aktualizační entity Home Assistantu.

# 0.2.2

- Distinguish missing form transaction, unknown/consumed transaction, expiration and invalidated configuration during browser consent. Token endpoints retain generic invalid_grant responses.
- Synchronize the runtime version with the add-on manifest.
- Does not claim to fix the remaining Green consent failure; the next fresh attempt supplies evidence without exposing credentials or transaction values.

# 0.2.1

- Fix browser OAuth consent rejected as invalid_origin: use same-origin referrer policy so form POST retains its Origin, without sending referrers to other origins.
- Keep exact Origin, cookie and CSRF checks; missing, null and foreign origins remain rejected.
- Regression tests cover the login response policy and denied origins. Actual ChatGPT completion still requires verification on Green.

# 0.2.0

- OAuth-protected MCP connector with separate read/control/maintenance scopes.
- PKCE S256, exact audience/redirect, persistent hashed opaque tokens, rotating refresh families and revocation.
- Paginated inventory; actions share existing allowlists and durable idempotency.
- Disabled by default; actual ChatGPT/Green/mobile authorization remains unverified.

# 0.1.0

- Fresh inventory through Supervisor Core REST and WebSocket.
- Authenticated REST API, disabled-by-default allowlisted actions, durable idempotency and local audit.
- Optional bridge to separate Supervisor updater with backup and post-update verification.
- Real Green deployment, restoration and ChatGPT connection remain unverified.

