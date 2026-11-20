const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const classes={};
class Element {
 attachShadow(){const nodes={};this.shadowRoot={set innerHTML(html){for(const [,id] of html.matchAll(/id="([^"]+)"/g))nodes[id]={value:'',textContent:'',disabled:false,hidden:false};},getElementById:id=>nodes[id]};}
}
vm.runInNewContext(fs.readFileSync(__dirname+'/../home-message.js','utf8'),{HTMLElement:Element,window:{},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c}});
(async()=>{
 const c=new classes['jarvis-home-message'](),calls=[];c.setConfig({});
 c.hass={states:{'media_player.homepod_obyvak_homepod_obyvak':{state:'off'}},callService:async(...a)=>calls.push(a)};
 assert.ok(c._el('message'),'iPhone must have a text field even without browser speech recognition');
 c._dictate();assert.match(c._el('status').textContent,/klávesnic/i);
 c._el('message').value='  Večeře je na stole.  ';await c._el('send').onclick();
 assert.equal(calls.length,1);assert.equal(calls[0][0],'tts');assert.equal(calls[0][2].message,'Večeře je na stole.');
 assert.equal(calls[0][2].media_player_entity_id,'media_player.homepod_obyvak_homepod_obyvak');
 c._el('message').value='  ';await c._send();assert.equal(calls.length,1,'blank text does not speak');
 c._el('message').value='Další vzkaz';c._hass.states[c._config.media_player].state='unavailable';await c._send();assert.equal(calls.length,1);assert.equal(c._el('message').value,'Další vzkaz');
 c._hass.states[c._config.media_player].state='off';let done;c._hass.callService=()=>new Promise(r=>done=r);
 const first=c._send();await c._send();assert.equal(c._el('send').disabled,true);done();await first;assert.equal(c._el('send').disabled,false);
 c._hass.callService=async()=>{throw new Error('failed');};await c._send();assert.match(c._el('status').textContent,/nepodařilo/);assert.equal(c._el('message').value,'Další vzkaz');
 console.log('Home message: iPhone text/dictation fallback, explicit playback, validation, offline, duplicate and failure checks passed');
})().catch(e=>{console.error(e);process.exit(1)});
