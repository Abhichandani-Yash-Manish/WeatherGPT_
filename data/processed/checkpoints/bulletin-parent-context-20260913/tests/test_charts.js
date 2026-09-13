// Pure component test, not a browser or visual verification.
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.events={};this.textContent='';}
 append(...children){this.children.push(...children);}
 setAttribute(key,value){this.attrs[key]=String(value);}
 addEventListener(event,fn){this.events[event]=fn;}
 all(tag){return [...(this.tag===tag?[this]:[]),...this.children.flatMap(n=>n.all(tag))];}
}
const context={document:{createElement:t=>new Node(t),createElementNS:(_,t)=>new Node(t)}};vm.createContext(context);vm.runInContext(fs.readFileSync('web/charts.js','utf8'),context);
const chart=context.historicalChart({title:'Source rainfall',unit:'mm',points:[{year:2000,value:'0.123456',evidence_id:'f1'},{year:2001,value:'2',evidence_id:'f2'},{year:2002,value:null},{year:2003,value:'4',evidence_id:'f3'},{year:2004,value:'5',evidence_id:'f4'}]});
assert.equal(chart.all('polyline').length,2,'Missing year must split the drawn line');
assert(chart.all('td').some(n=>n.textContent==='0.123456'),'Exact source precision must survive in the table');
const dot=chart.all('circle')[0];dot.events.keydown({key:'Enter',preventDefault(){}});assert(chart.all('p').some(n=>n.textContent==='2000: 0.123456 mm · f1'),'Keyboard inspection must identify exact value and evidence');
console.log('PASS: missing-year plot gaps, exact source precision, keyboard point inspection (component only)');
const hourly=context.historicalChart({title:'Hourly probability',axis_label:'Time (IST)',unit:'%',points:[{x:100,label:'13 Sep 06:30–07:30',value:'20',evidence_id:'t1-f1'},{x:3700,label:'13 Sep 07:30–08:30',value:'80',evidence_id:'t1-f2'}]});
assert(hourly.all('th').some(n=>n.textContent==='Time (IST)'));
assert(hourly.all('td').some(n=>n.textContent==='13 Sep 06:30–07:30'));
assert(hourly.all('circle').every(n=>Number.isFinite(Number(n.attrs.cx))));
hourly.all('circle')[1].events.click();assert(hourly.all('p').some(n=>n.textContent==='13 Sep 07:30–08:30: 80 % · t1-f2'));
console.log('PASS: hourly axes, exact IST interval labels and evidence inspection (component only)');
