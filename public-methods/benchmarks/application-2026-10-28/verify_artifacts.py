import json, hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
rows=[]
for condition in ['unaided','flat_same_records','compact_same_records']:
 f=p/(condition+'-output.json')
 if not f.exists():continue
 answers=json.loads(f.read_text())
 assert len(answers)==6 and {a['task_id'] for a in answers}=={'T1','T2','T3','T4','T5','T6'}
 for a in answers:
  words=len(a['answer'].split())
  rows.append({'condition':condition,'task_id':a['task_id'],'whitespace_words':words,'word_limit_pass':words<=220})
(p/'mechanical-checks.json').write_text(json.dumps({'checks':rows,'counting':'whitespace words; numbers and hyphenated tokens count as one; no semantic quality inference'},indent=2))
print(json.dumps(rows,indent=2))
