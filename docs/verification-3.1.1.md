# Odezva světel — 3.1.1, 27. 10. 2026

- Zdrojový commit 957a0db9ea3efd7eba33fa962ab65886f544510d.
- 95 testů OK, manifest a diff --check OK; nezávislá kontrola bez blokujících nálezů. Testy opožděného on/off, timeoutu, jasu a historického replay výsledku.
- CI run 40457321437: tests, containers (jarvis), containers (jarvis_updater) success.
- Živý upgrade b42c49ad0a274b8a8148266ab63c8a34: verified, backup_slug=f045bd83.
- Živý Jarvis hlásí 3.1.1, stream_connected=true.
- Jediné volání light.turn_off pro světlo obýváku: accepted=true, target_state_verified=true, replayed=false. Server request_ms=76, confirmation_ms=13, celý nástroj měřený klientem 775 ms.
- Před i po testu bylo světlo off. Toto je měření potvrzení již zhasnutého světla, nikoli přechodu ze svítícího stavu. Kvůli benchmarku se světlo nerozsvěcelo.

Potvrzení cílového stavu v nové odpovědi už nevyžaduje druhý inventář. Časy uvnitř serveru ani roundtrip nástroje nejsou celkovým časem odpovědi ChatGPT. U opožděného hlášení se čeká nejvýše 1,2 s; timeout či nepřesný jas nesmí být vydáván za úspěch. Při replayed=true je vráceno původní, historické pozorování.
