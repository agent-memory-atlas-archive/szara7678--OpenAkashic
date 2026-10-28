import json,hashlib,datetime
from pathlib import Path
p=Path(__file__).resolve().parent
protocol=json.loads((p/'protocol-v2.json').read_text())
key={x['blind_id']:x for x in json.loads((p/'blind-key.json').read_text())}
grades=json.loads((p/'blind-grades.json').read_text())
assert len(grades)==18
if isinstance(grades,dict):raise ValueError('Expected grade list')
assert {g['blind_id'] for g in grades}==set(key)
mechanical=json.loads((p/'mechanical-checks.json').read_text())['checks']
metrics=json.loads((p/'input-material-metrics.json').read_text())
by={c:[] for c in protocol['conditions']}
for g in grades:
 k=key[g['blind_id']]; row=dict(g,task_id=k['task_id']); by[k['condition']].append(row)
summary={}
for c,rows in by.items():
 summary[c]={'criterion_passes_model_reviewed':sum(r['objective_total'] for r in rows),'criterion_possible':24,'judgment_total':sum(r['method_fit']+r['actionability']+r['evidence_boundaries'] for r in rows),'judgment_possible':36,'word_limit_passes':sum(r['word_limit_pass'] for r in mechanical if r['condition']==c),'outputs':6,'constraint_violations':[{'task_id':r['task_id'],'items':r['constraint_violations']} for r in rows if r['constraint_violations']],'unsupported_claims':[{'task_id':r['task_id'],'items':r['unsupported_claims']} for r in rows if r['unsupported_claims']]}
flat=metrics['metrics']['flat_same_records-input.json'];compact=metrics['metrics']['compact_same_records-input.json']
report={'schema':'atlas-bounded-application-evaluation-v1','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'complete','protocol_sha256':hashlib.sha256((p/'protocol-v2.json').read_bytes()).hexdigest(),'design':{'tasks':6,'outputs':18,'generation_model':'gpt-6-luna','review_model':'gpt-6-sol','replicates_per_task_condition':1,'blind_review':'condition labels hidden; task-wise shuffled answer IDs; answer content can reveal source availability','baseline':'same complete public records as flat leaf-path JSON vs nested compact JSON; unaided third arm','task_selection':'synthetic corpus-aligned, manually chosen records before generation; T2 adjacent product-experiment evidence only','initial_fixture_error':'Korean stdin corrupted before generation; ASCII v2 frozen and used for all arms; initial artifacts retained as rejected audit inputs'},'summary':summary,'material':{'input_estimates':metrics['metrics'],'compact_vs_flat_token_estimate_reduction':1-compact['tokens_o200k_base']/flat['tokens_o200k_base'],'actual_provider_usage':None,'actual_cost':None,'timing_comparison':None,'interpretation':'Artifact token estimates only, not billed/provider tokens or costs.'},'by_condition':by,'measured':{'mechanical':'answer count, frozen hashes, same-record leaf equality, whitespace word limit, input material token estimate','semantic_model_assessment':'objective rubric criteria and all subjective quality scores are model assessed; not executed task results'},'limitations':['Six English synthetic tasks and Korean public records; no randomized human users, repetitions or significance test.','Manual record selection excludes retrieval errors and does not test network visualization or UI exporter.','Single condition agent generates all six tasks; sequential context/task carryover may affect answers.','One blind model judge; rubric ceiling and scoring bias possible. Objective semantic checks remain judgments, not external verification.','No real incident recovery, interviews, learning retention, registration, OSS contribution or real-world outcome measured.','Compact format is lossless nesting, not a validated task-specific reasoning system.','No claims about the public contributor outcomes being independently verified.','Actual provider token usage, reasoning tokens, cache, latency and billing unavailable.']}
report.update(json.loads((p/'report-additions.json').read_text()))
(p/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
