# Propojení a API

Tento projekt poskytuje REST API. **Není to zatím MCP server ani OAuth konektor pro ChatGPT.** Kód v GitHubu ani Cloudflare Tunnel nedávají chatu oprávnění ovládat dům. Samostatným dalším krokem bude vybrat podporovanou autorizovanou integraci, implementovat ji a ověřit skutečné čtení i povel z mobilu a tohoto prostředí. Bearer token se nemá posílat do konverzace.

Domácí hlasové Assist zařízení, rozpoznávání řeči a mobilní Assist jsou další integrační úkol. Nelze zatím slíbit společnou historii tohoto chatu, nepřetržité naslouchání ani automatický přenos paměti.

## Rozhraní

Vše kromě `GET /healthz` vyžaduje `Authorization: Bearer <api_token>`. Neautorizované volání nevrací inventář. Požadavky s browserovým `Origin` se odmítají. API nemá cookies ani CORS. Veřejný přístup pouze přes HTTPS; Cloudflare Access může být další vrstvou, ale jeho přihlašovací stránka musí být kompatibilní s budoucím klientem.

| Metoda a cesta | Význam |
|---|---|
| GET /healthz | Pouze živost procesu, bez domácích dat |
| GET /v1/health | Verze, spojení událostí, povolení zápisu |
| GET /v1/snapshot | Nově načtené stavy, služby, registry, konfigurace a systémové informace |
| POST /v1/actions | Přesně povolený povel, vyžaduje Idempotency-Key |
| GET /v1/maintenance/check | Obnoví seznam repozitářů a vrátí dostupnou verzi |
| POST /v1/maintenance/update | Založí aktualizační úlohu; tělo pouze `{"version":"0.2.0"}` a Idempotency-Key |
| GET /v1/maintenance/jobs/{id} | Trvalý stav úlohy |

Snapshot nemá cache stavů: při nedostupnosti obsahuje `connected: false`, `captured_at: null`, chyby a HTTP 503. Nedostupný registry znamená `partial: true`; nezmizí potichu. Položky jsou čtené souběžně, nejde o atomický snímek celého domu. `stream_connected` popisuje samostatný odběr událostí.

Příklad těla povelu: `{"entity_id":"light.obyvak","service":"light.turn_on","data":{"brightness":128}}`. Entita i služba musejí být výslovně povoleny v možnostech. Implementované služby: light.turn_on/off, switch.turn_on/off, automation.turn_on, climate.set_temperature a climate.set_hvac_mode. Další služby jsou odmítnuty i při uvedení v seznamu. Zámky, alarmy a dveře nejsou implementované.

Klíč požadavku: 1–128 znaků A–Z, a–z, číslice, `_` nebo `-`. Stejný klíč a tělo vrátí uložený výsledek; jiné tělo se odmítne. Přerušený povel má neznámý výsledek a neopakuje se. **Při nejistotě neposílejte stejný povel s novým klíčem**; nejprve ověřte skutečný stav. Odpověď `accepted` znamená přijetí služby HA, nikoli potvrzení fyzického výsledku. Následný stav může ještě předcházet dokončení zařízení.

Supervisor token je z prostředí aplikace, nikoli z klienta. Umožňuje rozsáhlý přístup k Core; aplikační seznam povolených povelů ho sám technicky neomezuje. Neukládejte domácí snapshoty do veřejného repozitáře. Audit obsahuje jen čas, druh operace a výsledek; rotuje po 1 MiB (aktuální + předchozí soubor). Trvalý deník povelů obsahuje výsledky včetně stavů na lokálním `/data`, maximálně 10 000 klíčů. Při naplnění se zápisy zastaví; klíče se automaticky nemažou, aby se staré povely nemohly zopakovat.
