# Automatický a vlastní prodej elektřiny

Datum: 5. 11. 2026. Stav: vlastník výslovně požádal pokračovat realizací bez dalšího schvalovacího kola. Prodej nebyl aktivován.

Dodatek vlastníka: při plné baterii povolit nyní omezované přebytky panelů při kladné ceně, baterii ponechat na dražší intervaly; dnešní 16:00 je návrh k ověření skutečnými cenami. Evidovat historicky měření, ceny, rozhodnutí, změny a skutečně dodanou energii. Možných 6 kW nezobrazovat jako naměřený výkon, dokud se nepotvrdí. Výkon je kW, energie kWh.

Historie je součástí dodávky: rozšířit existující privátní 10s archiv o skutečné údaje měniče a baterie a obchodní stav, transakční události ukládat ihned trvale před fyzickým zápisem. Zachovat originální čas měření a cenových publikací, revize a důvody rozhodnutí. Výpadek odesílání má trvalou frontu; ztracené minulé vzorky nedopočítávat jako skutečná měření. Nezavádět mazání historických dat na serveru.

## Účel a dohodnutý rozsah

Řídit výhodný prodej přebytků z panelů a dostupné energie z baterie. Nákup pro dům zůstává u ČEZ za vlastníkem potvrzených 5 Kč/kWh včetně poplatků. Nezavádět automatické nabíjení ze sítě pro následný prodej.

Vlastník zvolil chytré plánování včetně baterie a počáteční minimální rezervu pro prodej 60 %. Požaduje také tlačítko Vlastní prodej s volbou výkonu a délky. Distribuční portál, který vlastník předložil 5. 11., uvádí rezervovaný výkon dodávky 9,500 kW. EnerSpot potvrdil registraci výkupu od 5. 11.; podepsaná smlouva určuje základní výkup OTE minus 300 Kč/MWh, patnáctiminutové vyhodnocení a kurz ČNB střed dne dodávky.

Úspěch znamená skutečně naměřenou dodávku, správnou cenu a ověřené ukončení prodeje, ne pouze přijatý povel nebo uložený soubor.

## Zvažované přístupy

1. Pouze okamžité přebytky panelů: jednoduché, omezená práce s baterií, méně možností přesouvat prodej.
2. Plánování panelů a baterie po čtvrthodinách: využije dražší období, vyžaduje odhad spotřeby/výroby, ekonomické porovnání a bezpečný řadič. Vlastníkem vybraná varianta.
3. Nakupovat ze sítě pro další prodej: mimo rozsah, vlastník výslovně nechce nákupní obchodní automatiku.

## Ověřený současný stav

- Zdrojová větev mlegnavsky/jarvis feat/jarvis-addon, výchozí HEAD 521b72c0ef2900b2e2eac334bf870a92997c50f0.
- Živý jarvis_spot_control 0.3.4 obsahuje pouze ruční nabíjecí test a obnovu. Nemá exportní službu. Jeho trvalý záznam a ověřování nastavení lze využít, nikoli vydávat za hotový prodejní řadič.
- Čtení Greenu 5. 11. kolem 12:45 Europe/Prague: Zero Export To CT, export_surplus off, export_surplus_power 9990 W. Limit 9990 W překračuje schválený rezervovaný výkon; před povolením dodávky musí být snížen a přečten zpět. V této návrhové práci nebyla provedena změna měniče.
- Maximální nabíjecí/vybíjecí proud je 175 A; nezvyšovat. Výkon dodávky do sítě je jiná veličina. Dodržet nižší z limitů měniče, BMS, baterie a instalace.
- Jarvis energy_weather 1.0.1 již získává ověřované čtvrthodinové EUR/MWh a datum/kurz ČNB. Dnešní převod používá poslední dostupný kurz; zítřejší CZK je orientační. Současný senzor výslovně nemá smluvní cenu.
- Existuje Open-Meteo předpověď. Její sluneční záření ani graf nejsou ověřenou předpovědí kWh konkrétní střechy. Repo zaznamenává 22 panelů, dva stringy po 11, jihovýchod a sklon 45 stupňů. Neodvozovat geometrii znovu z mapy.
- Přístupy k historii existují v HA; současný inventář konektoru vrací pouze aktuální stavy. Historická data lze zpracovat uvnitř nové nativní integrace přes oficiální HA API. Neřešit chybějící historii smyšlenými průměry.

## Cenová a energetická logika

