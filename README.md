# Jarvis pro Home Assistant Green

Experimentální doplňky pro načtení aktuálního stavu domácnosti, povolené povely a řízené aktualizace. **Dosud neověřeno na skutečném Greenu.** Samotná instalace nezapojí tento chat do domácnosti.

- **Jarvis** čte aktuální stavy, oblasti, zařízení, entity, služby a systémové informace. Povely jsou ve výchozím nastavení vypnuté, vyžadují klíč, seznam povolených entit/služeb a jedinečný identifikátor požadavku.
- **Jarvis Updater** vytvoří zálohu a přes Supervisor aktualizuje pouze Jarvise ze stejného repozitáře. Je oddělený, protože Supervisor nedovoluje doplňku aktualizovat sebe sama.

Kód vzniká zde → po kontrole se začlení do hlavní větve a zvýší verze → Supervisor nabídne aktualizaci → povolený požadavek spustí zálohu, aktualizaci a kontrolu. GitHub není tunel ani spojení do domácnosti.

[Instalace](docs/install.md) · [Propojení a API](docs/connection.md) · [Aktualizace a obnova](docs/updates.md) · [Ověření na Greenu](docs/acceptance.md)

## Lokální ověření

```sh
python -m pip install -r jarvis/requirements.txt PyYAML==6.0.3
PYTHONPATH=jarvis:jarvis_updater python -m unittest discover -s tests -t . -v
python scripts/check_manifest.py
```

Testy používají simulované HTTP/WebSocket rozhraní Home Assistantu a Supervisoru. CI sestavuje oba kontejnery pro arm64 i amd64; výsledek sestavení je nutné zkontrolovat před instalací. Nepřidávejte do repozitáře tokeny, zálohy ani skutečný inventář domácnosti.
