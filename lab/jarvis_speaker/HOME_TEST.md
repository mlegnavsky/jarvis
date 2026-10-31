# Anička — následné ověření doma

Tato větev nyní obsahuje offline simulaci a export nastavení osobnosti.
Nemění domácí Green. Zelený test simulace nepotvrzuje funkčnost mikrofonu,
rozpoznání hlasu, přirozenost konverzace ani přehrávání HomePodu.

Před tímto testem musí vzniknout skutečné napojení: mikrofon a detektor oslovení
„Aničko“, rozlišení živé řeči od echa/televize, hlasové otisky a jejich schválení,
STT, konverzační model, český ženský TTS hlas a HomePod s potvrzením stop/konce
přehrávání. Je nutné propojit Jarvis backend a mapování mikrofonů na místnosti.
Obnova hlasitosti po restartu potřebuje trvalé uložení původních hodnot.
Tento dokument není návod k instalaci těchto dosud chybějících adaptérů.

Po propojení ověřit:

1. Řekni „Aničko“ potichu i nahlas z různých míst; změř prodlevu probuzení.
2. Poslechni český ženský hlas: příjemný, přirozený a energický. Nepředpokládat,
   že jde o stejný hlas jako v ChatGPT; vybrat podle skutečného poslechu.
3. Ověřený mluvčí řekne „rozsviť“; svítí správná místnost podle mikrofonu.
   Odpověď o úspěchu musí odpovídat ověřenému výsledku backendu.
4. Neznámý mluvčí zopakuje povel a pak se představí. Ani jeden krok nesmí
   zapnout světlo ani přehrát dříve odmítnutý povel. Schválení je samostatné.
5. Změň mluvčího uprostřed rozhovoru; ověření musí proběhnout pro každý povel.
6. Začni mluvit během odpovědi. HomePod musí skutečně přestat hrát; zaznamenat
   dobu do zastavení. Nestačí jen přepnout stav v programu.
7. Navazující dotaz do tří sekund od skutečného konce odpovědi pokračuje bez
   oslovení. Po třech sekundách je nutné nové „Aničko“. Delší samotný povel
   nesmí ukončit třísekundové okno pro ticho.
8. Zapni televizi/Apple TV. Po celou konverzaci je zvuk tišší, video se
   nezastaví a původní hlasitost se vrátí. Již tichou TV nezvyšovat.
9. Z televize i HomePodu přehraj podobná slova a oslovení. Nesmí probudit
   asistentku ani udělit oprávnění. Syntetický zdrojový štítek tento test nenahrazuje.
10. Přeruš spojení s výstupem, ukonči relaci a otestuj restart při ztlumení.
    Ověř obnovu hlasitosti, odmítnutí opožděných odpovědí a retry po výpadku.

Zaznamenat naměřené časy probuzení, identifikace (včetně sběru hlasu), zastavení
výstupu, chybná probuzení a výsledek každého bodu. Cíl <500 ms není zatím změřený.
Hlasová shoda sama nestačí k citlivým akcím, jako je odemknutí dveří nebo platba.
