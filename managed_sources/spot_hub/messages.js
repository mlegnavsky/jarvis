/* Czech presentation only. No service calls or changes to protection rules. */
(function(g){'use strict';
const names={native_mismatch:'Nastavení přečtené z měniče neodpovídá očekávaným hodnotám. Konkrétní rozdíly jsou v diagnostice.',native_conflict:'Nastavení měniče změnilo jiné ovládání. Automatika změnu nepřepisuje.',profile_changed:'Změnil se základní profil měniče.',native_clock:'Hodiny měniče neodpovídají požadovanému časovému programu.',running:'probíhá',measuring:'měřením sleduji dodávku',armed:'připraveno',stopping:'ukončuji',health:'Měření není čerstvé nebo měnič či baterie hlásí problém.',stale:'Naměřené údaje jsou zastaralé.',electrical_stale:'Chybí čerstvé údaje o proudu nebo napětí baterie.',measurement:'Chybí platné měření.',voltage:'Napětí baterie je mimo povolený rozsah.',current_limit:'Proud baterie překročil povolený limit.',battery_limit:'Byl překročen povolený výkon baterie.',early_export:'Dodávka byla zjištěna před začátkem povoleného okna.',arming_expired:'Čas pro přípravu nativního programu vypršel.',enable_expired:'Povolení spuštění prodeje vypršelo.',energy_budget:'Skončila dostupná energie pro tento prodej.',selected_block_missing:'Chybí platný vybraný prodejní blok.',budget:'Pro prodej už nezbývá energie nad rezervou.',measurement_or_health:'Chybí čerstvé měření nebo některý stav zařízení není v pořádku.',missing_measurement:'Chybí údaj o baterii nebo toku do sítě.',mode_changed:'Pracovní režim měniče se změnil.',price:'Výkupní cena není kladná nebo chybí platná cena.',export_limit:'Dodávka překročila povolený výkon.',battery_discharge:'Při prodeji pouze panelů bylo zjištěno vybíjení baterie.',reserve:'Baterie dosáhla nastavené rezervy.',deadline:'Skončilo časové okno prodeje.',no_surplus:'Výroba už nepokrývá spotřebu domu a prodej.',house_support:'Energie zůstává pro spotřebu domu.',manual:'Prodej byl ručně zastaven.',external_override:'Nastavení měniče změnilo jiné ovládání.',recovery:'Proběhla obnova po přerušení řízení.',start_failed:'Spuštění prodeje se nepodařilo dokončit.',stop_recovery:'Ukončení bylo dokončeno opakovanou kontrolou.',error:'Původní příčina chyby není doložená v tomto záznamu.'};
function translate(input){let s=String(input||'').replace(/^_Guard:\s*/,'');if(names[s])return names[s];
 if(/registr 145/.test(s)){const expected=s.match(/požadováno\s+([01])(?:[, .]|$)/)?.[1],actual=s.match(/naměřeno\s+([01])(?:[, .]|$)/)?.[1];const action=expected==='1'?'zapnutí':expected==='0'?'vypnutí':'změnu';return 'Měnič nepotvrdil '+action+' prodeje přebytků. '+(actual==='1'?'Čtení ukázalo zapnuto.':actual==='0'?'Čtení ukázalo vypnuto.':'Aktuální stav je neurčený nebo se čtení neshodují.');}
 if(/registr 143/.test(s))return 'Měnič nepotvrdil požadovanou změnu maximálního výkonu dodávky do sítě.';
 if(/registr 142/.test(s))return 'Měnič nepotvrdil požadovaný pracovní režim.';
 if(/registr 104/.test(s))return 'Měnič nepotvrdil nastavení cílového odběru při omezení přetoků.';
 if(/TimeoutError|timed out|timeout/i.test(s))return 'Vypršel čas čekání na odpověď měniče nebo potvrzení nastavení.';
 if(/runtime_data/.test(s))return 'Integrace měniče nebyla připravená. Záznam se týká komunikace se zařízením.';
 for(const [key,text]of Object.entries(names))s=s.replace(new RegExp('\\b'+key+'\\b','g'),text);
 s=s.replaceAll('number.inverter_export_surplus_power','Limit výkonu do sítě').replaceAll('switch.inverter_export_surplus','Povolení prodeje přebytků').replaceAll('select.inverter_work_mode','Pracovní režim měniče');
 if(/_Guard:|[a-z]+_[a-z]+|Native |native |stopped|restoration|cleanup/i.test(s))return 'Řízení se zastavilo kvůli chybě ověření měniče. Podrobnosti jsou v původní technické hlášce níže.';
 return s;
}
function stopInfo(stop,root){if(!stop)return null;
 const code=stop.original_reason||stop.reason,triggers=stop.context?.triggers||[];
 const matched=root&&root.sale_id===stop.id;
 return {cause:matched?translate(root.error):stop.failure_detail?translate(stop.failure_detail):triggers.length?triggers.map(translate).join(' '):translate(code),
  cleanup:stop.error||stop.failure_detail?translate(stop.error||stop.failure_detail):'Bez zaznamenané chyby při ukončování.',
  outcome:stop.stop_verified===true?'Zastavení a obnova nastavení byly následně potvrzené.':'Ukončení prodeje zatím není potvrzené.',
  technical:JSON.stringify({reason:stop.reason,original_reason:stop.original_reason,triggers,error:stop.error,failure_detail:stop.failure_detail,stopped_at:stop.stopped_at,mode:stop.mode,failure_context:stop.failure_context,failures:stop.failures,stop_verified:stop.stop_verified,root:matched?root:undefined},null,2)};
}
const api={translate,stopInfo};if(typeof module!=='undefined')module.exports=api;g.JarvisMessages=api;
})(typeof window==='undefined'?globalThis:window);
