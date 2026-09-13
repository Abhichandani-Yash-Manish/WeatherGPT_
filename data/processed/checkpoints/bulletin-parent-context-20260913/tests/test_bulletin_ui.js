// Component-level citation checks; this is not a browser/visual acceptance test.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {constructor(tag,text){this.tag=tag;this.textContent=text;this.children=[];}append(...nodes){this.children.push(...nodes);}addEventListener(){} all(tag){return [...(this.tag===tag?[this]:[]),...this.children.flatMap(n=>n.all(tag))];}}
const source=fs.readFileSync('web/app.js','utf8');const functionText=source.slice(source.indexOf('function renderConversation('),source.indexOf("$('compare-example')"));
const context={el:(tag,text)=>new Node(tag,text),URL,humanTime:x=>x};vm.createContext(context);vm.runInContext(functionText,context);
const packet={status:'answered',answer:'Published passage',choices:[],facts:[],notes:[],passages:[{id:'p1',crop:'Rice',stage:'Tillering',district:'Kamrup',page:2,issue_date:'2026-09-11',forecast_start:'2026-09-12',forecast_end:'2026-09-16',text:'<script>untrusted source text</script>',citation_ids:['t1-doc']}],citations:[{id:'other',url:'https://example.com/unrelated'},{id:'t1-doc',url:'https://imdagrimet.gov.in/Services/DistrictBulletin.php?district=Kamrup'}]};
const result=context.renderConversation(packet,{});const page=result.all('a').find(a=>a.textContent==='Open the original bulletin page');assert(page.href.includes('district=Kamrup#page=2'));assert.equal(page.rel,'noopener noreferrer');assert(result.all('p').some(p=>p.textContent==='<script>untrusted source text</script>'));
packet.citations[1].url='javascript:alert(1)';const held=context.renderConversation(packet,{});assert(!held.all('a').some(a=>a.textContent==='Open the original bulletin page'));
console.log('PASS: passage uses its bound citation, page locator, literal source text and HTTPS-only link (component only)');
packet.citations[1].url='https://imdagrimet.gov.in/current.pdf';packet.citations[1].local_document_path='/api/documents/'+'a'.repeat(64);const saved=context.renderConversation(packet,{});assert(saved.all('a').some(a=>a.textContent==='Open the saved source PDF'&&a.href==='/api/documents/'+'a'.repeat(64)+'#page=2'));
console.log('PASS: immutable stored PDF page is preferred to a changing publisher URL');
packet.passages[0].evidence_kind='published_bulletin_context';packet.passages[0].section='Weather Warning';packet.passages[0].crop='';packet.passages[0].stage='';
const parent=context.renderConversation(packet,{});assert(parent.all('summary').some(s=>s.textContent.startsWith('Bulletin context: Weather Warning')));assert(parent.all('p').some(p=>p.textContent.includes('current warning and individual field applicability remain unverified')));
console.log('PASS: parent context is labelled separately from crop evidence and current alerts');

assert(parent.all('a').some(a=>a.textContent==='Download saved PDF'&&a.href===packet.citations[1].local_document_path&&a.download==='bulletin-'+'a'.repeat(64)+'.pdf'));
console.log('PASS: saved PDF has a same-origin download fallback');
