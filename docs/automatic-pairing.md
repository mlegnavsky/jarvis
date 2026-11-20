# Automatické propojení Jarvise a Updateru

Od Updateru 0.2.0 lze výslovně povolit `auto_pairing: true` společně s `updates_enabled: true`. Ruční tokeny Updateru zůstanou prázdné. Výchozí stav obou přepínačů je vypnuto.

Updater odvodí jediný povolený cíl z vlastního identifikátoru repozitáře, načte jeho konfiguraci interním Supervisor API a vytvoří vlastní náhodný klíč v `/data/pairing.json` s oprávněním 0600. Žádný klíč není součástí zdrojového kódu ani odpovědí API. Existující REST klíč Jarvise se použije pouze uvnitř procesu pro kontrolu zdraví.

Před zápisem nastavení vznikne částečná záloha Jarvise. Updater zachová ostatní volby, potvrdí zápis a restartuje Jarvise. Změny nastavení během zálohování zápis zablokují. Opakovaný start již spárovaného Updateru nic nepřepisuje a Jarvise nerestartuje. Odebrané oprávnění nebo změněný/odstraněný klíč neobnovuje automaticky.

Zapnutí údržby přidá nástroje pro kontrolu a aktualizaci do serverového katalogu MCP. ChatGPT musí obnovit katalog a získat OAuth rozsah `jarvis:maintain`; starší grant pouze pro čtení se sám nerozšíří. Stejně platí `jarvis:control` pro ovládání zařízení. Updater smí aktualizovat pouze sourozeneckého Jarvise, nikoli sám sebe, Core nebo libovolnou aplikaci.

Při obnově ze zálohy je nutné zachovat kompatibilní dvojici konfigurace Jarvise a `/data/pairing.json` Updateru. Neshodné klíče zůstanou bezpečně zablokované. Pro odpojení vypněte `auto_pairing` a `updates_enabled` v Updateru a údržbu v Jarvisovi; samotné vypnutí Updateru nemaže dříve uložený klíč.

Ověření vydání: automatizované testy zálohy před zápisem, stejného cíle, trvalého klíče, zachování voleb a respektování odebrání oprávnění. Živé připojení OAuth a údržbu je nutné ověřit na skutečném Greenu.
