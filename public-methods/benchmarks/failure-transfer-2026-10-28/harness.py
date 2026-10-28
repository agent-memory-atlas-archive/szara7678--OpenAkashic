"""Pre-generation frozen harness. Run selftest or evaluate MANIFEST.json. Never imports candidates on host."""
import pathlib,json,subprocess,tempfile,shutil,hashlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
IMAGE='sha256:5789aa194f757888f41fa3d48e14b6feaa1b57c0af0b56fcb1372d6474d3bff0'
def run(candidate,fixture,reference=False):
 with tempfile.TemporaryDirectory(prefix='sandbox-',dir=ROOT) as tmp:
  b=pathlib.Path(tmp);b.chmod(0o755);shutil.copyfile(candidate,b/'candidate.py');shutil.copyfile(ROOT/'runner.py',b/'runner.py');f={k:v for k,v in fixture.items() if k!='gold'};f['reference']=reference;(b/'input.json').write_text(json.dumps(f))
  for x in b.iterdir():x.chmod(0o444)
  cmd=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','128m','--cpus','1','--user','65534:65534','--tmpfs','/tmp:rw,noexec,nosuid,size=32m,mode=1777','--mount',f'type=bind,src={b},dst=/bundle,readonly',IMAGE,'python','-I','/bundle/runner.py']
  try:
   r=subprocess.run(cmd,text=True,capture_output=True,timeout=10,env={'PATH':'/usr/bin:/bin'})
   return json.loads(r.stdout) if r.returncode==0 else dict(error=r.stderr[:1000])
  except Exception as e:return dict(error=str(e))
def check(f,result):
 if result.get('returncode')!=0 or result.get('unchanged') is not True or result.get('input_unchanged') is not True:return False
 o=result['output'];g=dict(f['gold']) if f['family']=='backup' else f['gold']
 if f['family']=='backup' and g['status']=='created':
  if result.get('actual_byte') is None:return False
  g['byte_clone']=result['actual_byte']
  observed=result.get('backup_observed')
  if not observed or any(observed.get(k)!=g[k] for k in observed):return False
 if f['family']!='search':return o==g
 if not g:return o==[]
 if not isinstance(o,list) or len(o)!=1 or not isinstance(o[0],dict) or set(o[0])!={'id','quote','sha256'}:return False
 d=next(d for d in f['payload']['docs'] if d['id']==g[0]);v=o[0];return v['id']==g[0] and isinstance(v['quote'],str) and 0<len(v['quote'])<=256 and v['quote'] in d['body'] and v['sha256']==hashlib.sha256(d['body'].encode()).hexdigest()
def selftest():
 fs=json.load(open(ROOT/'fixtures.json'));runs=[]
 for f in fs:
  r=run(ROOT/'reference.py',f,True);passed=check(f,r);bad=dict(r)
  if f['family']=='search':bad['output']=[{'id':'invented','quote':'fabricated','sha256':'0'*64}]
  else:
   bad['output']=dict(r.get('output',{}));field='clone_success' if f['family']=='backup' else 'inner_rows';bad['output'][field]=not bad['output'].get(field) if field=='clone_success' else bad['output'].get(field,0)+1
  runs.append(dict(id=f['id'],reference_pass=passed,known_fault_rejected=not check(f,bad),details=None if passed else r))
 mutants=[]
 for label,fixture_id,source in [
  ('fake_empty_backup','backup-0',"import sqlite3\ndef solve(p):\n sqlite3.connect(p['destination_path']).close()\n return dict(status='created',byte_clone=False,schema_equal=True,rows_equal=True,integrity_ok=True,foreign_key_violations=0,clone_success=True,data_valid=True)\n"),
  ('input_mutation','join-0',"def solve(p):\n p['left'].clear()\n return {}\n"),
 ]:
  with tempfile.TemporaryDirectory(prefix='mutant-',dir=ROOT) as td:
   mod=pathlib.Path(td)/'candidate.py';mod.write_text(source);f=next(x for x in fs if x['id']==fixture_id);result=run(mod,f);mutants.append(dict(name=label,rejected=not check(f,result)))
 # Mutate valid reference output to isolate semantic checks without additional oracle logic.
 for label,fid,field,value in [('fk_falsely_valid','backup-1','data_valid',True),('null_match_or_wrong_product','join-1','inner_rows',5),('wrong_search_hash','search-0','sha256','0'*64),('wrong_search_id','search-0','id','k2')]:
  f=next(x for x in fs if x['id']==fid);r=run(ROOT/'reference.py',f,True)
  if f['family']=='search':r['output'][0][field]=value
  else:r['output'][field]=value
  mutants.append(dict(name=label,rejected=not check(f,r)))
 report=dict(image=IMAGE,fixtures=len(fs),runs=runs,mutation_runs=mutants,passed=all(m['rejected'] for m in mutants) and all(x['reference_pass'] and x['known_fault_rejected'] for x in runs),limits=['Synthetic correctness only; no measured transfer until generation and candidate evaluation.','Family-level n=3; 54 cases are clustered checks, not 54 independent trials.','Docker is risk reduction, not a formal hostile-code security boundary. Candidates share UID with supervisor inside isolated container; sufficiently hostile code may tamper with supervisor.','No generation candidate is executed outside Docker. Reference is not disclosed to generation.','Six fixtures per family offer limited coverage. Byte equality is independently observed from the actual created files, because different valid backup mechanisms produce different bytes.'])
 (ROOT/'test-harness.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
def evaluate(path):
 manifest=json.load(open(path));assert set(manifest)=={'method_only','raw_experience','linked_experience'}
 for arm,programs in manifest.items():assert set(programs)=={'backup','join','search'}
 fs=json.load(open(ROOT/'fixtures.json'));out=[]
 for arm,programs in manifest.items():
  for f in fs:
   r=run(pathlib.Path(programs[f['family']]).resolve(),f);out.append(dict(arm=arm,family=f['family'],fixture=f['id'],passed=check(f,r),result=r))
 assert len(out)==54
 (ROOT/'candidate-results.json').write_text(json.dumps(dict(family_n=3,case_runs=54,runs=out),indent=2))
if __name__=='__main__':
 if sys.argv[1:] == ['selftest']:selftest()
 elif len(sys.argv)==3 and sys.argv[1]=='evaluate':evaluate(sys.argv[2])
 else:raise SystemExit('Usage: harness.py selftest | evaluate MANIFEST.json')
