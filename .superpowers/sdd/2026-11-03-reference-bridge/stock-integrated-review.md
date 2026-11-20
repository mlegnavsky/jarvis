# Cílená integrovaná revize stock kompatibility

Datum: 2026-11-03. Porovnání: `2e7041d` → pracovní změny v `stock-integrated-review.diff` a aktuální soubory. Revize byla pouze čtecí; jediný zápis je tento report. Žádné živé volání, nasazení, mikrofon ani další agent.

## Verdikt

V nové změně jsem nenašla reprodukovatelnou chybu úrovně Critical nebo Important. Implementace stock soužití, statické veřejné identity a rozpoznání oficiálního URL bez `@ref` je z pohledu zkontrolovaného zdroje připravena k publikaci kandidáta. To není souhlas s instalací: před tvrzením o dokončeném ověření je nutné dokončit právě běžící úplný build oficiálního balíčku a aktualizovat jeho důkazy. Před instalací dále zůstává přesný soukromý target/wake build a následné fyzické přejímací testy.

Neopakovala jsem oznámené celé testovací suite. Provedla jsem kontrolu zdroje a skutečných lokálních upstream implementací; `git diff --check` prošel. Výsledky fixture buildů a behaviorálních testů níže vycházejí z implementačního reportu, nikoli z mého nového spuštění.

## Zkontrolované vztahy

- `existing_player` je nyní konkrétní `SendspinMediaSource`. Codegen uchová jeho `PlayerRoleListener` před instalací adaptéru. Skutečná upstream třída má veřejnou dědičnost a listener rozhraní dovoluje volat její chráněné overrides přes veřejný base pointer.
- Route a `stream_owner_` zůstávají součástí otevřeného streamu. Configurovaný referenční server se při idle/cancel nezmění na normal. Neznámá identita končí v DROP; změna identity při PCM také. Nový cizí stream při lease lease zneplatní a nezíská stock výstup v témže životním cyklu.
- Normální start nastaví `stream_open_` před voláním stock listeneru. `arm()` odmítá otevřený stream i callback bez otevřeného streamu. End nejprve zastaví přijímání PCM, uvolní mutex během čekání a stock callbacku, a otevřený stream ponechá až do dokončení end. Samostatný `stock_stream_started_` zaručuje end i po přechodu normální route do DROP.
- Všechny delegované callbacky běží mimo reference mutex. Skutečný `SendspinMediaSource` předává PCM do `SourceBinding::write_audio`; start/volume/mute používají deferred požadavky orchestrátoru. Zkontrolovala jsem tuto skutečnou cestu navíc k hardware stubům. SDK 0.9.3 dokumentuje PCM na sync tasku a lifecycle na main loop; end čeká na idle sync task. `get_server_information()` patří mezi thread-safe gettery. Nenalezla jsem konkrétní lock inversion ve zkontrolované stock cestě.
- Stock codec advertisement, mono podpora na vstupu zdroje, 480us fixed delay a unpaired policy se nepřepisují diagnostickým hub setupem. Normální mixer nyní zachová 32bit výstup přes gate; reference sama stále vyžaduje PCM 48kHz/stereo/16bit. Normální DMA dál pokračuje do obvyklého speaker callback chainu.
- `reference_identity` vytváří/čte stejnou lokální identitu jako probe přes executor a zveřejňuje jen `Identity.peer_id`; výjimky zveřejní jen název typu. Samotná metoda neotevírá endpoint, socket ani mikrofon. Control má stávající nonce a novou 120s mez. Nová závislost v test requirements odpovídá již pinované nativní závislosti `aiosendspin[server]==10.3.0`.
- Stage vyžaduje 43 znaků base64url a vkládá identitu jako quoted YAML var. Regex v metadatech používá `fullmatch`, takže volitelné `@ref` nerozšířilo allowlist na suffixy, cizí URL ani credentials. Původní konfigurace včetně nepřítomnosti ref zůstává zachovaná; stage stále nemá aktivaci.

## Critical / Important

