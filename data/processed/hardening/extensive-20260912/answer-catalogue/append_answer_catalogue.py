import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
root=Path('/Users/heer/WeatherGPT');base=root/'data/processed/hardening/extensive-20260912';out=base/'answer-catalogue'
report=root/'docs/11-extensive-validation-and-rag-gate.md'
def read(path):return json.loads(path.read_text())
def quoted(value):return '\n'.join('> '+line for line in str(value).splitlines())
def label(key):return key.replace('_',' ').capitalize()
def rendered(value):return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
def rel(path):return '../'+str(path.relative_to(root))
def question_and_answer(title,question,answer,status,missing=None,source=None,selection=None):
 lines=['### '+title,'','**Question / test input:** '+rendered(question),'','**Recorded result:** `'+status+'`','',quoted(answer),'']
 if selection:lines+=['**Selection / test condition:** '+selection,'']
 if missing:lines+=['**Explicit missing information:** '+'; '.join(missing)+'.','']
 if source:lines+=['**Evidence:** '+source,'']
 return '\n'.join(lines)
workflow_path=base/'workflow-replay/answers.json';workflow=read(workflow_path)
contexts_path=base/'rag-replay/contexts.json';contexts=read(contexts_path)
current_path=base/'rag-replay/current-store-status.json';current=read(current_path)
live_path=root/'data/processed/hardening/answers-batch-four-20260912/live/answer.json';live=read(live_path)
capture_path=out/'automated-test-answers.json';captured=read(capture_path);summary=read(out/'capture-summary.json')
city_points={}
for p in (root/'data/processed/foundation/20260911T194849Z').glob('forecast-*.json'):
 sample=read(p);city_points[json.dumps(sample['coverage']['requested_point'],sort_keys=True)]=p.stem.removeprefix('forecast-').capitalize()
lines=['<!-- TEST_ANSWER_CATALOGUE_START -->','## Complete sample questions and recorded answers','',
 f'This catalogue includes **{len(workflow)} saved workflow answers**, **one earlier live-check answer**, **{len(contexts)+1} RAG responses**, and **{len(captured)} responses captured from the automated question tests**: **{len(workflow)+1+len(contexts)+1+len(captured)} recorded responses in total**. Repeated questions are retained because selection, evidence, time or failure conditions differ. Answers below are reproduced from the saved output fields, including unsuccessful and partial results.','',
 'The original audit checkpoint remains unchanged. This report was extended afterward at the user’s request. The original report is preserved in the [frozen implementation snapshot](../data/processed/hardening/extensive-20260912/implementation/docs/11-extensive-validation-and-rag-gate.md); the [answer-catalogue addendum manifest](../data/processed/hardening/extensive-20260912/answer-catalogue/addendum-manifest.json) records the extended report and its inputs.','',
 '**How to read the examples:** historical replay uses genuine saved provider values at a simulated receipt clock; the earlier live check uses its dated real receipt; automated test fixtures use deliberately constructed values. None of these examples is a continuing current-weather claim. The 63,072 arithmetic comparisons are numerical oracle checks and did not produce natural-language question/answer pairs.','',
 '- [Saved forecast workflow answers](#saved-forecast-workflow-answers)','- [Earlier live Ahmedabad answer](#earlier-live-ahmedabad-answer)','- [Recorded RAG responses](#recorded-rag-responses)','- [Automated question-test responses](#automated-question-test-responses)','',
 '## Saved forecast workflow answers','',
 'All 16 answers below come from the [complete workflow payloads]('+rel(workflow_path)+'). The replay clock was **11 September 2026, 20:00 UTC**, so “today” resolves to **12 September in India**. Receipt timestamps in these replay answers are simulated. The complete JSON retains original questions, place selection, values, units, validity, freshness, source URL/hash/locators and missing information.','']
for n,(key,a) in enumerate(workflow.items(),1):
 title=label(key);selection=None
 location=a.get('location') or {};point=location.get('requested_point')
 if key.startswith('national_land_sample') and point:
  title=city_points.get(json.dumps(point,sort_keys=True),'National sample')+' — selected coordinate sample'
  selection=f"Explicit latitude {point['latitude']}, longitude {point['longitude']}; this is a model point sample, not a citywide average."
 elif location.get('status')=='selected_point':selection='The source place point was explicitly selected after resolving source candidates.'
 source='[Complete recorded response]('+rel(workflow_path)+'), entry `'+key+'`.'
 citations=a.get('citations') or []
 if citations:
  c=citations[0];source+=' ['+c['provider']+' source request]('+c['url']+'); response SHA-256 `'+c['response_sha256']+'`.'
 lines.append(question_and_answer(f'S{n:02d}. '+title,a['question'],a['answer'],a['status'],a.get('missing_information'),source,selection))
