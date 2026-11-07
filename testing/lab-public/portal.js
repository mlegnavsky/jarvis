'use strict';
const origin='https://raw.githubusercontent.com/mlegnavsky/jarvis/lab/plesk-bootstrap-20261029/';
const statusBox=document.getElementById('status');
async function refresh(){
 try{
  const response=await fetch(origin+'catalog.json?t='+Date.now(),{cache:'no-store'});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const data=await response.json();
  if(!Array.isArray(data.releases))throw new Error('Neplatný formát přehledu');
  statusBox.replaceChildren();const p=document.createElement('p');
  p.textContent=data.releases.length?'Poslední testovaný commit: '+data.releases[0].source_commit+' · '+data.releases[0].verified_at:'Zatím žádná publikovaná verze';statusBox.append(p);
  const out=document.getElementById('releases');out.replaceChildren();
  for(const release of data.releases){
   if(!/^[a-f0-9]{40}$/.test(release.source_commit))continue;
   const section=document.createElement('section');const title=document.createElement('h3');title.textContent=release.source_commit.slice(0,12);section.append(title);
   for(const pkg of release.packages||[]){
    if(!/^[a-z0-9_.-]+\.zip$/.test(pkg.file))continue;
    const p=document.createElement('p');const a=document.createElement('a');a.href=origin+'releases/'+release.source_commit+'/'+pkg.file;a.textContent=pkg.app+' '+pkg.version+' — zdrojový ZIP';p.append(a);section.append(p);
   }
   for(const [file,label] of [['release.json','Kontrolní součty'],['heating-report.json','Výsledky simulace']]){const a=document.createElement('a');a.href=origin+'releases/'+release.source_commit+'/'+file;a.textContent=label;section.append(a,document.createTextNode(' · '));}
   out.append(section);
  }
 }catch(e){statusBox.textContent='Aktuální přehled nelze načíst. Nejde o potvrzení úspěšných testů. '+e.message;document.getElementById('releases').replaceChildren();}
}
document.getElementById('refresh').addEventListener('click',refresh);refresh();
