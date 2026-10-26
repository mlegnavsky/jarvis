# Jarvis doma — připravený instalační balíček

**Stav: připraveno ke konfiguraci; skutečné nasazení a akustické ověření neprovedeno.** Tento adresář nezakládá zařízení, API účet ani pipeline automaticky. Green nyní není dostupný z kanceláře a dosud nemáme potvrzený konkrétní hlasový satelit/TV. První spárování hardwaru a vložení tajných údajů musí proběhnout v HA UI; potom lze pokračovat vzdálenou správou v rámci připojeného rozhraní.

## Vybrané zapojení

| Část | Nastavení |
|---|---|
| Domácí jméno | Jarvis |
| Mikrofon/reproduktor | Home Assistant Voice Preview Edition, po potvrzení skutečného zařízení |
| Probuzení | „Hey Jarvis“, microWakeWord přímo na zařízení |
| Rozpoznání celé řeči | OpenAI STT; Whisper jen jako lokální záložní varianta k proměření |
| Konverzace | Nativní OpenAI integrace v HA |
| Český hlas | Piper; konkrétní nainstalovaný český hlas se zvolí v HA |
| Řízení domu | HA Assist, nejprve zakázané; následně vybrané entity |
| Mobil | Dosavadní ChatGPT/Anička a samostatně autorizovaný Jarvis MCP |

Detektor místně sleduje oslovení, nikoli nepřetržité cloudové konverzace. Po probuzení se zvuk řeči posílá STT službě a přepsaný text konverzačnímu modelu. Piper může odpověď přečíst místně. Toto je běžná STT → model → TTS pipeline, nikoli slíbený plně simultánní Realtime hovor; odezvu, přerušování a pokračování je nutné změřit. Doslovná nahrávka oslovení v TV může zařízení probudit. Fyzické vypnutí mikrofonu musí zastavit jeho příjem.

Zdrojový soubor `homeassistant/components/openai_conversation/stt.py` v oficiálním tagu Core `2026.6.4` potvrzuje podporu OpenAI STT i v Martinově uvedené verzi. Přesná dostupnost providerů a nastavení se ověří v aktuálním UI. Z důvodu této přípravy není nutná automatická aktualizace Core. Speech-to-Phrase nepoužívat jako hlavní STT pro volné povídání; je určené pro omezenou sadu povelů. Whisper na slabším hardwaru může mít vysokou latenci.

## Jednorázové zprovoznění doma

1. Ověřit zálohu HA a přístup do administrace. Potvrdit, zda už existuje vhodné hlasové zařízení. Pokud chybí, pořídit jeden Voice Preview Edition pro první místnost; zde žádný nákup neproběhl. Počítat s USB-C napájením dle výrobce. Green sám nemá potřebný pokojový mikrofon/reproduktor.
2. Připojit/spárovat zařízení podle jeho průvodce a přidělit správnou oblast. Zvolit „Hey Jarvis“. Nejprve běžný firmware a standardní model wake word, nikoli neověřené vlastní oslovení nebo speakerID.
3. Připravit oddělený projektový OpenAI API klíč. Platba API je samostatná vůči ChatGPT Pro. Před vložením ověřit účtování, upozornění a skutečný typ limitu v projektu; rozpočtové upozornění nemusí být tvrdým vypnutím. API klíč vložit výhradně do HA integrace, nikdy do GitHubu/chatu. Tato příprava nic neúčtuje ani neaktivuje placený provoz.
4. Nastavení → Zařízení a služby → přidat OpenAI. V konverzační části pojmenovat agenta Jarvis, začít doporučenými nastaveními dostupnými v dané verzi; web search a rozšiřující placené funkce zatím nepřidávat. Zkopírovat [jarvis_prompt_cs.md](jarvis_prompt_cs.md) do instrukcí. „Control Home Assistant“ zatím vypnout. Nesahat ručně do `.storage` a nezapisovat přihlašovací údaje přes veřejné konfigurační soubory.
5. Ve stejné integraci přidat/použít Speech-to-text. V hlasové pipeline Jarvis vybrat češtinu, OpenAI STT, agenta Jarvis a Piper s českým hlasem. Je-li některá položka chybějící, ověřit aktuální verzi/integrace, neinstalovat neověřené balíčky naslepo. Pipeline přiřadit satelitu.
6. Ověřit obyčejný rozhovor bez řízení domu. Příklady: „Hey Jarvis, řekni mi krátký vtip“, „Vysvětli mi, jak funguje tepelné čerpadlo“, navazující otázka a ukončení „děkuji, konec“. Návazný poslech závisí na podpoře satelitu a konverzačního agenta. Dokud není ověřen, počítat s opětovným oslovením pro další vstup; nestartovat nekonečnou automatickou poslechovou smyčku.
7. Teprve potom zkontrolovat **celý** seznam entit vystavených do Assist, včetně výchozího vystavení. Povolit nejprve jednu neškodnou lampu a případně teplotní čidlo, zapnout řízení HA v agentovi a vyzkoušet jednoznačný povel a dotaz na stav. Zámky, alarmy a kritická zařízení ponechat nevystavené. Jména/aliasy a oblasti musí odpovídat skutečnému domu.
8. Nastavit mikrofon dál od TV/reproduktoru a ověřit mluvení v běžných místech místnosti. Počáteční citlivost ponechat výchozí; její zvyšování zkoušet až po měření falešných probuzení. AEC se typicky týká vlastního přehrávání zařízení, není to univerzální oddělovač cizí televizní řeči.
9. Volitelné ztlumení TV přidat až po ověření její HA entity a podpory `media_player.volume_set`, podle následující části. Pro každý další pokoj zkoušku zopakovat; neinstalovat několik souběžně se ovlivňujících automatik pro stejnou TV.

