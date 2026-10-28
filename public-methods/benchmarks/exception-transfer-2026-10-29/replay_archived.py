#!/usr/bin/env python3
"""Recompute archived exact-content/file scores and actual token receipt totals offline."""
import pathlib,json,collections
R=pathlib.Path(__file__).resolve().parent
gold={x['id']:x['decisions'] for x in json.loads((R/'protocol/gold.json').read_text())['tasks']}
expected={x['id']:x for x in json.loads((R/'measurements.json').read_text())}
def load(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return None
summary=collections.defaultdict(lambda:collections.Counter())
for ident,row in expected.items():
 d=R/'artifacts'/ident;file=load(d/'answer.json');final=load(d/'final.txt');a=file if file is not None else final
 dec=a.get('decisions',{}) if isinstance(a,dict) else {};points=sum(type(dec.get(k)) is type(v) and dec.get(k)==v for k,v in gold[row['task']].items())
 assert points==row['content_points'],(ident,'content points')
 strict=points if file is not None else 0;assert strict==row['strict_artifact_points'],(ident,'artifact points')
 receipts=[json.loads(x) for x in (d/'model-receipts.jsonl').read_text().splitlines()]
 usage={k:sum(x.get('usage',{}).get(k,0) for x in receipts) for k in ['input_tokens','output_tokens']};usage['cached_input_tokens']=sum(x.get('usage',{}).get('input_tokens_details',{}).get('cached_tokens',0) for x in receipts)
 for k,v in usage.items():assert v==row[k],(ident,k)
 trace=[json.loads(x) for x in (d/'trace-public.jsonl').read_text().splitlines()];cli=[x['usage'] for x in trace if x['type']=='turn.completed'][-1];assert all(cli.get(k)==v for k,v in usage.items()),ident
 total=summary[row['arm']];total.update({'content_points':points,'strict_file_points':strict,'runs':1,'total_tokens':usage['input_tokens']+usage['output_tokens']})
print(json.dumps({'verified_runs':len(expected),'arms':dict(summary)},indent=2))