1. Interní čas je UTC, obchodní den Europe/Prague. Každý interval má začátek i konec; podporovat dny o 92/96/100 čtvrthodinách a opakovanou podzimní hodinu.
2. Smluvní cena před případným daňovým vypořádáním je EUR/MWh × příslušný kurz Kč/EUR / 1000 − 0,30 Kč/kWh. Zachovat surová EUR, datum kurzu a jeho předběžnost. Nepřičítat automaticky DPH k příjmu vlastníka. Zítřejší prodejní rozhodnutí přepočítat po zveřejnění odpovídajícího kurzu.
3. Cena musí patřit skutečnému aktuálnímu intervalu. Nula, záporná hodnota, neplatná/nekonečná cena a chybějící interval znamenají zákaz prodeje i v ručním režimu. Nezaměnit chybějící data za nulu.
4. Plán porovnává prodej s ponecháním energie pro dům. Zahrnuje případný následný nákup od ČEZ, ztráty, opotřebení a bezpečnostní přirážku. Samotná kladná cena nestačí pro vybíjení baterie.
5. Plánovat zbytek dne a dostupné zveřejněné intervaly následujícího dne; předpovědní horizont alespoň 24 hodin. Neznámé budoucí ceny se nevymýšlejí. Chybějící zítřejší cena není automaticky důvod zastavit dnešní skutečný neuložitelný přebytek.
6. Pro první plánování jsou modelové, zveřejněné parametry: účinnost cyklu 90 %, náklad dodatečného cyklování 0,50 Kč/kWh dodané z baterie, minimální očekávané zlepšení proti ponechání energie 0,50 Kč/kWh prodeje z baterie. Jde o konzervativní návrhové předpoklady, nikoli naměřené hodnoty ani výrobní specifikace. Ztráty modelovat zvlášť při nabití/vybití, ne odečíst dvakrát.
7. Referencí ekonomického porovnání je běžná vlastní spotřeba se stejným počátečním a srovnatelným koncovým stavem baterie. Cena energie z panelů není automaticky 5 Kč/kWh. Nesmí vzniknout falešný zisk prostým vyprázdněním baterie na konci horizontu.
8. Výroba nejprve pokrývá potřebný výkon domu a chráněnou zásobu. Volnou energii lze uložit na dražší období, pokud to po nákladech zlepší výsledek. Přebytek bez možnosti účelného uložení/prospěšné vlastní spotřeby lze dodat při kladné ceně i pod 5 Kč/kWh.
9. Nabíjení a prodej nesmějí soupeřit. Řadič nesmí kvůli prodeji zapnout nabíjení ze sítě. Změny vlastníka nebo jiné automatizace musí vyvolat nové vyhodnocení a pozastavení obchodních zápisů; nesmí se donekonečna přepisovat.

## Rezerva a předpovědi

- 60 % je spodní hranice vybíjení za účelem prodeje, nikoli nový zákaz použití baterie pro běžnou spotřebu domu nebo zálohu při výpadku sítě.
- Pro automatiku může být účinná rezerva vyšší: max(60 %, energie potřebná pro očekávanou spotřebu do konzervativně očekávaného dobití plus nejistota). Očekávaná výroba může uvolnit pouze již dostupnou energii nad touto rezervou, ne prodávat energii, která dosud nevznikla.
- Odhad spotřeby vychází z časově odpovídající historie; při nedostatku historie použít doloženou konzervativní spotřebu nebo bateriový automatický prodej pozastavit. Hodinový průměr není jistota budoucího maxima.
- Kalibrovat model výroby proti měření; zatím nepodkládat automatický výdej baterie pouhým optimistickým odhadem počasí. Nedostatečná kvalita předpovědi snižuje povolený objem prodeje, nezvyšuje jej.
- Nemáme-li dost dat pro bateriový plán, může fungovat skutečný neuložitelný přebytek z panelů. UI musí říci, která část plánování je nedostupná.

## Provozní stropy a ochrany

- Smluvní maximum je 9500 W v předávacím místě. Navržený provozní strop je 9300 W. Pro všechny režimy se počítá celková skutečná dodávka z panelů i baterie po spotřebě domu, ne pouze výkon baterie.
- Nastavit a ověřit nativní Max Sell Power před povolením exportu. HA dohled je druhá vrstva, nikoli ochrana schopná zaručit omezení každé krátké špičky.
- Baterie: nepřekročit 175 A ani 10 kW, respektovat nižší aktuální limit BMS. Současný krátký nabíjecí test není důkaz povoleného vybíjecího výkonu instalace.
- Měření výkonu, SOC a relevantní stavy musí být čerstvé podle skutečného source/last_reported, ne jen opětovného renderu. Pro start požadovat vzorky do 30 s; dohled při stáří nad 30 s začne ukončení. Limity lze v implementaci zpřísnit podle reálné obnovy, ne uvolnit pro obejití výpadku.
- Vyžadovat Normal a OK alarm/fault na měniči, neaktivní bateriový alarm/fault, dostupnou teplotu a BMS. Pro úvodní provoz obchodního vybíjení použít konzervativní rozsah teploty baterie 0 až méně než 45 °C; je to provozní politika, ne celý výrobní rozsah vybíjení.
- Vnitřní teplota měniče není okolní teplota. Nesrovnávat ji s okolním rozsahem −40 až +60 °C a nevymýšlet výrobní vypínací mez. Zaznamenávat trend, alarmy a případné omezování výkonu; první testy musí zahrnovat tepelný průběh.
- Výpadek sítě okamžitě ruší obchodní požadavek; zálohování domu a nativní ochrany mají přednost. Neměnit anti-islanding, ochranné napětí/frekvenci, firmware ani elektrické zapojení.

