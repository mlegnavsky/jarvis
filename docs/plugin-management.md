# Správa aplikací a integrací — stav 27. 10. 2026

Main Jarvis3.7.0, nezávislá brána Updater1.0.0. Rozlišujeme Supervisor aplikace, integrace HA, vlastní kód a firmware fyzických zařízení. Žádná univerzální operace neumožňuje měnit uzavřený program či firmware bez zdrojů a podporovaného sestavení.

## Ověřené společné operace

- Aplikace: informace, redigované options a schéma, logy, změny options s revizí a zálohou, řízený start/stop/restart/update/install/uninstall a ověření výsledku. Ochrany připojení a vlastních řídicích aplikací zůstávají platné.
- Integrace: `jarvis_admin_read` query=`integrations` nebo `integration` target=entry_id poskytuje metadata, podporu options a revizi bez přihlašovacích data.
- `integration_options_start` arguments={entry_id,expected_revision} založí nativní options flow po záloze HA. Výsledek `form` znamená načtený formulář, nikoli uloženou změnu.
- query=`integration_options` target=flow_id znovu načte jen flow založené Jarvisem. `integration_options_submit` arguments={flow_id,expected_revision,user_input} před odesláním ověří revizi a názvy polí. HA provádí vlastní validaci typů/voleb. Neznámý výsledek se neopakuje novým klíčem.
- query=`integration_subentries` target=entry_id načte samostatné agenty/služby integrace. `integration_subentry_options_start` arguments={entry_id,subentry_id,expected_revision} otevře jejich reconfigure formulář. Další kroky používají stejný submit, ale trvalá vazba určuje správnou nativní route.
- `integration_reload` arguments={entry_id,expected_revision}: záloha, nativní reload a kontrola loaded/require_restart.
- query=`voice_pipelines` ukazuje skutečné pipeline a preferred_pipeline.

V již otevřeném chatu lze stejné operace volat přes `jarvis_action`, entity_id=jarvis.system, service=jarvis.admin, data={action:read,query,target} nebo {action:change,operation,arguments}. Pro zápisy zachovat request_id a ověřovat job. `configuration_saved` znamená terminální potvrzení nativního flow; `settings_readback_verified=false` výslovně odlišuje chybějící nezávislé ověření hodnot. Fyzické a akustické ověření se nesmí nahrazovat tímto stavem.

Formuláře nevracejí data/context/result ani výchozí či suggested hodnoty, včetně vnořených struktur. Cizí a uzavřené flows nejsou přístupné. Žádné `.storage` ani secrets.yaml se přímo neupravují.

## Matice instalovaných aplikací

| Aplikace | Dostupné nastavení | Úprava vnitřního kódu |
| --- | --- | --- |
| Jarvis | Oprávnění, MCP, řízená údržba | Vlastní Git, sestavení a nasazení ověřené |
| Jarvis Updater | Aktualizace, brána, revokace | Vlastní Git; aktualizace přes Main Admin |
| Jarvis Core0.1.0 | Jméno, uživatel, API credential přes options | Lokální zdroj není současným mountem dostupný; role/další použití neprokázané |
| Piper | Hlas, backend, rychlost/parametry syntézy | Vyžaduje spravovanou vlastní verzi zdrojového projektu |
| Whisper | Model, jazyk, STT knihovna a parametry | Vyžaduje vlastní sestavení |
| Speech-to-Phrase | App options; HA pipeline zvlášť | Vyžaduje vlastní sestavení |
| ESPHome Device Builder | App options; integrace zařízení mají vlastní options flows | Překlad/nahrání firmware není součást této nové správy |
| Matter Server | Logování, beta, dostupné parametry | Vlastní sestavení serveru; nikoli firmware koncových zařízení |
| Cloudflared | Dostupné app options | Cloudflare účet/DNS a vzdálené řízení tunelu nejsou samostatně zpřístupněné |
| File editor | Dostupné app options | HA konfigurační soubory spravuje Jarvis přímo |
| Terminal & SSH | Dostupné app options | Není zde poskytován libovolný shell |
| Advanced SSH & Web Terminal | Dostupné app options | Není zde poskytován libovolný shell |

Vlastní HA integrace v custom_components lze upravovat přes existující souborové operace s revizí a before-image. Pro aktivaci použít podporovaný reload, případně ověřený restart HA. Libovolná úprava kódu jiné aplikace vyžaduje přístup k jejím zdrojům, vlastní build/repozitář a konkrétní test změny; není automaticky prokázaná samotným manager oprávněním.

## Aktuálně ověřené hlasové zapojení

Výchozí pipeline Jarvis: čeština, `stt.faster_whisper` → `conversation.extended_openai_conversation` → `tts.openai_tts`, hlas onyx. Vedle toho existuje místní Speech-to-Phrase/Piper pipeline. Nativní OpenAI integrace obsahuje conversation, ai_task_data, stt a tts subentries; dostupnost těchto agentů sama neznamená, že je výchozí pipeline používá. Přesunutý funkční Voice PE dědí oblast obýváku.

## Zbývající hranice

Některé integrace nemají options ani subentry formuláře a nastavují se jiným nativním postupem. Reconfigure/reauth, prvotní párování, firmware a konkrétní vlastní buildy všech cizích aplikací nejsou touto verzí univerzálně pokryté. Proto nelze tvrdit neomezenou správu každého pluginu. Dostupné možnosti se určují z aktuální instalace, nikoli z názvu doplňku.

Nativní API ověřeno proti zdrojům HA Core2026.6.4: `homeassistant/components/config/config_entries.py` a `homeassistant/components/assist_pipeline/pipeline.py` v oficiálním repozitáři home-assistant/core.
