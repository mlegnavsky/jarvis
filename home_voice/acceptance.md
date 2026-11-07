# Jarvis doma — ověření

Automaticky prošlo 54 testů včetně 8 testů skutečných YAML/Jinja podmínek a modelovaných stavových sekvencí TV automatiky. [CI 40353927336](https://github.com/mlegnavsky/jarvis/actions/runs/40353927336) ověřilo i sestavení a start doplňků na zdrojovém commitu `69bbdc76c45be9789dab84ebefa9668bc86c9800`. To nenahrazuje HA runtime ani akustické zkoušky.

## Praktické ověření — dosud neprovedeno

Testy provádět nejprve bez povolených domácích změn. U každé zkoušky zaznamenat úspěšná oslovení, falešná probuzení, srozumitelnost a odezvu. Audio soukromých rozhovorů není nutné ukládat. Samotný test nepotvrzuje rozpoznávání identity mluvčího.

| Situace | Zkouška | Přijetí / co upravit |
|---|---|---|
| Ticho | 10 oslovení z běžných míst pokoje | Všech 10 očekávaně probudí; jinak poloha/citlivost |
| Běžná TV | 10 oslovení při normální hlasitosti | Mluvený povel správně rozpoznán, odpověď slyšitelná |
| TV bez oslovení | Alespoň 60 minut různého programu | Zapsat každý falešný wake; cílem nula v testu, nikoli záruka do budoucna |
| Podobná fráze / přesné oslovení v TV | Bez domácích oprávnění pustit nahrávku testovací fráze | Podobné fráze nemají běžně budit; přesná nahrávka může probudit a nesmí se vydávat za technicky vyřešený problém |
| Hlasitá TV / více lidí | 10 pokusů; také promluvy bez oslovení | Poznat limity konkrétní místnosti; při špatném rozpoznání nepovolovat další zápisy |
| Běžný rozhovor | Vtip, vysvětlení, navazující otázka, ukončení | Změřit skutečnou latenci a zda je nutné znovu wake word; žádná falešná tvrzení o paměti |
| Mikrofon vypnutý | Fyzický přepínač mute, poté oslovení | Žádná aktivace a žádný nový přepis řeči |
| Internet/OpenAI nedostupné | Krátce odpojit připojení nebo vypnout pipeline provider | Srozumitelná chyba; běžná HA pravidla/fyzické ovladače fungují |
| Povolena jedna lampa | Jeden povel a dotaz na skutečný stav | Odpovídá HA UI a fyzické lampě; nejednoznačný cíl se nedohaduje |
| Vypnuté řízení agenta | Zkusit povel | Žádná změna; zkontrolovat i vystavení entit |
| TV duck | Hraje TV nad nastavenou tichou úrovní, začít rozhovor | Jediné snížení na nižší úroveň, návrat po idle jen za uvedených podmínek |
| TV vypnutá/muted/tišší | Zahájit rozhovor | Žádný zásah do hlasitosti |
| Ruční hlasitost | Během hovoru nastavit odlišnou úroveň | Automatický návrat nepřepíše ruční aktuální úroveň |
| Další hlasový vstup | Navázat další větou před návratem idle | Nepřepíše se uložená původní hlasitost; nevznikne druhý běh |
| Timeout/restart/odpojení | Přesáhnout 2 minuty nebo restartovat HA při ztlumení | Žádné pozdní automatické zesílení; případný tichý stav upravit ručně |
| Účtování | Po krátké sadě hovorů zkontrolovat API použití | Skutečné náklady, upozornění a případný tvrdý limit jsou známé |

Po přijetí první místnosti zopakovat akustické testy pro každou další. Pokud TV není integrovaná nebo nepodporuje volume_set, ztlumení neoznačovat za nasazené. Všechny řádky tohoto checklistu zůstávají neověřené do reálné zkoušky.
