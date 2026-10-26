# Jarvis — další rozvoj

První priorita je spolehlivé spojení a správně ověřený výsledek. Následující fáze jsou návrh, nikoli hotové schopnosti nebo naplánované automatizace.

| Fáze | Co přinese | Podmínka před rozšířením |
|---|---|---|
| 1. Skutečné spojení | Green → Cloudflare → OAuth/MCP → ChatGPT | Přihlášení, čerstvý stav, restart, mobilní data |
| 2. Mapa domu | Oblasti, srozumitelné české názvy a seznam ovladatelných zařízení | Skutečný inventář; nic nenavrhovat podle domnělých zařízení |
| 3. Běžné ovládání | Světla, vybrané zásuvky, scény a nastavení topení | Úzké služby, fyzické potvrzení výsledku, oprávnění pro jednotlivé cíle |
| 4. Dostupnost a hlas | Skutečný ChatGPT hlas doma i na mobilu; nejprve existující počítač | Postup v [voice.md](voice.md); samostatně ověřit nástroje, rozhovor a oprávnění každého klienta |
| 5. Dohled a upozornění | Výpadky zařízení, teploty, baterie senzorů, chybové stavy | Lokální HA automatizace a oznámení, fungující i bez otevřeného chatu |
| 6. Topení a energie | FVE Deye, baterie, přebytky, AKU a vytápění podle skutečně zapojeného systému | Nejdříve pouze měření; ověřené senzory, limity a ruční režim |
| 7. Další členové domácnosti | Individuální účty, odvolání přístupu, role host/dítě/správce | Přechod na vhodného identity providera; současný jeden owner se nesdílí |

## Zásady rozšiřování

- HA pravidla a fyzické ovladače mají fungovat bez ChatGPT a při výpadku internetu. Dlouhodobé rozhodování patří do deterministických HA automatizací s možností vypnutí.
- Scope samo neurčuje, které zařízení smí klient ovládat; rozhoduje i centrální policy. Nová zařízení se nejprve zkouší na čtení, potom se povolí konkrétní služba.
- U topení/energie nejprve definovat skutečné povolené rozsahy a chování při ztrátě čidla; samotný doporučený výpočet nemá automaticky měnit nastavení.
- Nezavádět obecný shell, libovolné service proxy nebo spouštění vzdálených skriptů jako zkratku pro programování. Úpravy konfigurace potřebují vlastní validaci, diff, zálohu a návratovou cestu.
- Protokol nyní používá ověřený handshake MCP 2025. Novější protokolové generace přidávat samostatným adaptérem a testy s oficiálním klientem; netvrdit podporu neimplementované verze.
- Verze funkcí a katalog nástrojů usnadňují další klienty. Při změně katalogu je potřeba jeho obnovení v ChatGPT. Rozšíření nemají měnit význam existujících povelů potichu.
- Společná historie konverzace se nepřenáší automaticky. Budoucí paměť domácnosti musí mít definovaný obsah, pravidla uchovávání a přístup jednotlivých lidí.
