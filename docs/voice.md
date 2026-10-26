# Anička doma i na mobilu — zvolený směr

Martin upřesnil, že chce běžný rozhovor přímo s ChatGPT (Aničkou), včetně domácího ovládání během hovoru, doma i mimo domov. Samostatný HA Assist/agent přes modelové API tento požadavek sám nesplňuje. Primární řešení proto bude skutečný klient ChatGPT + autorizovaný Jarvis MCP.

## Co bylo ověřeno v dokumentaci 26. 10. 2026

Oficiální [ChatGPT Voice](https://learn.chatgpt.com/docs/features/voice) popisuje hlas v desktopové aplikaci, navázání na existující rozhovor/úkol podle rollout dostupnosti a stejná oprávnění jako u příslušného úkolu. [Plugins](https://learn.chatgpt.com/docs/plugins) popisuje pluginy a MCP nástroje na podporovaných plochách včetně mobilu; dostupnost konkrétního pluginu se liší. [Custom MCP setup](https://developers.openai.com/api/docs/guides/custom-mcp-server) se provádí na webu.

To potvrzuje směr pro zkoušku, nikoli funkční propojení tohoto účtu, Jarvise a hlasu. Vlastní MCP, nativní mobil, hlasové režimy a existující rozhovor je nutné ověřit na konkrétním účtu/zařízení. Z dokumentace nevyplývá trvalé naslouchání na domácí oslovení ani podpora libovolného chytrého reproduktoru.

## Postup ověření

1. Na webu autorizovat skutečný Jarvis MCP po domácí instalaci a spuštění tunelu. Ověřit čtení skutečné entity textovým dotazem.
2. V desktopové aplikaci ChatGPT ověřit dostupnost stejného pluginu/nástrojů a hlasu v rozhovoru. Začít jen čtením: během běžného hovoru se zeptat na teplotu a porovnat odpověď s HA.
3. Teprve potom vyzkoušet jeden povolený povel během hovoru a potvrzení případně požadované klientem. Zachovat stejný request_id při retry.
4. Doma nejprve použít existující počítač s mikrofonem a reproduktorem. Nic dalšího nekupovat, dokud tato cesta neprojde. Ověřit ozvěnu, slyšitelnost, mikrofon, odpojení hlasu a ruční spuštění/zastavení.
5. Na Martinově telefonu samostatně ověřit stejný účet, dostupný plugin, hlas a mobilní data. Rozlišit mobilní prohlížeč a nativní aplikaci. Případné propojení telefonu s desktopovým hostem závisí na operačním systému a dostupnosti funkce; neslibovat univerzálně.
6. Až po úspěšné zkoušce rozhodnout o stálém domácím zařízení a případném spouštění hlasu. Green zůstává správcem domácnosti, nikoli klientem ChatGPT.

## Hranice

- Tento postup zatím nebyl proveden na Greenu ani v reálném hlasovém rozhovoru s připojeným Jarvisem.
- Navázání na tentýž rozhovor není automatické sjednocení paměti a historie všech chatů.
- Bez otevřeného/aktivního klienta neslibujeme naslouchání ani autonomní rozhovor. Trvalá domácí pravidla provozuje HA.
- Samostatný API hlasový agent může být pozdější alternativou, pouze pokud Martin přijme odlišnou historii/paměť a případné API náklady. Není výchozím směrem tohoto projektu.
