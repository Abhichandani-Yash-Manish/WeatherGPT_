"""Generate source utilization and actionable audit records without changing source readiness."""
import csv,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
reg=json.loads((ROOT/'data/registry/sources.json').read_text())
chat={'S21','S25','S26','S27','S61'}
numeric={'S18','S19','S20','S22','S24','S37','S56'}
reference={'S06','S15','S57','S58','S59'}
rows=[]
for p in reg['products']:
 sid=p['id']
 if sid in chat:route='connected_to_chat_scoped';next_step='Repair fidelity and expand supported operations; preserve source scope.'
 elif sid in numeric:route='adapter_exists_not_connected_to_chat';next_step='Add typed product tool, identity/time validation and end-to-end acceptance cases.'
 elif sid in reference:route='reference_adapter_exists_not_connected_to_chat';next_step='Review issue/expiry/geographic/content semantics before context retrieval or dissemination.'
 elif p['processing_state']=='deferred':route='deliberately_deferred';next_step='Retain rationale; reactivate only for a demonstrated PS need.'
 elif p['evidence_level']=='sample_inspected' and p['record_kind'] not in {'gap','documentation'}:route='sample_or_reference_only';next_step='Inspect actual product contract and value beyond existing upstreams before building.'
 else:route='catalogue_lead_gap_or_blocked';next_step='Resolve access or specific missing contract; do not count as answer-ready data.'
 rows.append({'source_id':sid,'product':p['product'],'record_kind':p['record_kind'],'category':p['category'],'evidence_level':p['evidence_level'],'processing_state':p['processing_state'],'conversational_use':route,'next_step':next_step})
with (OUT/'source-utilization.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
from collections import Counter
(OUT/'source-utilization.json').write_text(json.dumps({'as_of_utc':datetime.now(timezone.utc).isoformat(),'registry_entries':len(rows),'counts':dict(Counter(r['conversational_use'] for r in rows)),'classification_basis':'Static inspection of conversation.py, research_answers.py, gazetteer.py and foundation adapters. Runtime reachability is not national completeness or scientific validation. Some registry entries are references/gaps, not independent datasets.','sources':rows},indent=2)+'\n')
items=[
('P01','high','reproduced_isolated','Values can be attributed to the wrong place while passing generation checks','weathergpt_data/conversation.py:195','isolated-probes.json','Bind each displayed claim to one typed evidence tuple: entity, parameter, interval, value, unit and source. Render factual clauses deterministically; reject changed attribution.',['R11','F01']),
('P02','high','reproduced_isolated','Historical reads do not verify the serving database against its build manifest','weathergpt_data/climate.py:103','isolated-probes.json','Verify publication manifests and serving artefacts for both national and district data; source-PDF hash alone does not authenticate transformed values.',['R10','R11','F11']),
('P03','high','reproduced_live_planner_and_lookup','Multi-year and multi-parameter requests lose required operations','weathergpt_data/language.py:16','planner-probes.json','Introduce typed task lists, date ranges, requested measures and operation enums; track coverage of every requested task.',['R11','F01','F08']),
('P04','high','static_and_live_planner','Specialist and daily-history adapters are unreachable from chat','weathergpt_data/conversation.py:78','source-utilization.json','Connect airport reports, marine, river and daily reanalysis through governed tools and explicit source entity types.',['R08','R09','R11','F06','F08']),
('P05','high','fresh_public_response','Four-variable forecast contract excludes available useful parameters','weathergpt_data/adapters.py:104','live-source-checks/summary.json','Add a separately identified extended forecast contract with units, nulls, model lineage, probability interval semantics and hourly timeline operations.',['R04','F05']),
('P06','high','static_and_fresh_feed_metadata','Warning ingest lacks complete applicable current alert lifecycle','weathergpt_data/foundation.py:147','live-source-checks/cap_rss.body','Resolve feed authority, coverage, update/cancel chains, validity and geometry; keep historical/replay labels; then subscription/outbox/delivery lifecycle.',['R02','R08']),
('P07','high','static','Documents are extracted pages without reviewed retrieval units','weathergpt_data/documents.py:6','source-utilization.json','Build document-family structured extraction, issue/validity/place/crop/stage filters, parent context, hybrid retrieval and citation verification.',['R09','F07']),
('P08','high','static','Place points do not support district/village area or specialist identity claims','weathergpt_data/gazetteer.py:51','source-utilization.json','Separate settlement/district/station/river/sea entities; dated administrative crosswalk, source footprints and resolvable choice/correction state.',['R01','R04','F03','F04']),
('P09','medium','static_and_live_planner','Historical lookup is not climate trend analysis','weathergpt_data/research_answers.py:10','planner-probes.json','Add range retrieval, comparisons, baselines, anomaly and descriptive trend tools with missingness and comparability checks.',['R10','F08']),
('P10','medium','static','Freshness scheduling is manual/request-driven and budget is narrow','data/registry/ingestion-policy.json','source-utilization.json','Prioritized prefetch for subscribed/active footprint plus demand retrieval; unified budgets for all tools; source-aware freshness, retention and restore rehearsal.',['R06','R07']),
('P11','medium','static','Local global locks reject concurrent questions; no cancellation or stage streaming','weathergpt_data/conversation.py:18','review-baseline.json','Bounded queue, per-conversation ownership, provider timeouts, cancellation and progress; measure warm/cold p50/p95 before choosing hosted inference.',['R06','R11']),
('P12','high','static','No user-level acceptance benchmark for all promised operations and languages','scripts/evaluate_conversation.py','tests.txt','Version a scenario set with requested tasks and expected evidence; score completion separately from correct refusal/clarification, and test semantic swaps and stale updates.',['R11','F10']),
('P13','medium','static','Voice and mobile requirements remain incomplete','web/index.html','review-baseline.json','Desktop-first now per user; later speech transcript confirmation, TTS and mobile acceptance. Sarvam trial is optional and must preserve place/date/negation/units.',['R11','F10']),
('P14','medium','static','Private runtime data is tracked and reproduction/deployment packaging is incomplete','requirements-foundation.txt','review-baseline.json','Separate curated fixtures from runtime conversations/logs; propose retention/deletion and repository hygiene, reproducible setup, CI and migrations before sharing. Do not erase evidence/history during this review.',['R06','R12']),
('P15','high','documentation_conflict','Early design documents overstate compliance and suggest unjustified derived risk scores','docs/01-idea-analysis-and-critique.md','review-baseline.json','Mark early hypotheses as superseded, keep PS wording authoritative, and require validated definitions before risk indices or operational claims.',['R12'])]
findings=[{'id':i,'priority':p,'evidence_type':t,'finding':f,'code_reference':c,'evidence':e,'proposed_repair':r,'prior_review_links':refs,'status':'open'} for i,p,t,f,c,e,r,refs in items]
(OUT/'findings.json').write_text(json.dumps({'schema_version':'product-potential-review-v1','as_of_utc':datetime.now(timezone.utc).isoformat(),'implementation_changed':False,'sharing_and_hosting':'on_hold_by_user','operational_ready':False,'findings':findings},indent=2)+'\n')
print(json.dumps(dict(Counter(r['conversational_use'] for r in rows))))
