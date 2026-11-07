# Výkonové jednotky a ČEZ — 4.11.2026

Opraveno ve spot_control/card.js a spot_dashboard/card.js: malé výkony pod 1000 W jsou celé watty, ostatní kW. Energie kWh a ceny Kč/kWh zachovány. Kontrola živého YAML dashboardu: žádný další pevný převod do kW, 11 výskytů W. Osm hraničních případů ověřeno nad skutečně staženým JS; stávající card service-route test prošel. tests/power_units.cjs uchovává regresní příklady.

ČEZ nákup pevně 5 Kč/kWh výslovně potvrzen vlastníkem. OTE zůstává pouze testovací prodejní cena. Opraveny obě karty i nen nasazený nativní generátor native_view.py. Render test staženého JS ověřil Nákup · ČEZ · pevná sazba 5 Kč/kWh a zachování Prodej · test OTE.

Živý write units021-write verified; cez-write-card verified, revision e272e647ad8d822bef6a2934c679adf751fbb4e7b926851d4903f99456480784. Cloudflare vracel starý JS s cf-cache-status HIT, max-age 2678400; nestačí přepsat soubor. Configuration extra_module_url nyní /local/jarvis-spot-control.js?v=0.2.1-cez5. HTML tuto adresu potvrzeně vydává po aktivaci. Nová URL stažena a syntax/render ověřeny. Uživatelova již otevřená stránka vyžaduje obnovení, její vizuální vykreslení nebylo přímo sledováno.

units021-activate verified 16:18:22 UTC, backup c5b52834; následné uživatelovo upřesnění tarifu aktivováno cez-price-activate verified 16:25:16 UTC, backup 71b44763. Core 2026.6.4 RUNNING. Lease units021-release verified. Žádný nový nabíjecí test ani zvýšení proudu. Doporučený další test: současných 20 A a po minutě ručně Zastavit a vrátit, s ověřením návratu parametrů. Zvýšení výkonu je samostatný krok.

Viz docs/ENERGY-DATA-MAP.md pro parametry baterie, historii a aktuální limity. Není tvrzeno, že výpočet historického maxima byl dokončen.
