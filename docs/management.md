# Vzdálená správa od 3.1.0

Používá stejné připojení, klíče, maintenance_enabled a OAuth jarvis:maintain jako aktualizace. Zápisy navíc vyžadují writes_enabled. Oprávnění Supervisoru ani počet doplňků se nemění.

## Rozhraní

- jarvis_diagnostics(check_config=false): vybrané systémové nastavení, kapacita deníku; s true také kontrola konfigurace HA bez restartu.
- jarvis_automations(): entity, ID a stavy automatizací (nejvýše 500, total/truncated uvedeny).
- jarvis_automation_get(id): editorová definice a SHA-256 revize; chybějící definice má config=null a revision=missing. Nepřístupné API není chybějící definice.
- jarvis_automation_change(operation, id, expected_revision, config, request_id, backup_id?): save/delete/restore. save předává celou definici, alias a initial_state=false; delete/restore mají config={}; restore navíc backup_id.
- jarvis_automation_backups(): metadata posledních 100 změn, jejich výsledky a ID záloh.

Nejprve načíst definici a revizi. Před každou změnou je uložen původní obsah v /data/management.sqlite (0600), pak proveden zápis přes HA editorové API. HA ověřuje syntaxi a sémantiku. Zpětné načtení potvrzuje pouze uloženou definici. Po nejistém výsledku kontrolovat skutečný obsah a metadata; tentýž request_id se nikdy znovu nevykoná. Pro stejný záměr nezakládat nový request_id.

Obnova vrací původní definici s initial_state=false; záloha chybějící definice znamená odstranění nově vytvořené automatizace. Není to obnova celého domu. Běžící nezměněná automatizace může zůstat zapnutá, protože HA stejný obsah nemusí znovu načíst. Aktivaci/vypnutí ověřovat samostatně podle stavu entity. Zdroj: HA 2026.6.4 homeassistant/components/config/automation.py a view.py.

Revize brání zápisu známé zastaralé definice. HA neposkytuje atomický compare-and-swap proti současným úpravám v jiném editoru; během změny nepoužívat paralelně jiného editora.

## Již otevřený chat

Pokud katalog ještě neobsahuje nové nástroje, existující jarvis_action podporuje přesně pojmenované služby jarvis.automation_get/save/delete/restore pro entity automation.<ID>. Save data={expected_revision, config}; delete data={expected_revision}; restore data={expected_revision, backup_id}; get data={}. ID zde znamená editorové ID, nikoli nutně slug zobrazované entity.

Pro jarvis.diagnostics/automations/automation_backups je entity_id=jarvis.system a data={} (diagnostics smí obsahovat check_config typu boolean). Tento kompatibilní přenos vyžaduje **obě** OAuth oprávnění control a maintain a nic neposílá jako libovolnou HA službu.

## Limity a provoz

Deník drží nejvýše 1000 změn. Při naplnění odmítá všechny nové změny, včetně obnovy, dokud není správcem provedena řízená údržba deníku; API pro jeho promazání zatím není. Kontrolovat remaining v diagnostice. Čtení a vrácení výsledků již známých request_id zůstává dostupné. Deník nepřenášet do GitHubu; obsahuje soukromé konfigurační zálohy.

Tato verze nepovoluje libovolné soubory configuration.yaml, shell, instalaci cizích doplňků ani obecný proxy přístup. Ovládání zařízení stále používá své původní seznamy povolení. Katalog automatizací zobrazuje nahrané entity; nenačtené a jinam ručně vložené YAML definice nemusí mít editorové API.

## Ověření

Testy HTTP klienta, autorizace MCP, ochrany proti souběhu, restartu, přerušení, dvojímu zápisu, obnovy a plného deníku. Živý test vytváří pouze novou vypnutou testovací definici bez akcí na zařízení, zpětně ji čte, maže, obnovuje a uklidí. Výsledky instalace a zálohy jsou v trvalé úloze Updateru.
