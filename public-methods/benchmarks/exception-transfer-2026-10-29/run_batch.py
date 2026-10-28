import pathlib,json,sys,datetime,hashlib
R=pathlib.Path('/home/insu/akashic/runtime/public-research-v1/exception-transfer-20261029');sys.path.insert(0,str(R/'harness'))
from run_candidate import run
manifest=json.loads((R/'experiment-freeze.json').read_text())
for p,m in manifest['files'].items():
 assert hashlib.sha256((R/p).read_bytes()).hexdigest()==m['sha256'],p
for ident in json.loads((R/'execution/order.json').read_text()):
 d=R/'execution'/ident
 result=run(ident,(d/'frozen-prompt.txt').read_text(),300)
 receipts=[json.loads(x) for x in (d/'model-receipts.jsonl').read_text().splitlines()] if (d/'model-receipts.jsonl').exists() else []
 result['completed_model_calls']=sum(bool(x.get('completed')) for x in receipts)
 result['answer_exists']=(d/'workspace/answer.json').exists()
 with (R/'execution/batch-progress.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
 print(json.dumps(result),flush=True)
 if not receipts or any(x.get('status') in [401,403,429,503] for x in receipts):
  print('INFRASTRUCTURE_STOP',flush=True);break