'use strict';
// Plotting uses Number only for pixel coordinates; source values remain exact text.
function historicalChart(chart) {
 const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const box=make('section');box.className='history-chart';box.append(make('h3',chart.title));
 const axis=p=>p.x===undefined?p.year:p.x;
 const label=p=>p.label===undefined?String(p.year):p.label;
 const good=chart.points.filter(p=>p.value!==null && Number.isFinite(Number(p.value)));
 const receipt=make('p','Select a point to inspect its exact source value. Missing intervals remain gaps.');receipt.setAttribute('aria-live','polite');
 if(good.length){
  const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 640 270');svg.setAttribute('role','group');svg.setAttribute('aria-label',chart.title+' in '+chart.unit);
  const node=(name,attrs,text)=>{const n=document.createElementNS(ns,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;svg.append(n);return n;};
  const first=Math.min(...chart.points.map(axis)),last=Math.max(...chart.points.map(axis));
  let low=Math.min(...good.map(p=>Number(p.value))),high=Math.max(...good.map(p=>Number(p.value)));
  if(chart.unit==='mm')low=Math.min(0,low);if(high===low){low-=1;high+=1;}
  const x=y=>62+(y-first)/Math.max(1,last-first)*550,y=v=>215-(Number(v)-low)/(high-low)*180;
  [0,.5,1].forEach(f=>{const v=low+(high-low)*f;node('line',{x1:62,x2:612,y1:y(v),y2:y(v),'class':'chart-grid'});node('text',{x:54,y:y(v)+4,'text-anchor':'end'},v.toFixed(1));});
  node('text',{x:62,y:245},label(chart.points[0]));node('text',{x:612,y:245,'text-anchor':'end'},label(chart.points[chart.points.length-1]));node('text',{x:62,y:22},chart.unit);
  let segment=[];const flush=()=>{if(segment.length>1)node('polyline',{points:segment.join(' '),fill:'none','class':'chart-series'});segment=[];};
  chart.points.forEach(p=>{if(p.value===null){flush();return;}segment.push(x(axis(p))+','+y(p.value));});flush();
  good.forEach(p=>{
   const text=label(p)+': '+p.value+' '+chart.unit+' · '+p.evidence_id;
   const dot=node('circle',{cx:x(axis(p)),cy:y(p.value),r:4.5,tabindex:0,role:'button','aria-label':text,'class':'chart-point'});
   const title=document.createElementNS(ns,'title');title.textContent=text;dot.append(title);
   const select=()=>{receipt.textContent=text;};dot.addEventListener('click',select);dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});
  });box.append(svg,receipt);
 }
 const detail=make('details');detail.append(make('summary','View exact values and evidence IDs'));
 const table=make('table');const header=make('tr');[chart.axis_label||'Year','Value ('+chart.unit+')','Evidence'].forEach(t=>{const th=make('th',t);th.scope='col';header.append(th);});table.append(header);
 chart.points.forEach(p=>{const row=make('tr');[label(p),p.value===null?'Missing':p.value,p.evidence_id||'No value'].forEach(v=>row.append(make('td',v)));table.append(row);});detail.append(table);box.append(detail);return box;
}