## Řadič a ovládání

Stavy: vypnuto, připraveno, čeká na cenu/rezervu/data, připravuje prodej, prodej potvrzen měřením, ukončuje, blokováno poruchou, obnova nepotvrzena. Žádný souběh ručního nabíjecího testu, ručního prodeje a automatického obchodního vybíjení; jeden držitel řízení a trvalý transakční záznam.

Vlastní prodej otevře nativní podstránku mobilního dashboardu:

- Výkon jako maximální požadovaná dodávka do sítě, nikoli záruka dodaného výkonu; rozsah do provozního stropu. Počáteční návrh 1 kW.
- Délka 1 až 60 minut, výchozí 15 minut; případné delší obchodování řeší automatika po jednotlivých oknech.
- Ukázat aktuální čistou jednotkovou cenu po poplatku, rezervu, plánovaný konec a odhad dostupné energie. Při změně čtvrthodiny znovu vyhodnotit cenu. Ruční volba nahrazuje výběr nejvýhodnějšího okamžiku, ne bezpečnostní ochrany.
- Startovat až po vědomém stisku Spustit prodej; otevření podstránky nesmí vyvolat fyzický zápis. Hodnoty formuláře se samovolně nemažou ani se stránka nezavírá při obnově telemetrie.
- Jantarová znamená připravuji, modrá Prodej běží až po skutečně potvrzené dodávce, zelená připraveno, červená blokováno/chyba. Viditelný Stop, čas a dodaná energie. Samotný stav přepínače neznamená skutečný prodej.
- Úspěšné dokončení ručního prodeje vrátí předchozí povolený režim automatiky. Ruční Stop vše pozastaví prodej a automatika jej bez nového uživatelského povolení ihned neobnoví. Porucha také vyžaduje odstranění příčiny a vědomé obnovení.
- Rezervu lze do budoucna upravit nastavením, nikoli obejít servisním parametrem ručního formuláře. Během prodeje změna rezervy směrem nahoru okamžitě omezuje dostupnou energii.

## Měnič a chování při výpadku řízení

Oficiální manuál DEYE, kapitoly 5.7: Solar Sell v Zero Export To CT dovoluje přebytky panelů; Selling First spolu s Time of Use dovoluje také energii z baterie. Program Power je maximum vybíjení baterie, nikoli samostatný limit přetoků. Je třeba ověřit přesné mapování aktuální integrace/firmwaru, nativní SOC a exportní limit skutečným měřením při malém výkonu.

Před každým zápisem uložit původní hodnoty a zamýšlený bezpečný konec. Nastavovat nejdřív výkonové/SOC hranice a bezpečný následující interval, až poté povolit export. Číst skutečné potvrzení měniče. Při částečném selhání nejprve ukončit obchodní výdej, teprve pak vracet ostatní parametry. Nikdy neobnovit nebezpečný původní exportní limit 9990 W při aktivní dodávce.

Samotný HA časovač nemůže zaručit konec při vypnutém HA nebo přerušeném spojení. Aktivace vyžaduje ověřený nativní konec bateriového vybíjení/SOC a zkoušku ztráty spojení. Šest denních TOU oken není důkaz libovolného vzdáleného časovače. Režim prodeje nesmí další den nepozorovaně znovu spustit baterii.

Zvlášť ověřit, zda nativní ukončení bateriového výdeje zastaví i PV prodej. Pokud PV export při vypnutém HA může pokračovat, UI a předání musí přesně uvést toto omezení; úplné tvrzení „prodej vždy skončí po době“ je zakázané. Jestli zvolený měnič neumí požadovaný autonomní konec celého prodeje, nejdřív předložit vlastníkovi konkrétní zjištění a varianty (samostatný nezávislý dohled / vědomě omezený režim). Bez vyřešení této materiální otázky plnou automatiku nezapínat. Toto je technická ověřovací podmínka, ne tvrzení, že potřebná funkce chybí.

