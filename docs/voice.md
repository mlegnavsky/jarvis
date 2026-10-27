# Hlas doma a na mobilu — aktuální rozhodnutí

Martin zvolil dvě prostředí:

- **Doma Jarvis:** samostatný hlasový asistent přes OpenAI v Home Assistantu, místně probouzený „Hey Jarvis“. Green řídí domácnost, hlasový satelit poskytuje mikrofon a reproduktor.
- **Mobil Anička:** běžný ChatGPT spouštěný ručně. Domácí nástroje připojené přes autorizovaný MCP/OAuth se ověří podle docs/chatgpt.md. Dostupnost nástrojů v konkrétním hlasovém mobilním klientu stále vyžaduje zkoušku.

Předchozí návrh stavět domácí stálý poslech na skutečné aplikaci ChatGPT byl po vysvětlení omezení nahrazen samostatným domácím Jarvisem. Nevzniká automatické sdílení historie/paměti ani předplatného/API účtování mezi těmito prostředími.

Připravené soubory, pipeline, instrukce, TV automatizace a přesný checklist: **[home_voice/README.md](../home_voice/README.md)**.

## Ověřený stav 27. 10. 2026

Vzdálená správa je dostupná přes Jarvis3.7.0 a nezávislou bránu Updater1.0.0. Martin přesunul funkční Voice PE z chodby do obýváku. Jeho zařízení i zděděné oblasti entit nyní odpovídají obýváku, název je „Hlasový terminál - Obývák“. Původní odpojený terminál má odlišný název a nemá přiřazenou oblast. Identifikátory a párování jsou zachované.

Funkční terminál odpovídá jako idle, mikrofon není ztlumený a probouzecí slovo je Hey Jarvis. Dvě existující automatizace hlasitosti byly přesměrovány na skutečný terminál, načteny a jejich stav on ověřen. Jejich původní pravidla hlasitosti nebyla změněna. Akustický test nebyl proveden z kanceláře.

OpenAI konverzace/STT/TTS i místní hlasové aplikace jsou přítomné. Aktivní preferred pipeline byla ověřena: český Jarvis, Whisper → Extended OpenAI Conversation → OpenAI TTS (onyx). Vazba starého lokálního Jarvis Core0.1.0 dosud není potvrzená; nelze tvrdit synchronizovanou paměť ani hotové hlasové testy jen z přítomnosti integrací. Starší podrobný instalační návod v home_voice je návrh, nikoli autoritativní popis aktuální pipeline.
