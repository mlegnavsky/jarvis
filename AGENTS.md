# Jarvis — pravidla práce pro každého dalšího agenta

Nejdřív přečti `docs/WORK-MANIFEST.md`, strojový kontrakt `docs/operations-manifest.json` a otevřené úkoly `docs/OPEN-WORK.md`. Tyto soubory jsou výchozí bod pro pokračování, nikoli náhrada aktuálního stavu Greenu.

## Pracovní dohoda s Martinem

- Komunikuj česky, v ženském rodě, stručně. Jakmile uživatel začne mluvit, přestaň mluvit.
- Přímý kód/API/můstek a Git jsou výchozí cesta. Nezačínej prohlížečem ani opakovaným přihlašováním.
- Schválený úkol proveď až po ověřený provozní výsledek. Nevracej pouze plán nebo tvrzení, že něco umíš.
- Již udělený souhlas platí v daném rozsahu. Znovu ho nevyžaduj. Ptej se pouze na skutečně chybějící rozhodnutí, přihlašovací údaj nebo souhlas vyžadovaný nadřazeným pravidlem nástroje.
- Nevyžaduj po Martinovi kopírování příkazů, klíčů nebo souborů, pokud práci umí provést dostupné nástroje.
- Neslibuj „plnou správu“, pokud neexistuje konkrétní funkční a ověřená operace. Manifest přístupy sám neuděluje.

## Krátký postup každé změny

1. Načti manifest, otevřené úkoly, čerstvý remote HEAD a potřebný živý stav. Hledej pomocí rg, nezjišťuj znovu známé základy.
2. Ověř dostupnou operaci a oprávnění. Chybějící operaci označ jako mezeru; nezkoušej stále stejnou nepodporovanou cestu.
3. Proveď nejmenší cílenou změnu. U opravy chyby nejprve reprodukce a regresní test. Neopakuj již schválenou návrhovou diskusi.
4. Ověř změnu, publikuj přes Git s kontrolou očekávaného HEAD, nasaď přes přímý můstek s CAS revision. Git commit není nasazení.
5. Polluj stejnou trvalou úlohu. queued/running/accepted/unknown není úspěch. Při unknown zjisti, která fáze nastala, a teprve podle důkazů rozhodni o dalším kroku. Nikdy slepě nereplikuj zápis novým request_id.
6. Potvrď běžící verzi a skutečný stav zařízení/funkce. Aktualizuj OPEN-WORK a provozní důkazy. Pak oznam výsledek a skutečné zbývající omezení.

## Prevence zdržení a kolizí

- Nespoléhej na paměť chatu nebo na soubory ve scratch. Trvalý zdroj je uvedená větev Gitu a nasazená konfigurace.
- Preferuj reload podporované části před celým restartem. Nový Python kód již načtené integrace může vyžadovat restart; netvrď opak bez ověření.
- Restartuj jen při potřebě a po kontrole místních změn, prostoru, ochrany a běžících úloh. Neměň současně nasazované soubory z jiného worku.
- Nevytvářej opakovaně velké zálohy bez znalosti volného místa a skutečné potřeby; zároveň neobcházej povinnou ochranu existujícího nasazovacího rozhraní.
- Při chybě zastav opakování a řeš příčinu. U nedostatku prostoru nezkoušej znovu tutéž zálohu.
- Klíče, hesla, session cookies, soukromé hlasové modely a nahrávky nepatří do Gitu ani uživatelských výpisů.
- Neprováděj upgrade HA Core/OS ani další nesouvisející změny jako vedlejší efekt opravy.
- Prohlížeč je pouze poslední možnost pro skutečně chybějící API; respektuj pravidla nástroje pro použití a přihlášení. Rozlišuj chybějící funkci od chybějící autentizace.
