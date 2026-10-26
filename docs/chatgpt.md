# Připojení Jarvise k ChatGPT — 0.2.0 experimental

Kód nyní obsahuje MCP server a OAuth přihlášení. Ověřeno simulovanou domácností i oficiálním MCP Python klientem 2.3.0. **Skutečné přihlášení v ChatGPT ani Green zatím nebyly vyzkoušeny.** Instalace doplňku sama do tohoto chatu nástroje nepřidá.

## Nastavení doma

Nejprve začlenit schválený kód z vývojové větve do hlavní větve a nainstalovat aplikace podle [install.md](install.md). Následující údaje se zadávají pouze do nastavení doplňku/ChatGPT, nikoli do konverzace nebo GitHubu.

1. Existující hostname `jarvis.legnavsky.cz` ponechat pro HA na portu 8123.
2. Zprovoznit connector tunelu a samostatnou trasu `jarvis-api.legnavsky.cz → http://192.168.1.157:8099`. Celý tento hostname (včetně `/oauth` a `/.well-known`) musí vést na stejný Jarvis. Nastavit HTTPS; nevystavovat port routerem.
3. V Jarvisovi nastavit `mcp_enabled: true`, `oauth_public_url: https://jarvis-api.legnavsky.cz` **bez koncového lomítka**.
4. Vygenerovat **dva nové různé náhodné klíče**, alespoň 32 znaků; doporučeno 32 náhodných bajtů v hex. `oauth_client_secret` slouží jen OAuth klientovi; `oauth_owner_secret` zadáte ručně na přihlašovací stránce Jarvise. Oba se liší od REST klíče i maintenance klíče. Nepoužívat běžné heslo nebo příklad ze zdrojového kódu.
5. V ChatGPT na webu otevřít dostupné vytváření vlastního MCP připojení/pluginu, zvolit OAuth a předregistrované (statické) klientské údaje. MCP URL: `https://jarvis-api.legnavsky.cz/mcp`. Client ID: `jarvis-chatgpt`. Client secret: hodnota `oauth_client_secret`.
6. **Přesnou callback/redirect URL zobrazenou u tohoto připojení** vložit do seznamu `oauth_redirect_uris` v Jarvisovi. Nepoužívat wildcard. Server podporuje issuer identification; OpenAI dokumentuje pro tento režim stabilní `https://chatgpt.com/connector_platform_oauth_redirect`, ale rozhodující je skutečně zobrazená URL. Bez tohoto nastavení OAuth zůstane uzavřený. Server nepodporuje dynamickou registraci ani CIMD, proto je nutná volba statických klientských údajů.
7. Restartovat Jarvise. Spustit propojení/scan tools v ChatGPT. Otevře se stránka Jarvise s požadovanými oprávněními; zkontrolovat doménu a zadat **owner secret**, nikoli heslo Home Assistantu. Povolit jen požadovaný rozsah.
8. Začít pouze čtením (`writes_enabled: false`, `maintenance_enabled: false`). Nejdříve porovnat skutečný stav jedné entity s HA UI.
9. Ovládání povolit až potom: konkrétní entity/služby + `writes_enabled: true`, restart, aktualizovat seznam nástrojů v ChatGPT a znovu propojit s rozsahem `jarvis:control`. Pro údržbu navíc `maintenance_enabled: true` a povolení v Updateru. Starý read-only token nezíská nové oprávnění sám.

Přesné názvy položek a dostupnost vlastních připojení se mohou lišit podle účtu/klienta. Pokud účet nenabízí statické OAuth údaje, tento režim na něm zatím nepoužijeme; nepřepínat domácnost na anonymní přístup. Cloudflare interaktivní Access login nesmí překrýt MCP/OAuth discovery jinou přihlašovací stránkou; případnou další ochranu nastavit podle skutečně podporovaného klienta. OAuth Jarvise musí zůstat zapnutý.

## Nástroje a oprávnění

