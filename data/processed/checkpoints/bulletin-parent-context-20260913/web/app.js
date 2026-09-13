'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="workspace-token"]').content;
let busy = false;
let conversationId = null;
const labels = {precipitation:'Rainfall total',temperature_2m:'Temperature',wind_speed_10m:'Wind speed',relative_humidity_2m:'Relative humidity'};
const states = {prototype_answer:'Forecast available',needs_selection:'Choose your place',needs_clarification:'A little more detail',unavailable:'Evidence unavailable',stale:'Refresh needed',partial:'Incomplete coverage',degraded:'Refresh incomplete',outside_validity:'Choose a future window'};
function el(tag, text, cls) { const node=document.createElement(tag); if(text!==undefined)node.textContent=text; if(cls)node.className=cls;return node; }
function humanTime(value) { return new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'})+' IST'; }
function selectionFromForm() {
  if ($('location-mode').value!=='point') return {};
  if (!$('latitude').value.trim() || !$('longitude').value.trim()) throw Error('Enter both latitude and longitude.');
  return {coordinates:{latitude:Number($('latitude').value),longitude:Number($('longitude').value)}};
}
function toggleLocation() {
 const point=$('location-mode').value==='point';
 $('point-fields').hidden=!point;$('name-fields').hidden=point;$('place').required=!point;
 $('latitude').required=point;$('longitude').required=point;
}
$('location-mode').addEventListener('change',toggleLocation);
function fail(message) { $('error').textContent=message;$('error').hidden=false; }
function setBusy(value) {
 busy=value;
 document.querySelectorAll('button').forEach(button=>button.disabled=value);
 $('busy').textContent=value?'Understanding your question and retrieving evidence…':'Powered by local Ollama · Source-backed answers';
}
async function send(body, refresh=false, showQuestion=true) {
 if(busy)return;
 $('error').hidden=true;
 if(showQuestion)$('thread').append(el('div',body.question,'question-bubble'));
 setBusy(true);
 try {
  const payload={...body}; if(conversationId)payload.conversation_id=conversationId;
  const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-WeatherGPT-Token':token},body:JSON.stringify(payload)});
  const packet=await response.json();
  if(!response.ok)throw Error(packet.error || 'The request could not be completed.');
  if(packet.conversation_id)conversationId=packet.conversation_id;
  const card=packet.schema_version==='weather-conversation-v1'?renderConversation(packet,body):render(packet,body);$('thread').append(card);
  card.scrollIntoView({behavior:'auto',block:'nearest'});
 } catch(error) {fail(error.message || 'The local workspace is unreachable. Restart it and reload this page.');}
 finally {setBusy(false);}
}
$('builder').addEventListener('submit',event=>{
 event.preventDefault();
 try {
  const point=$('location-mode').value==='point';
  const place=point?'selected point':$('place').value.trim();
  const intent=$('measure').value==='rain'?'How much rain is forecast':`What is the ${$('measure').value} forecast`;
  const question=`${intent} for ${place} ${$('day').value} from ${$('start').value} to ${$('end').value}?`;
  $('question').value=question;send({question,...selectionFromForm()});
 } catch(error){fail(error.message);}
});
$('ask-form').addEventListener('submit',event=>{
 event.preventDefault();
 try {send({question:$('question').value.trim(),...selectionFromForm()});}catch(error){fail(error.message);}
});
function render(packet, body) {
 const a=packet.answer,card=el('article',undefined,'answer-card');
 const top=el('div',undefined,'answer-top');
 top.append(el('strong','WeatherGPT'),el('span',states[a.status]||a.status,'status'+(a.status==='prototype_answer'?'':' held')));card.append(top);
 card.append(el('p',a.answer,'answer-copy'));
 if(a.status==='degraded')card.append(el('p','These values come from the last published forecast. A due collection is incomplete. Request a successful refresh before relying on a current answer.','notice'));
 const clarification=packet.context.clarification;
 if(clarification && clarification.candidates.length) {
  const choices=el('div',undefined,'choices');
  clarification.candidates.forEach(c=>{
   const choice=el('button',`${c.label} · ${c.kind}`,'choice');choice.type='button';
   choice.append(el('small',`${c.namespace} · ${c.version}`));
   choice.addEventListener('click',()=>send({question:body.question,entity_id:c.entity_id},false,false));
   choices.append(choice);
  });card.append(choices);
 }
 if(a.values.length) {
  const metrics=el('div',undefined,'metrics');
  a.values.forEach(v=>{
   const m=el('div',undefined,'metric');m.append(el('small',labels[v.parameter]||v.parameter));
   const value=v.coverage!=='complete'?'Unavailable':v.value_decimal!==undefined?`${v.value_decimal} ${v.unit}`:`${v.min_decimal}–${v.max_decimal} ${v.unit}`;
   m.append(el('strong',value));m.append(el('small',v.parameter==='precipitation'?'Sum over the exact requested interval':'Range of hourly samples; not continuous extremes'));metrics.append(m);
  });card.append(metrics);
 }
 if(a.location?.requested_point) {
  const receipt=el('section',undefined,'receipt');const dl=el('dl');
  const add=(label,value)=>{dl.append(el('dt',label),el('dd',value));};
  add('Selected point',`${a.location.label} · ${a.location.requested_point.latitude}, ${a.location.requested_point.longitude}`);
  if(a.request)add('Window',humanTime(a.request.start_utc)+' → '+humanTime(a.request.end_utc));
  if(a.freshness){add('Retrieved',humanTime(a.freshness.retrieved_at_utc));add('Refresh health',a.freshness.refresh_health);add('Model issued','Unknown');}
  if(a.location.returned_grid)add('Model grid',`${a.location.returned_grid.latitude}, ${a.location.returned_grid.longitude} · ${a.location.grid_distance_km} km from selected point`);
  receipt.append(dl);
  a.citations.forEach(c=>{ const p=el('p'); const link=el('a',`${c.provider} · ${c.product}`);const url=new URL(c.url);if(url.protocol==='https:'){link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';p.append(link);receipt.append(p);} });
  if(a.values.length)receipt.append(el('p','Model output is not an observation or a district average. Local representativeness has not been independently validated.'));
  card.append(receipt);
 }
 const actions=el('div',undefined,'actions');
 if(a.location?.status==='selected_point' && a.request && ['prototype_answer','stale','degraded','partial','unavailable'].includes(a.status)){
  const refresh=el('button','Refresh this forecast');refresh.type='button';
  refresh.addEventListener('click',()=>send(body,true,false));actions.append(refresh);
 }
 const download=el('button','Download evidence');download.type='button';
 download.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(packet,null,2)],{type:'application/json'}));const link=el('a');link.href=url;link.download='weathergpt-evidence.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 actions.append(download);card.append(actions);
 if(packet.refresh)card.append(el('p',packet.refresh.message,'refresh-note'));
 const detail=el('details',undefined,'receipt');detail.append(el('summary','Inspect answer and source evidence'),el('pre',JSON.stringify(packet,null,2)));card.append(detail);
 // A stored answer card is a timestamped receipt, not a perpetually current answer.
 if(packet.context.expires_at_utc){
  const expiry=Date.parse(packet.context.expires_at_utc);
  const notice=el('p',`Evidence serving lifetime ends ${humanTime(packet.context.expires_at_utc)}. Ask again before using it.`,'hint');card.append(notice);
  const expire=()=>{top.querySelector('.status').textContent='Expired · ask again';top.querySelector('.status').classList.add('held');notice.textContent='This earlier response has expired. Ask again or refresh to check current evidence.';};
  setTimeout(expire,Math.max(0,expiry-Date.now()));
 }
 return card;
}

$('history-example').addEventListener('click',()=>{const question='What was the annual rainfall in Ahmedabad district, Gujarat in 2010?';$('question').value=question;send({question});});
$('new-conversation').addEventListener('click',()=>{conversationId=null;$('thread').replaceChildren(el('article','New conversation. Ask about a forecast, a historical rainfall value, or explain what you are planning.','welcome'));$('question').value='';send({question:$('question').value});});
function renderConversation(packet,body) {
 const card=el('article',undefined,'answer-card');
 const top=el('div',undefined,'answer-top');
 const stateLabels={answered:'Evidence retrieved',partial:'Weather evidence · additional information needed',needs_selection:'Choose a place',needs_clarification:'One detail needed',unavailable:'Evidence gap',explanation:'General explanation',outside_validity:'Choose an upcoming window'};
 top.append(el('strong','WeatherGPT'),el('span',stateLabels[packet.status]||packet.status,'status'+(packet.status==='answered'?'':' held')));card.append(top);
 const copy=el('p',packet.answer,'answer-copy');card.append(copy);
 if(packet.choices.length){
  const choices=el('div',undefined,'choices');
  packet.choices.forEach(c=>{const button=el('button',c.label,'choice');button.type='button';button.append(el('small',`${c.source_id} · ${c.coordinates.latitude}, ${c.coordinates.longitude}${c.match_type?' · '+c.match_type:''}`));button.addEventListener('click',()=>send({question:body.question,selection_id:c.selection_id},false,false));choices.append(button);});card.append(choices);
 }
 if(packet.task_coverage){card.append(el('p',`${packet.task_coverage.completed} of ${packet.task_coverage.requested} requested tasks completed`,'hint'));}
 (packet.charts||[]).forEach(chart=>card.append(historicalChart(chart)));
 (packet.calculations||[]).forEach(c=>{const p=el('p',`${c.label}: ${c.value} ${c.unit} · ${c.expression||c.method}`,'notice');card.append(p);});
 if(packet.task_results && packet.task_results.length>1){const detail=el('details',undefined,'receipt');detail.open=true;detail.append(el('summary','Requested tasks'));packet.task_results.forEach(t=>detail.append(el('p',`${t.id} · ${t.request.kind} / ${t.request.operation} · ${t.status}`)));card.append(detail);}
 if(packet.facts.length && packet.facts.length<=12){const metrics=el('div',undefined,'metrics');packet.facts.forEach(f=>{const m=el('div',undefined,'metric');m.append(el('small',f.label),el('strong',`${f.value} ${f.unit}`));if(f.place)m.append(el('small',f.place));if(f.start)m.append(el('small',humanTime(f.start)+' → '+humanTime(f.end)));if(f.year)m.append(el('small',`${f.year} · ${f.period}`));metrics.append(m);});card.append(metrics);}
 if(packet.notes.length){const detail=el('details',undefined,'receipt');detail.open=true;detail.append(el('summary','Scope and assumptions'));packet.notes.forEach(n=>detail.append(el('p',n)));card.append(detail);}
 (packet.passages||[]).forEach(passage=>{const detail=el('details',undefined,'receipt');const context=passage.evidence_kind==='published_bulletin_context';const label=context?`Bulletin context: ${passage.section}`:`${passage.crop} · ${passage.stage||'Stage not stated'}`;detail.append(el('summary',`${label} · ${passage.district} · Page ${passage.page}`),el('p',`Published ${passage.issue_date}. Forecast context ${passage.forecast_start}–${passage.forecast_end}.`,'hint'),el('p',passage.text));if(context)detail.append(el('p','Source context only; current warning and individual field applicability remain unverified.','hint'));const source=packet.citations.find(c=>(passage.citation_ids||[]).includes(c.id));if(source){try{const url=new URL(source.url);const local=source.local_document_path;const archived=typeof local==='string' && /^\/api\/documents\/[a-f0-9]{64}$/.test(local);if(archived || url.protocol==='https:'){url.hash='page='+passage.page;const link=el('a',archived?'Open the saved source PDF':'Open the original bulletin page');link.href=archived?local+'#page='+passage.page:url.href;link.target='_blank';link.rel='noopener noreferrer';detail.append(link);if(archived){const download=el('a','Download saved PDF');download.href=local;download.download='bulletin-'+local.split('/').pop()+'.pdf';detail.append(el('span',' · '),download);}}}catch{}}card.append(detail);});
 if(packet.follow_up)card.append(el('p',packet.follow_up,'notice'));
 const sources=el('section',undefined,'receipt');const seen=new Set();packet.citations.forEach(c=>{const key=c.source_id+'|'+c.url;if(seen.has(key))return;seen.add(key);const p=el('p');if(c.url){try{const url=new URL(c.url);if(url.protocol==='https:'){const a=el('a',`${c.provider||c.source_id} · ${c.product||'Source evidence'}`);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';p.append(a);}}catch{}}if(c.retrieved_at_utc)p.append(el('small',' · Retrieved '+humanTime(c.retrieved_at_utc)));if(c.page)p.append(el('small',' · Page '+c.page));sources.append(p);});card.append(sources);
 const actions=el('div',undefined,'actions');const download=el('button','Download answer evidence');download.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(packet,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='weathergpt-conversation-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});actions.append(download);card.append(actions);
 if(packet.expires_at_utc){const note=el('p','Evidence expires '+humanTime(packet.expires_at_utc)+'. Ask again before using an old answer.','hint');card.append(note);setTimeout(()=>{top.querySelector('.status').textContent='Expired · ask again';note.textContent='This earlier answer has expired. Ask again to retrieve current evidence.';},Math.max(0,Date.parse(packet.expires_at_utc)-Date.now()));}
 const trace=el('details',undefined,'receipt');trace.append(el('summary','Inspect interpretation and retrieval'),el('pre',JSON.stringify(packet,null,2)));card.append(trace);
 return card;
}

$('compare-example').addEventListener('click',()=>{const question='Compare annual rainfall in Ahmedabad district, Gujarat in 2009 and 2010.';$('question').value=question;send({question});});
$('trend-example').addEventListener('click',()=>{const question='Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.';$('question').value=question;send({question});});

$('probability-example').addEventListener('click',()=>{$('question').value='What is the chance of rain in Ahmedabad, Gujarat tomorrow morning?';send({question:$('question').value});});
$('daily-example').addEventListener('click',()=>{$('question').value='Show daily rainfall in Ahmedabad city, Gujarat from 1 July through 7 July 2025, including the total.';send({question:$('question').value});});