lines+=['## Earlier live Ahmedabad answer','',
 'This answer was produced by the earlier bounded live request, not by a new request for this report update. The forecast response was retrieved **12 September 2026 at 07:38:40 UTC**; the serving freshness limit ended **08:38:40 UTC that day**.','',
 question_and_answer('L01. Ahmedabad — real dated source receipt',live['question'],live['answer'],live['status'],live['missing_information'],'[Original full live answer]('+rel(live_path)+').')]
lines+=['## Recorded RAG responses','',
 'These are the actual context gate’s deterministic responses, not language-model-generated answers. The first five use the historical replay; the sixth reuses the earlier live receipt. An abstention supplies no eligible numeric evidence to the RAG client.','']
for n,(key,p) in enumerate(contexts.items(),1):
 lines.append(question_and_answer(f'R{n:02d}. '+label(key),p['user_question'],p['deterministic_answer'],p['status'],p['missing_information'],'[Recorded RAG context]('+rel(contexts_path)+'), entry `'+key+'`.'))
lines.append(question_and_answer('R06. Stored live Ahmedabad receipt admitted during the recorded check',current['user_question'],current['deterministic_answer'],current['status'],current['missing_information'],'[Full recorded context]('+rel(current_path)+'). Context expiry: **'+current['expires_at_utc']+'**.'))
lines+=['## Automated question-test responses','',
 f'For this report extension, all **{summary["tests_run"]} tests passed again** and the actual answer-service return values were captured: **{summary["answer_responses_captured"]} responses from {summary["tests_producing_answers"]} test methods**. The remaining tests check parsers, calculations, storage, geography, documents or other contracts without returning a natural-language answer. They remain listed in the [complete test log]('+rel(out/'capture-tests.txt')+').','',
 '**All values in this section are synthetic test fixtures.** For example, the repeated 3.0 mm result and 1.0 °C sample values are constructed test inputs, not actual Ahmedabad forecasts. Temporary file paths and technical error messages are preserved where they appeared in the actual returned answer.','',
 '[Full captured questions, selections and response payloads]('+rel(capture_path)+') · [Capture summary]('+rel(out/'capture-summary.json')+').','']
for item in captured:
 a=item['response'];test=item['test'].split('.')[-1].removeprefix('test_').replace('_',' ');selection=item['selection']
 condition='Test `'+item['test']+'`.'
 if selection:condition+=' Explicit call options: `'+json.dumps(selection,ensure_ascii=False,sort_keys=True)+'`.'
 lines.append(question_and_answer(f'T{item["case_number"]:03d}. '+test.capitalize(),a['question'],a['answer'],a['status'],a.get('missing_information'),None,condition))
lines+=['<!-- TEST_ANSWER_CATALOGUE_END -->','']
block='\n'.join(lines)
text=report.read_text()
start='<!-- TEST_ANSWER_CATALOGUE_START -->'
if start in text:text=text[:text.index(start)].rstrip()+'\n'
# Put a discoverable link near the report's opening decision.
nav='[Read every sample question and recorded answer](#complete-sample-questions-and-recorded-answers).\n\n'
anchor='## Measured results\n'
if nav not in text:text=text.replace(anchor,nav+anchor,1)
report.write_text(text.rstrip()+'\n\n'+block)
inputs=[workflow_path,contexts_path,current_path,live_path,capture_path,out/'capture-summary.json',out/'capture-tests.txt']
manifest={'schema_version':'answer-catalogue-addendum-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'report':str(report.relative_to(root)),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),'inputs':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'counts':{'saved_workflow_answers':len(workflow),'earlier_live_answer':1,'rag_responses':len(contexts)+1,'automated_test_answer_responses':len(captured),'total_recorded_responses':len(workflow)+1+len(contexts)+1+len(captured)},'tests_rerun':summary,'scope':'Actual recorded answer strings appended verbatim. Original frozen checkpoint preserved. No new weather retrieval or LLM call.'}
(out/'addendum-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Verify every output string occurs as a complete quoted passage, not just a paraphrase.
answers=[a['answer'] for a in workflow.values()]+[live['answer']]+[p['deterministic_answer'] for p in contexts.values()]+[current['deterministic_answer']]+[r['response']['answer'] for r in captured]
final=report.read_text()
assert all(quoted(a) in final for a in answers)
assert final.count('### S')==len(workflow) and final.count('### T')==len(captured)
print(json.dumps({'report':str(report),'responses_verified':len(answers),'bytes':report.stat().st_size,'tests_passed':summary['tests_passed']}))