Žádný potvrzený nález. Nemám požadavek na opravu produktového kódu před publikací kandidáta.

## Drobnosti a otevřené důkazy

1. `firmware/reference_bridge/build-proof.json` během revize stále popisuje předchozí hash/buildy a stock jako unsupported experiment. Implementační report výslovně říká, že finální důkazy teprve doplní. Před publikací dokončeného balíčku aktualizovat hashe, aktuální minimal buildy, stock routing testy a výsledek úplného immutable package buildu; starý důkaz nepoužít jako důkaz tohoto delta. Jde o známou rozpracovanou evidenci, nikoli nově objevený runtime blocker.
2. Oba validátory ověřují tvar 43 znaků, nikoli kanonické poslední bity base64url. Identita vzniklá skutečným `Identity.peer_id` je kanonická. Chybná ruční hodnota by pouze zabránila arm, protože musí přesně odpovídat paired server ID; nejde o obcházení izolace. Další normalizace není pro tento kontrakt nutná.

## Co tato revize netvrdí

- Fixture/stub testy nedokazují skutečnou akustickou tichost, párování, runtime heap, scheduler/DMA závody na ESP32, síťové reconnecty ani přesnost časového zarovnání. Zachování fixed delay není důkaz synchronizace.
- Neověřovala jsem skutečný Green ani stavy 3.12.3/1.3.5; jsou kontextem od root, ne výsledkem mého live čtení. Nové 3.12.4/1.3.6 tím nejsou nasazené.
- Nehodnotila jsem znovu celou dříve revidovanou reference foundation, security boundary hostu ani neomezené vlastní listener implementace. Posouzení callback reentrance se vztahuje na konkrétní připnutý stock `SendspinMediaSource`/`SourceBinding`, ne na hypotetický listener synchronně reenterující vlastní start/end.
- Původní veřejný balíček bez ref je proměnlivý. Úplný veřejný build se vztahuje k uvedenému SHA `d4e6fa43d6a1a7d342b7d4d403567e06516719de`; nepřisuzuje automatickou kompatibilitu budoucím změnám dev. Přesný soukromý compile gate zůstává nutný.

Publikace zdrojového kandidáta: bez nalezeného kódového blockeru. Dokončené build ověření: čeká na nový úplný build a refresh evidence. Fyzická připravenost / instalace: touto revizí nepotvrzena.

## Doplňková revize: reentrantní teardown a oddělené čítače

Po původní revizi implementer reprodukoval timeout při synchronním `on_stream_start()` → `on_stream_end()`. Původní `stock_callbacks_ == 0` čekalo i na vlastní dosud nevrácený main-loop callback. To je potvrzený opravený problém obecnějšího reentrantního kontraktu SDK; původní výše uvedená revize byla užší a výslovně posuzovala konkrétní deferred stock cestu.

Zkontrolovala jsem pouze nový rozdíl v headeru, implementaci a regresi: `stock_writes_` se zvyšuje spolu s celkovým počtem při přijetí normálního PCM callbacku a snižuje výhradně odpovídajícím `stock_done_(true)`. End přepne route do DROP ještě před čekáním, uvolní mutex přes condition variable a čeká už jen na tento počet zápisů. Main-loop start/metadata zůstávají v `stock_callbacks_`, takže ani po reentrantním uzavření streamu nelze arm provést, dokud se původní callback nevrátí. Guard `stream_open_` během delegovaného end zůstává zachován. Počítání je vyvážené ve všech nově dotčených větvích.

Nová regrese skutečně vyvolá end ze start callbacku a kontroluje přesně jednu dvojici start/end a uzavřený stream. Stávající souběžný write/end test nadále pokrývá čekání na PCM. RED timeout a GREEN adapter/yield testy jsou evidence implementera; neopakovala jsem je bez nového důvodu. Nezjistila jsem nový Critical/Important nález ani regresi v ochraně arm. Counter delta přijata. Předchozí limita fyzické připravenosti platí; všechny tři finální buildy a aktualizace proof musí nyní odpovídat právě této poslední verzi s oddělenými čítači.
