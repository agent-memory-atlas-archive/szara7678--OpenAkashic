from pathlib import Path
import json,hashlib,datetime,collections
p=Path(__file__).resolve().parent
r=json.loads((p/'candidate-results.json').read_text());f=json.loads((p/'freeze.json').read_text());summary={}
for arm in ['method_only','raw_experience','linked_experience']:
 rows=[x for x in r['runs'] if x['arm']==arm]
 by={family:{'passed':sum(x['passed'] for x in rows if x['family']==family),'cases':6} for family in ['backup','join','search']}
 inp=(p/'generation'/arm/'input.json').read_text();tokens=None
 try:
  import tiktoken
  tokens=len(tiktoken.get_encoding('o200k_base').encode(inp))
 except ImportError:pass
 summary[arm]={'programs_fully_passed':sum(x['passed']==6 for x in by.values()),'programs':3,'passed_cases':sum(x['passed'] for x in rows),'cases':18,'families':by,'input_characters':len(inp),'input_utf8_bytes':len(inp.encode()),'input_material_o200k_tokens':tokens,'actual_usage':None,'actual_cost':None,'failures':[{'family':x['family'],'fixture':x['fixture'],'result':x['result']} for x in rows if not x['passed']]}
report={'schema':'openakashic-failure-transfer-result-v1','measured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':hashlib.sha256((p/'protocol.json').read_bytes()).hexdigest(),'freeze_sha256':hashlib.sha256((p/'freeze.json').read_bytes()).hexdigest(),'frozen_at':f['frozen_at'],'design':json.loads((p/'protocol.json').read_text()),'summary':summary,'comparison':'Manually selected existing public method versus added real stored synthetic-example reports versus exact same reports regrouped by outcome_id. No independent retrieval comparison.','limits':['Three selected families, one implementation per arm and family. Six fixtures per program are clustered checks, not independent generations.','All arms already receive complete task contracts and baseline method caveats; ceiling effects possible.','Prior join case is successful risk detection, not an observed failed join. Backups expose FK inconsistency; search prior cases include actual misses.','No private or real customer data; examples are synthetic. No measured user benefit, reviewer time, actual billing or statistical superiority.','One agent generates three programs within each arm; within-arm context carryover possible. Requested model label is not independently verified backend identity.','Exact same experience objects and no additional claims in linked arm. This is packaging, not graph reasoning.']}
(p/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({arm:{k:v for k,v in x.items() if k not in ['failures','families']} for arm,x in summary.items()}))
