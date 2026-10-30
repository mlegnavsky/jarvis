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
