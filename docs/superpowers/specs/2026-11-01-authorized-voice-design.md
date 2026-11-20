# Ověřené hlasové oslovení a povely — návrh 2026-11-01

Stav: návrh k odsouhlasení, nikoli nasazená funkce.

## Zadání
Martin potvrdil, že „zamkni“ a „odemkni“ vždy znamenají hlavní vchod.
„Aničko“ zahajuje rozhovor. Samostatné „rozsviť“ a „zhasni“ ovládají
pouze světla v místnosti zachycujícího mikrofonu. Žádná z těchto akcí
se neprovede pro neověřený hlas. Záznam z TV nesmí obejít kontrolu.

## Přístup
Navázat na existující lokální CAMPPlus, Assist a firmware Voice PE.
Alternativa trvalého přenosu zvuku do cloudu nepřináší ověření hlasu
a zbytečně mění existující řešení; náhrada celého asistenta není potřeba.
Zvolený technický návrh je rozhodnutí implementátorky, dosud ne schválení uživatelem.

## Chování
- Povolený profil na začátku pouze existující Martinův profil. Samotné
  založení dalšího hlasového profilu automaticky neuděluje oprávnění.
- Kontrola platí pro každý povel i během pokračujícího rozhovoru.
  Rozpoznání jména v textu ani identita přihlášeného terminálu nejsou hlasový důkaz.
- Neznámý hlas, nedostatek zvuku, více mluvčích, nejednoznačný výsledek
  nebo výpadek modelu znamená žádnou akci. Výsledky jsou jednorázové,
  vázané na tentýž zvukový úsek, mikrofon a povel, s krátkou expirací.
- Krátké slovo, z něhož nelze získat dost hlasových dat, vyvolá
  žádost o delší větu. Její nové ověření je podmínkou provedení.
  Dvouapůlsekundový limit se nesníží bez ověření přesnosti na skutečných vzorcích.
- „Aničko“ musí dostat vlastní akustický model. Detekce slova může
  interně spustit omezený sběr zvuku k ověření, ale sama není autorizací.
  Neověřený hlas nedostane běžný rozhovor ani ovládání domu.
- Nepoužívat přímé spuštění INTENT z pouhé detekce slova.
- Pro světla použít skutečnou oblast mikrofonu; chybějící oblast ani světla
  neznamenají návrat na celý dům nebo jinou místnost.
- Zamykání: lock.vstup_zamek_vchod, služby lock.lock / lock.unlock.
  Odemknutí neznamená otevření dveří (lock.open se nepoužije).
- Pokrýt také lokální zkratky a generované nástrojové povely, aby nemohly obejít kontrolu.
- Rozpoznávání mluvčího je pravděpodobnostní a současný systém nemá
  ověřenou detekci přehrávky hlasu. Neslibovat odolnost vůči nahrávce Martina.

## Současná zjištění
Existuje jeden uložený hlasový profil. CAMPPlus a adaptér jsou připravené.
Přímo prováděné povely rozsviť/zhasni jsou nyní blokované opravou
0f3e7f06f338825e6a45b4aa2488c417bdc5847a.
Nasazený firmware obsahuje jarvis_cz, rozsvit_cz a zhasni_cz;
neobsahuje model Aničko. Výcviková větev a pipeline již existují.
Aktivní mikrofon je v obýváku; zámek hlavního vchodu je v oblasti vstup.
Jarvis service policy zatím neobsahuje lock.unlock; případné rozšíření
musí zůstat jen pro uživatelem vyžádaný zámek a požadované služby.

## Ověření a nasazení
Nejprve regresní testy: neznámý/krátký hlas, cizí mikrofon, expirované
či znovu použité ověření, přepnutí mluvčího a chyby modelu.
Testy příkazů ověří přesné cíle a absenci jakékoli akce při odmítnutí.
Testy zámku používají náhradu zařízení; neodemykat skutečný vchod při testu.
Výcvik Aničko uchová model a jeho původ i výsledky; syntetický test
se nevydává za fyzický test v domácnosti. Neaktivovat neověřený model
jako cestu k ovládání zámku.
Nasazení přes Git, zálohu, revizní kontroly a ověřené opětovné spuštění.
Uživatelský test: Martin, cizí hlas, TV, ticho, krátké slovo a pokračující
rozhovor. Akustické fungování a odolnost vůči TV potvrdit až tímto testem.

## Upřesnění po kontrole návrhu
- Oprávnění navázat na stabilní voice_id Martinova profilu; nové založení stejného jména práva nepřenese.
- Čekající krátký povel má expiraci 10 sekund. Nová delší věta musí ověřit hlas a výslovně potvrdit tutéž akci a cíl. Libovolný rozhovor není potvrzení odemknutí.
- Ověření světel nelze použít pro zámek. Vynucení před lokálními příkazy i nástroji LLM.
- Samotné krátké oslovení otevře pouze šestisekundové okno pro doplnění hlasových dat; bez ověření se běžný rozhovor neotevře.
- Před přidáním pěti modelů ověřit kapacitu firmwaru a možnost přidat nová modelová ID. Současná správa dokládá nahrazování existujících ID; případné rozšíření musí mít vlastní testy a revizní ochranu.
- Fyzické testy zahrnou přehrávku Martinova hlasu. Bez detekce přehrávky neslibovat skutečnou autentizaci ani zaručenou ochranu proti TV.
