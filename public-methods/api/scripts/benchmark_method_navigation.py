"""Public record lookup workload. Measures transport material, not reasoning or human utility."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler
from app.research_method_context import counted
from app.research_store import digest


def run(endpoint):
    opener = build_opener(ProxyHandler({}))
    def get(path):
        started = time.perf_counter()
        with opener.open(Request(endpoint.rstrip('/')+'/research/api/methods'+path, headers={'User-Agent':'OpenAkashic-Verification/0.3 (+https://github.com/szara7678/OpenAkashic)','Accept':'application/json'}), timeout=30) as response:
            data = json.load(response)
        return data, round(time.perf_counter()-started, 6)
    catalog, _ = get('/catalog?limit=24');items=list(catalog['items'])
    while catalog['has_more']:
        catalog,_=get('/catalog?'+urlencode({'limit':24,'offset':len(items)}));items.extend(catalog['items'])
    methods = [get('/'+x['id'])[0] for x in items]
    sources = defaultdict(list)
    for m in methods:
        for s in m.get('sources',[]):
            sources[s['url']].append({'id':m['id'],'version':m['version'],'title':m['title']})
    flat_index = dict(sorted(sources.items()))
    source_cases = [{'source_url':url,'expected_refs':sorted({(m['id'],m['version']) for m in refs})} for url,refs in flat_index.items() if len(refs)>1]
    feedback_cases = [{'id':m['id'],'version':m['version'],'expected_outcomes':sorted(x['id'] for x in m.get('outcomes',[])), 'expected_opinions':sorted(x['id'] for x in m.get('opinions',[]))} for m in methods if m.get('outcomes') or m.get('opinions')]
    cases = {'sources':source_cases,'feedback':feedback_cases}
    frozen_hash=hashlib.sha256(json.dumps(cases,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    records=[]
    for c in source_cases:
        focus='source_'+digest(c['source_url'])[:24]
        data,elapsed=get('/network?'+urlencode({'focus':focus,'depth':1,'limit':100}))
        if data['scope']['truncated'] or data['scope']['focus_missing']:
            raise RuntimeError('Incomplete graph cannot be counted as complete navigation')
        returned=sorted((n['method_id'],n['version']) for n in data['nodes'] if n['kind']=='method')
        records.append({'kind':'shared_source','source_url':c['source_url'],'focus':focus,'expected_refs':c['expected_refs'],'returned_refs':returned,'success':returned==c['expected_refs'], 'graph_tokens':counted(data),'flat_index_lookup_tokens':counted({'url':c['source_url'],'methods':flat_index[c['source_url']]}),'elapsed_seconds':elapsed})
    for c in feedback_cases:
        data,elapsed=get('/'+c['id']+'/graph');m=next(m for m in methods if m['id']==c['id'])
        returned_outcomes=sorted(n['id'] for n in data['nodes'] if n['kind']=='outcome');returned_opinions=sorted(n['id'] for n in data['nodes'] if n['kind']=='opinion')
        exact=all(n['method_version']==c['version'] for n in data['nodes'] if n['kind'] in ('outcome','opinion'))
        trimmed={'method_id':m['id'],'version':m['version'],'outcomes':m.get('outcomes',[]),'opinions':m.get('opinions',[]),'sources':m.get('sources',[])}
        records.append({'kind':'feedback','method_id':c['id'],'expected_outcomes':c['expected_outcomes'],'returned_outcomes':returned_outcomes,'expected_opinions':c['expected_opinions'],'returned_opinions':returned_opinions,'success':returned_outcomes==c['expected_outcomes'] and returned_opinions==c['expected_opinions'] and exact and not any(data['truncated'].values()),'graph_tokens':counted(data),'direct_method_tokens':counted(m),'flat_projection_tokens':counted(trimmed),'elapsed_seconds':elapsed})
    shared=[x for x in records if x['kind']=='shared_source'];feedback=[x for x in records if x['kind']=='feedback']
    return {'schema':'method-navigation-workload-v1','measured_at':datetime.now(timezone.utc).isoformat(),'method_count':len(methods),'case_definition_sha256':frozen_hash,'cases':cases,'records':records,
      'summary':{'source_tasks':len(shared),'source_success':sum(x['success'] for x in shared),'feedback_tasks':len(feedback),'feedback_success':sum(x['success'] for x in feedback),'shared_graph_tokens':sum(x['graph_tokens'] for x in shared),'flat_index_once_tokens':counted(flat_index),'flat_lookup_tokens':sum(x['flat_index_lookup_tokens'] for x in shared),'all_full_records_once_tokens':counted(methods),'feedback_graph_tokens':sum(x['graph_tokens'] for x in feedback),'feedback_direct_tokens':sum(x['direct_method_tokens'] for x in feedback),'feedback_flat_projection_tokens':sum(x['flat_projection_tokens'] for x in feedback),'median_graph_seconds':statistics.median(x['elapsed_seconds'] for x in records) if records else None},
      'limits':['Exhaustive tasks generated from this stored corpus, not independent natural-language questions.','Deterministic URL and record ID lookup; no model generated or graded answers.','The flat URL index uses the exact same stored references and is a strong baseline. It can be reused.','Counts are o200k JSON transport material, not billed usage or latency of model reasoning.','Graph versus direct record material includes different structural fields; no claim of equal answer quality.','Human navigation speed, novel task output quality and independent OSS adoption remain unmeasured.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--endpoint',default='http://127.0.0.1:18082');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit('Refusing to overwrite an existing result')
    result=run(a.endpoint);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['summary'],ensure_ascii=False))