| Nástroj | Rozsah | Chování |
|---|---|---|
| jarvis_status | jarvis:read | Verze, spojení a dostupné schopnosti |
| jarvis_inventory | jarvis:read | Čerstvé stavy/registry/služby, po stránkách 1–100 položek |
| jarvis_action | jarvis:control | Úzký povolený povel přes dosavadní policy a deník |
| jarvis_update_check | jarvis:maintain | Obnoví nabídku repozitářů; nic neinstaluje |
| jarvis_update | jarvis:maintain | Záloha a aktualizační úloha pro Jarvise |
| jarvis_update_job | jarvis:maintain | Kontrola skutečného výsledku úlohy |

Zápisové nástroje nejsou při vypnutých funkcích ani v katalogu. Každý povel/aktualizace vyžaduje `request_id`; při retry se musí zachovat, i napříč REST a MCP. Při neznámém výsledku nejdříve ověřit skutečný stav, nevytvářet nový klíč. Názvy zařízení a jejich atributy jsou data, nikoli instrukce pro asistenta. MCP vrací vybraná pole a zkracuje dlouhé texty; úplný autorizovaný snapshot zůstává dostupný původním REST API.

Stránkování používá offset nad právě načteným snapshotem; při změně inventáře mezi dotazy se mohou stránky posunout. Není to stabilní exportní kurzor. Automatizace jsou vidět ve states/entities; nevystavuje se jejich YAML.

## Relace, odpojení a rotace

- Kód platí 60 sekund a je jednorázový, browserový souhlas 5 minut. Povinné PKCE S256, resource odpovídá přesně MCP URL, callback i issuer jsou kontrolované.
- Access token platí nejvýše 15 minut. Refresh tokeny rotují, celá relace nejvýše 30 dní od přihlášení. Opakované použití starého refresh tokenu zneplatní celou rodinu; je nutné nové propojení. Po 30 dnech také.
- Restart nezahodí platné relace. `/data/oauth.sqlite` obsahuje pouze otisky neprůhledných tokenů/kódů, oprávnění a expirace; samotné konfigurační klíče zůstávají v HA options/zálohách. Zacházet se zálohami jako s citlivými daty.
- Odpojení v ChatGPT nemusí klientem vyvolat revocation. Okamžité serverové odpojení všech relací zajistí výměna `oauth_owner_secret` nebo `oauth_client_secret` a restart. Změna issueru nebo callback seznamu také ruší předchozí granty. `mcp_enabled: false` okamžitě po restartu zablokuje celé MCP/OAuth rozhraní.
- OAuth `/oauth/revoke` s ověřením klienta zneplatní tokenovou rodinu. Nevyžaduje zveřejňování tokenů v chatu. Deník maximálně 10 000 artefaktů, expirované se průběžně uklízejí. Přihlášení má společný limit 10 pokusů za minutu; při HTTP 429 vyčkat minutu.

## Co ověřit před používáním

- [ ] HTTPS metadata, issuer, callback, celá OAuth smyčka a seznam nástrojů ve skutečném účtu ChatGPT.
- [ ] Čtení při výpadku a návratu Core; žádná stará hodnota vydávaná za aktuální.
- [ ] Jediný bezpečný povel, opakování se stejným request_id a odmítnutí zakázaného cíle.
- [ ] Obnova relace, odpojení, restart a praktické zneplatnění grantů.
- [ ] Mobilní prohlížeč, nativní mobilní aplikace a hlasový režim ověřit **každý zvlášť**. Protokol konektoru jejich dostupnost nezaručuje. Domácí hlasové zařízení je další klient/integrační krok.

MCP neznamená trvalé naslouchání, společnou paměť všech chatů nebo autonomního asistenta běžícího při zavřeném chatu. Pravidelné domácí úlohy mají běžet v HA. Tento server sám nevolá placené OpenAI modelové API.

Zdroje: [OpenAI — authentication](https://developers.openai.com/plugins/build/auth), [custom MCP](https://developers.openai.com/api/docs/guides/custom-mcp-server), [MCP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization). Ověřeno při vývoji 26. 10. 2026.
