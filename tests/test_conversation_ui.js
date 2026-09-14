// Component-level conversation-control checks; this is not a browser acceptance test.
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
 constructor(tag,text){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.events={};this.focused=false;}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 addEventListener(event,fn){this.events[event]=fn;}
 focus(){this.focused=true;}
}
const source=fs.readFileSync('web/app.js','utf8');
const controls=source.slice(source.indexOf("$('history-example')"),source.indexOf('function renderConversation('));
const nodes={},sent=[];
const context={$:id=>nodes[id]||(nodes[id]=new Node(id)),el:(tag,text)=>new Node(tag,text),send:body=>sent.push(body)};
vm.createContext(context);vm.runInContext(controls,context);

context.$('question').value='half typed question';
context.$('new-conversation').events.click();
assert.equal(sent.length,0,'Starting a new conversation must not submit the cleared question box');
assert.equal(context.$('question').value,'');
assert.equal(context.$('thread').children.length,1,'The thread is replaced by a single welcome card');
assert(context.$('question').focused,'The cleared input keeps focus for the next question');
console.log('PASS: new conversation resets the thread without sending an empty question (component only)');

context.$('history-example').events.click();
assert.equal(sent.length,1);
assert(sent[0].question.includes('Ahmedabad'),'An example control still submits its own written question');
console.log('PASS: example controls still submit a real question (component only)');
