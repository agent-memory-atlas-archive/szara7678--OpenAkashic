import os,sys,subprocess,pathlib,json
ident=sys.argv[1]
pathlib.Path(os.environ['CODEX_HOME']).mkdir(parents=True,exist_ok=True)
relay=subprocess.Popen([sys.executable,'/harness/relay.py'])
base='http://127.0.0.1:18090/'+ident
os.environ['OA_ENDPOINT']=base
with open('/work/isolation.json','wb') as f:subprocess.run([sys.executable,'/harness/probe.py'],stdout=f,check=True)
cmd=['codex','--no-daemon','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--dangerously-bypass-approvals-and-sandbox','--json','-C','/work','-m','gpt-6-luna','-c','model_provider="isolated_eval"','-c','model_providers.isolated_eval.name="Isolated signed-in broker"','-c','model_providers.isolated_eval.base_url="'+base+'/model"','-c','model_providers.isolated_eval.wire_api="responses"','-c','model_providers.isolated_eval.requires_openai_auth=false','-c','model_providers.isolated_eval.request_max_retries=0','-c','model_providers.isolated_eval.stream_max_retries=0','-c','model_reasoning_effort="medium"','-c','web_search="disabled"','-c','features.memories=false','-c','features.multi_agent=false','-c','features.shell_snapshot=false','-o','/work/final.txt','-']
try:
 r=subprocess.run(cmd,input=pathlib.Path('/prompt.txt').read_bytes());sys.exit(r.returncode)
finally:relay.terminate()