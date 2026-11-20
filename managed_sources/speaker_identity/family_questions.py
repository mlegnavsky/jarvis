"""Czech enrollment prompts. Training phrases never execute device actions."""
QUESTIONS=(
 ('běžná řeč','Popiš prosím celou větou, co obvykle děláš doma večer. Mluv přirozeně asi šest až osm sekund.'),
 ('rozsvícení','Řekni prosím: Aničko, rozsviť světlo v obýváku, abychom tady večer dobře viděli na čtení.'),
 ('zhasnutí','Řekni prosím: Aničko, zhasni světlo v chodbě, protože už jsme všichni přešli do obýváku.'),
 ('tepleji','Řekni prosím: Aničko, přidej trochu teplo v dětském pokoji, protože je tam dnes večer chladno.'),
 ('chladněji','Řekni prosím: Aničko, uber prosím topení v obýváku, chtěli bychom tam mít trochu chladněji.'),
 ('kontrola místnosti','Kontrolní věta: Aničko, prosím rozsviť světlo v dětském pokoji, ať si tam můžeme v klidu číst.'),
 ('kontrola teploty','Kontrolní věta: Aničko, nastav prosím v obýváku příjemnou teplotu, protože tady budeme dnes odpočívat.'),
 ('kontrola vypnutí','Kontrolní věta: Aničko, zhasni prosím všechna světla v chodbě, už je dnes nebudeme potřebovat.'),
 ('hlasitost','Řekni prosím: Aničko, ztiš trochu televizi v obýváku, abychom si mohli nerušeně povídat.'),
 ('stav domácnosti','Řekni prosím: Aničko, řekni mi, jaká je teď doma teplota a jestli někde zůstalo rozsvíceno.'),
 ('odchod','Řekni prosím: Aničko, odcházím z obýváku, zhasni tam prosím světlo a trochu ztlum topení.'),
 ('běžná řeč','Popiš prosím celou větou, co bys doma chtěl dělat o víkendu. Stačí šest až osm sekund přirozené řeči.'),
)
COMMANDS={
 'světla':('Rozsviť.','Zhasni.','Rozsviť v obýváku.','Zhasni v dětském pokoji.','Rozsviť v chodbě.','Zhasni všude.'),
 'topení':('Přidej teplo.','Uber topení.','Nastav v obýváku dvacet jedna stupňů.','Jaká je teplota v pokoji?'),
 'zvuk a televize':('Ztiš televizi.','Přidej hlasitost.','Pozastav televizi.','Pokračuj v přehrávání.'),
 'rozhovor':('Zopakuj to prosím.','Mluv pomaleji.','Počkej chvíli.','Končíme.'),
 'stav domácnosti':('Kde zůstalo rozsvíceno?','Kolik dnes vyrobily panely?','Jaký je stav baterie?'),
}
