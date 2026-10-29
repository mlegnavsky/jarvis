# Rozpracováno — stav 29. 10. 2026

Před každou navazující prací obnov živý stav; níže je poslední doložený checkpoint, nikoli permanentně aktuální telemetrie.

## 1. Dokončit opravu hlášení topení

- Příčina: poslední chyba ovládání zůstávala uložena i po pozdějším dosažení požadovaného stavu zásuvky.
- Oprava integrace jarvis_solar_heating 1.0.1 publikována v Gitu, commit c32db75b973d50bca5f9140a263b8c762a0f828d.
- Nasazené soubory verified: heat101-file-0-20261029 a heat101-file-1-20261029. Regresní test opožděného potvrzení prošel, celkem17 testů topení a193 addon testů.
- Aktivace NENÍ dokončená. Job heat101-activate-20261029 je unknown. Supervisor log přesně dokládá odmítnutí přípravné zálohy pro nedostatek prostoru (1,5GB); backup_slug null. Neopakovat naslepo.
- Po vyřešení prostoru znovu ověř fázi/živý stav, pak dokonči potřebnou aktivaci a potvrď, že obývák ukazuje správný aktuální důvod místo staré chyby.

## 2. Schválené uvolnění místa

Martin již výslovně schválil odstranění čtyř starších průběžných záloh. Nežádat znovu souhlas se stejným mazáním. K 29.10. v 10:04UTC nebyla žádná z nich smazána.

| Schválený slug | Datum UTC | Poslední známá velikost MB |
|---|---|---:|
| 91ee007c | 2026-10-29 05:34 | 615,62 |
| fd90919a | 2026-10-29 05:39 | 615,84 |
| e7b028f1 | 2026-10-29 05:47 | 616,14 |
| 36c1e560 | 2026-10-29 05:52 | 616,35 |

Celkem přibližně2464MB. Před odstraněním znovu ověř existenci, název Jarvis before remote administration a protected=false. Pokud metadata neodpovídají, nesmaž jinou zálohu jako náhradu.

Zachovat zejména protected automatickou9659c1f3 a nejnovější ověřenou před topením94e01687, plus všechny ostatní neschválené zálohy. Mazání není ve stávajícím Jarvis Admin implementováno. Tato mezera se nesmí zamlčet ani vydávat za chybějící uživatelské heslo.

## 3. TV / Apple TV

Oddělená zařízení; cíl: zapnout TV a Apple TV, otevřít SledovaniTV a přehrát Discovery. Veřejná dokumentace HA potvrzuje obecné deep links; konkrétní funkční URL Discovery v tvOS aplikaci nebylo dohledáno ani otestováno. Nic neoznačovat za nasazenou automatizaci. Vyhnout se souběžným změnám Core z několika worků.
