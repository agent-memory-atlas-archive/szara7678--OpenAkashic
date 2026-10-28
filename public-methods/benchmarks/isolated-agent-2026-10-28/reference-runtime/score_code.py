import sys,json,pathlib,subprocess,time,tempfile,hashlib,importlib.util
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verifier',ROOT/'protocol/verify_tasks.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
IMAGE='python@sha256:5789aa194f757888f41fa3d48e14b6feaa1b57c0af0b56fcb1372d6474d3bff0'
fixtures=json.loads((ROOT/'protocol/fixtures.json').read_text())['cases']
def execute(ident,payload):
 file=ROOT/'execution'/ident/'workspace/solution.py'
 if not file.is_file():return {'ok':False,'reason':'missing_artifact'}
 cmd=['docker','run','--rm','-i','--network','none','--read-only','--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32','--memory','128m','--cpus','1','--tmpfs','/tmp:rw,nosuid,size=16m,mode=1777','-v',str(file)+':/candidate.py:ro',IMAGE,'python','-I','-B','/candidate.py']
 with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=out,stderr=err)
  try:p.communicate(json.dumps(payload,ensure_ascii=False).encode(),timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.communicate();return {'ok':False,'reason':'timeout'}
  out.seek(0);err.seek(0);b=out.read(65537);e=err.read(65537)
  if p.returncode:return {'ok':False,'reason':'nonzero_exit'}
  if len(b)>65536 or len(e)>65536:return {'ok':False,'reason':'stream_limit'}
  try:return {'ok':True,'value':json.loads(b,object_pairs_hook=v.unique_object,parse_constant=v.reject_constant)}
  except (ValueError,UnicodeDecodeError):return {'ok':False,'reason':'invalid_json'}
def main():
 report=[]
 for arm in ['base','akashic','required']:
  for number,task in [(1,'C1'),(2,'C2')]:
   ident=f'{arm}-{number}-'+('r1' if arm=='required' else 'r2');checks=[];t=time.monotonic()
   for case in [c for c in fixtures if c['task_id']==task]:
    for mode in ['literal','reverse_input']:
     payload=json.loads(json.dumps(case['input']))
     if mode=='reverse_input':payload['events' if task=='C1' else 'records'].reverse()
     r=execute(ident,payload);ok=r['ok'] and v.equal_json(r.get('value'),case['expected'])
     checks.append({'case':case['id'],'visibility':case['visibility'],'mode':mode,'passed':bool(ok),'points':int(ok) if case['weight'] else 0,'reason':'match' if ok else ('wrong_result' if r['ok'] else r['reason'])})
   item={'id':ident,'task':task,'points':sum(c['points'] for c in checks),'max_points':12,'checks':checks,'grading_seconds':time.monotonic()-t};report.append(item);print(json.dumps({k:item[k] for k in ['id','points','grading_seconds']}),flush=True)
 out=ROOT/'results';out.mkdir(exist_ok=True);(out/'coding.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()