## Dvě různá oprávnění

Domácí OpenAI agent používá **nativní Assist API a vystavené entity HA**. Mobilní ChatGPT konektor používá **Jarvis MCP scopes a jeho allowlisty**. Nejde o stejný kontrolní mechanismus a MCP `writes_enabled: false` nezakazuje nativnímu Assistovi jeho vlastní zápisy. Obě cesty je nutné nastavovat zvlášť. Prompt je návod k chování, ne technická náhrada oprávnění. Domácímu agentovi nevystavovat správce aktualizací nebo shell.

## Volitelné ztlumení televize

Soubor: [tv_duck.yaml](../blueprints/automation/jarvis/tv_duck.yaml). Je to standardní HA blueprint. Nejprve musí být schválené soubory v hlavní větvi; draft PR se sám do HA nenainstaluje.

V Nastavení → Automatizace a scény → Blueprints importovat URL:
`https://github.com/mlegnavsky/jarvis/blob/main/blueprints/automation/jarvis/tv_duck.yaml`

Potom vytvořit jednu automatizaci z tohoto blueprintu, vybrat skutečný satelit a TV/soundbar a nastavit tichou úroveň (výchozí 0,15 = 15 % **nastavení hlasitosti**, nikoli snížení o 15 % nebo záruka stejné akustické hlasitosti). Před uložením ověřit, že jde o správný audio výstup TV. Pokud integrace vystavuje pouze krokové Volume up/down bez absolutní úrovně a volume_set, tuto automatizaci nepoužívat.

Automatizace reaguje na `idle → listening`, stáhne pouze hrající TV s vyšší známou hlasitostí a neztlumí již tichou nebo ztišenou TV. V jednom běhu uchová původní úroveň přes processing/responding i navazující poslech. Na návrat do idle čeká nejvýše přibližně dvě minuty s dvousekundovým ověřením. Vrací hlasitost pouze pokud je satelit idle, limit nevypršel, TV dál hraje, není muted a aktuální úroveň odpovídá její nastavené tiché úrovni s tolerancí 0,005.

Při ruční změně na jinou úroveň, zastavení TV, timeoutu nebo odpojení se automatický návrat přeskočí. Krátká změna hlasitosti a návrat přesně na tutéž tichou úroveň není podle aktuálního stavu rozlišitelná; současné ověření také není atomické s příkazem do zařízení. Restart HA, vypnutí automatiky nebo chyba služby může TV ponechat ztlumenou — upravit ji ručně. Automatizace nepřežívá restart s uloženou původní úrovní a nespouští pozdní automatické zvýšení po restartu. Dlouhý rozhovor nad dvě minuty proto může vyžadovat ruční obnovení.

**Ztlumení se provádí až po probuzení. Neřeší původní falešné probuzení televizí.** To ověřuje samostatný akustický checklist.

## Paměť a návrat změn

[memory.example.md](memory.example.md) je pouze šablona pro ručně schválená dlouhodobá fakta. Nevzniká automatická dlouhodobá paměť nebo synchronizace s Aničkou v ChatGPT. Citlivé poznámky neukládat do tohoto veřejného repozitáře.

Pro návrat: vypnout TV automatizaci (případně ručně upravit hlasitost), v agentovi vypnout řízení HA, odpojit/vypnout mikrofon satelitu a podle potřeby přepnout pipeline na předchozí. OAuth/MCP přístup se odvolává samostatně podle docs/chatgpt.md. Nedotýkat se ostatních HA automatizací. Po kompromitaci API klíče ho odvolat v OpenAI a změnit v HA.

## Co ještě zbývá

[acceptance.md](acceptance.md) obsahuje měření při televizi, více lidech, výpadku internetu a ověření účtování. Testy v repozitáři renderují skutečné šablony blueprintu; neprovádějí akustický test ani plnou validaci konfigurace běžícím Home Assistantem. Obojí musí proběhnout na Greenu před zapnutím automatizace.

Zdroje ověřené při přípravě: [OpenAI integrace HA](https://www.home-assistant.io/integrations/openai_conversation/), [oficiální STT zdroj Core 2026.6.4](https://github.com/home-assistant/core/blob/2026.6.4/homeassistant/components/openai_conversation/stt.py), [místní STT a výkon](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/), [Voice Preview Edition](https://www.home-assistant.io/voice-pe/), [stavy satelitu](https://contributors.home-assistant.io/core/entities/assist-satellite/), [start_conversation](https://www.home-assistant.io/actions/assist_satellite.start_conversation/).
