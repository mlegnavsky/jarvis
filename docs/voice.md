# Hlas doma a na mobilu — aktuální rozhodnutí

Martin zvolil dvě prostředí:

- **Doma Jarvis:** samostatný hlasový asistent přes OpenAI v Home Assistantu, místně probouzený „Hey Jarvis“. Green řídí domácnost, hlasový satelit poskytuje mikrofon a reproduktor.
- **Mobil Anička:** běžný ChatGPT spouštěný ručně. Domácí nástroje připojené přes autorizovaný MCP/OAuth se ověří podle docs/chatgpt.md. Dostupnost nástrojů v konkrétním hlasovém mobilním klientu stále vyžaduje zkoušku.

Předchozí návrh stavět domácí stálý poslech na skutečné aplikaci ChatGPT byl po vysvětlení omezení nahrazen samostatným domácím Jarvisem. Nevzniká automatické sdílení historie/paměti ani předplatného/API účtování mezi těmito prostředími.

Připravené soubory, pipeline, instrukce, TV automatizace a přesný checklist: **[home_voice/README.md](../home_voice/README.md)**.

Zatím není nasazený fyzický satelit, OpenAI účet/klíč nebyl konfigurován a žádná API konverzace se neprovedla. Získání credentials a první spárování proběhne doma, nikoli v této veřejné dokumentaci.
