# Daily Energy Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Denní graf 00:00–24:00 s hodnotami pod kurzorem a přepínači nahoře v laboratoři.
**Architecture:** Zachovat samostatnou SVG kartu a přidat oddělenou veřejnou ukázku se syntetickými daty.
**Tech Stack:** JavaScript Web Components, SVG, Python publisher, Node test.
**Spec:** docs/superpowers/specs/2026-10-30-day-energy-chart-design.md

## Global Constraints
- Europe/Prague, žádné produkční údaje v laboratoři, žádný restart Greenu.

## Review Focus
- Změny času: 23h/25h kalendářní den.
- Chybějící a budoucí data: žádné falešné nuly.
- Obnova HA stavu nesmí zrušit kurzor nebo přepínače.
- Mobilní šířka a dotyk, klávesnice.
- Publisher musí přenést přesně aktuální kartu.

### Task 1: Karta a laboratorní publikace
- [x] Regresní Node test pro pražské hranice dne a neplatné hodnoty, nejprve red.
- [x] Upravit kartu, laboratorní ukázku a allowlist publisheru.
- [x] Ověřit Node testy, Python publikaci a vykreslení/interakci v prohlížeči.
- [ ] Publikovat přes Git CAS, ověřit CI a skutečné HTTP soubory.

### Task 2: Baterie, ceny a datum
- [ ] Přidat historii baterie/spotu a přesné intervaly již publikovaných cen, výběr dne s ochranou pořadí požadavků.
- [ ] Přidat samostatné stupnice, přepínače, kalendář a šipky do stejné SVG karty.
- [ ] Ověřit datum/DST/záporné ceny/chybějící data a prohlížeč, publikovat do laboratoře.
- [ ] Nasadit přes CAS a změnit nativní Lovelace resource URL; ověřit skutečný graf na Greenu.


### Task 3: Rychlost a počasí
- [x] Omezit překreslení na související entity, přidat cache a binární čtení kurzoru.
- [x] Zjednodušit kreslené body, zachovat špičky a výpadky.
- [x] Doplnit rozlišený odhad baterie a časově zarovnanou lištu počasí/venkovní předpovídané teploty.
- [ ] Ověřit cílené regresní a Chromium testy, publikovat a nasadit přes CAS, změnit resource URL a ověřit živý graf.
