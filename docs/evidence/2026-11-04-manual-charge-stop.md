# Ruční vypnutí nabíjecího testu — 4.11.2026

Martin potvrdil funkční zapnutí a ruční vypnutí. Přímé čtení po testu v 17:27–17:28 Europe/Prague:
- sensor.jarvis_spot_control idle od 17:27:10.799.
- Aktivní program 5: charging Disabled od 17:27:06.370, SOC zpět 30 % od 17:27:08.544. Ostatní programy rovněž Disabled / 30 %.
- battery_grid_charging_current obnoven na 40 A od 17:27:09.795. Globální battery_grid_charging on odpovídá původnímu stavu, neznamená běžící nucené nabíjení.
- Zero Export To CT, export_surplus off, zero_export_power 20 W zachováno.
- Baterie 17:27:59 vybíjela 340 W / 6,51 A, napětí 53,27 V, PV 0 W, load 230 W. Nabíjení tedy skutečně neběželo.
- Síť 17:27:44 hlásila -83 W (krátký vzorek dodávky), 17:28:09 +18 W odběr. Nelze tvrdit absolutně nulové okamžité přetoky jen z nastavení. První záporný vzorek nebyl zamlčen; další vzorek potvrdil návrat k malému odběru.

Výsledek: ruční zastavení a návrat pozorovaných parametrů potvrzeny. Průběh zapnutí uživatel pozoroval, asistent zachytil až stav po ukončení. Žádná nová změna proudu ani spuštění testu asistentem.