Po restartu nejdřív zpracovat trvalou rozpracovanou transakci, obnovit bezpečný stav a sladit skutečný měnič. Automatické pokračování starého ručního prodeje je zakázané. Konflikt s nezávislou ruční změnou se neřeší slepým návratem starého snapshotu.

## Finance a důkazy

Energii prodanou v jednotlivých čtvrthodinách odvozovat z ověřeného čítače dodávky a časových bodů; při nedostatečném rozlišení označit odhad nebo mezeru. Z resetu či chybějícího vzorku nevytvářet prodej. Naměřené kWh násobit příslušnými intervalovými cenami, nikoli dnešní cenou pro celý den.

Zobrazovat odděleně dodané kWh, odhad tržby po 0,30 Kč/kWh, modelové náklady a odhad přínosu. Částka v Jarvisu je provozní odhad; konečné vyúčtování vystavuje EnerSpot z distribučních dat. Původní finanční/meřicí historii nezpětně přeznačit za placený prodej.

## Realizace a přijetí

Navázat na native HA integraci a dashboard v tomto repozitáři. Plánovací výpočty oddělit od transakčního řadiče a adaptéru měniče. LLM nesmí přímo rozhodovat o nízkoúrovňovém zápisu ochranných hodnot. Vlastník rozhoduje o politice, deterministická kontrola vynucuje meze.

1. Implementovat cenovou/modelovou část a řízení bez aktivních obchodních zápisů. Ověřit DST, neplatná data, mezní SOC, ekonomickou alternativu, výkon panelů+baterie a konflikty ručního řízení.
2. Ověřit nativní limit, SOC, obnovu a konec po ztrátě spojení. Po dohodnuté aktivaci provést malý časově omezený fyzický prodej, počátečně nejvýše 0,5 kW po 3 minuty; nezkoušet rovnou 9,3 kW. Aktuální povolení zápisů zkontrolovat a případné rozšíření držet jen na konkrétní prodejní entity/služby.
3. Fyzicky prokázat dodávku, ukončení, návrat do bezpečného režimu a zachování rezervy. Až potom předat ruční tlačítko jako provozní.
4. Automatiku nejprve ověřit ve stínovém plánování se skutečnými cenami a daty. Přepnout ji do aktivního provozu až po splnění výše uvedených ochran a ověření proti skutečné spotřebě/výrobě.
5. Nasazení přes Git, aktuální HEAD/CAS a existující přímý můstek. Před restartem respektovat souběžné hlasové práce. Záloha, kontrola kapacity, přesný readback souborů, běžící verze a případné rollbacky podle pracovního manifestu. Žádný upgrade HA/OS ani nevyžádané změny jiných systémů.

Začátek programování neznamená aktivovaný prodej. Úspěšný test nabíjení neznamená ověřený prodej ani dlouhodobý tepelný test.

## Rozhodnutí ponechaná implementaci

Datové struktury, oddělení modulů, detailní optimalizační metoda, přístup k oficiálním recorder API, dostatečný kalibrační vzorek a cílené testy jsou na implementaci. Zvolené řešení musí prokázat výše uvedené chování; chybějící předpověď nebo nativní ochrana se nesmí nahradit tichým oslabením pravidel.

Návrhové výchozí hodnoty navíc oproti výslovné volbě vlastníka: provozní strop 9300 W, ruční rozsah 1–60 minut s výchozími 15 minutami / 1 kW, model 90 % a 0,50 Kč/kWh opotřebení + 0,50 Kč/kWh ekonomická rezerva. Nejsou prezentovány jako předchozí přání vlastníka. Před implementací je předložit spolu s tímto návrhem.

## Zdroje

- Živé readbacky Greenu 5. 11. 2026: spot_control/engine.py a energy_weather/__init__.py, aktuální inventář prodejních/programových parametrů. Zdrojový HEAD uveden výše.
- Vlastníkem předložený distribuční portál: 9,500 kW pro výrobní místo; soukromý snímek zůstává mimo veřejný Git.
- Soukromá podepsaná smlouva EnerSpot z 27. 10. a potvrzení registrace z 5. 11.; osobní údaje/EAN/bankovní spojení nevkládat do veřejného návrhu.
- DEYE SUN-(3–12)K-SG05LP3-EU-SM2, oddíly 5.7 a technické údaje: https://www.deyeinverter.com/deyeinverter/2024/08/13/instructions_sun-3-12k-sg05lp3-eu-sm2_240813_en.pdf
- Baterie Felicity FLA48460-EU: https://doc.felicitysolar.com/Manual-lang/2.FR/FR-Manual_FLA48460-EU%20Guide%20utilisateur%20-%20Fran%C3%A7ais.pdf
- OTE denní trh: https://www.ote-cr.cz/cs/kratkodobe-trhy/elektrina/denni-trh
