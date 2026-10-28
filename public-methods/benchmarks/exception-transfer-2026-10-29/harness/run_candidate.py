import json,pathlib,subprocess,os,time,sys,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
BINARY='/home/insu/.nvm/versions/node/v22.22.2/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex'
IMAGE='python@sha256:5789aa194f757888f41fa3d48e14b6feaa1b57c0af0b56fcb1372d6474d3bff0'
def run(ident,prompt,timeout=120):
 d=ROOT/'execution'/ident;w=d/'workspace'
 if (d/'timing.json').exists() or (d/'trace.jsonl').exists():raise RuntimeError('Refusing to overwrite a prior attempt')
 w.mkdir(parents=True,exist_ok=True);os.chmod(w,0o777)
 (d/'prompt.txt').write_text(prompt,encoding='utf-8')
 cmd=['docker','run','--rm','--name','oa-exception-'+ident,'--network','none','--read-only','--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','1g','--cpus','1','--tmpfs','/tmp:rw,nosuid,size=256m,mode=1777','--tmpfs','/home/eval:rw,nosuid,size=64m,mode=1777','-v',BINARY+':/usr/local/bin/codex:ro','-v',str(pathlib.Path(BINARY).parent/'codex-code-mode-host')+':/usr/local/bin/codex-code-mode-host:ro','-v',str(ROOT/'harness')+':/harness:ro','-v',str(ROOT/'execution'/'bridges'/ident)+':/bridge:ro','-v',str(w)+':/work:rw','-v',str(d/'prompt.txt')+':/prompt.txt:ro','-w','/work','-e','HOME=/home/eval','-e','CODEX_HOME=/home/eval/.codex',IMAGE,'python','/harness/inside.py',ident]
 (d/'container-config.json').write_text(json.dumps({'image':IMAGE,'binary_sha256':hashlib.sha256(pathlib.Path(BINARY).read_bytes()).hexdigest(),'network':'none','home':'fresh tmpfs','mounts':['native binary readonly','harness readonly','UDS broker directory readonly','task workspace readwrite','prompt readonly'],'credentials_mounted':False,'timeout_seconds':timeout,'argv':cmd},indent=2))
 t=time.monotonic();start=time.time();status='completed'
 with (d/'trace.jsonl').open('wb') as out,(d/'stderr.txt').open('wb') as err:
  p=subprocess.Popen(cmd,stdout=out,stderr=err)
  try:code=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   subprocess.run(['docker','kill','oa-exception-'+ident],capture_output=True);code=p.wait();status='timeout'
 result={'id':ident,'status':status,'exit_code':code,'wall_seconds':time.monotonic()-t,'started_epoch':start,'ended_epoch':time.time()}
 (d/'timing.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 prompt=pathlib.Path(sys.argv[2]).read_text() if len(sys.argv)>2 else 'This is a synthetic isolation smoke test. Run pwd; show only whether /home/insu and /mnt/c and /root/.codex exist (do not read anything outside /work). Write result.txt containing exactly smoke-ok. Reply only done. Do not search the web.'
 print(json.dumps(run(sys.argv[1],prompt,int(sys.argv[3]) if len(sys.argv)>3 else 120)))