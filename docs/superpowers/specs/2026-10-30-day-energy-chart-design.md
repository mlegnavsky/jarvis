# Denní energetický graf
Martin požaduje pevnou osu dne 00:00–24:00, procházení myší s hodnotami a přepínače křivek nahoře. Realizovat nejprve přes laboratoř; neopakovat schvalovací otázky.
Upravit existující JarvisPowerSun SVG kartu. Alternativní nová knihovna by zbytečně přidala závislost; rolling 24h nesplňuje požadavek. Zvolená implementace zachová stávající výrobu, spotřebu, síť a Slunce.
Den je Europe/Prague včetně změn letního času. Budoucí měření nesimulovat. Nedostupná měření zobrazit jako chybějící, nikdy jako nulu. Interakce myš/dotyk/klávesnice. Přepínače a hodnoty nad grafem, výška Slunce na samostatné ose.
Veřejná laboratoř obsahuje výhradně označená syntetická data a tentýž JS jako karta. Produkční data ani přihlašovací údaje nepublikovat. Nasazení v laboratoři nezaměňovat za změnu Greenu.

## Rozšíření schválené vlastníkem
Do stejného grafu přidat baterii (%) a spotovou cenu (Kč/kWh bez DPH, před poplatky obchodníka), oba s přepínačem a barevnou vlastní stupnicí. Zachovat 3 výkony a Slunce. Přidat datum, předchozí/následující den a návrat na dnešek. Historie z HA recorderu podle jeho retence. Budoucí měření nikdy nevymýšlet; publikované čtvrthodinové ceny z existujícího senzoru zobrazit i dopředu, chybějící ceny označit. Při rychlém přepnutí dne nesmí pomalejší odpověď přepsat poslední vybraný den.


## Rychlost, spojení baterie a počasí
Vlastník žádá rychlejší načtení, přirozené spojení mezer baterie a lištu skutečného typu předpovídaného počasí s venkovní teplotou nad stejným grafem. Použít existující Open-Meteo senzor (7denní předpověď); starší neuchované počasí nevymýšlet. Baterii mezi dvěma platnými krajními měřeními lineárně odhadnout a značit přerušovanou čarou a ≈ v hodnotě; neextrapolovat bez měření na druhém konci. Cache sedmi navštívených dnů, nejvýše2min pro aktuální den a24h pro minulé; nepřekreslovat při změně nesouvisejícího zařízení. Kreslení zjednodušit při zachování extrémů a výpadků; kurzor číst z původních dat. Výchozí aktuální čas se aktualizuje, ručně zvolený čas se zachová.
