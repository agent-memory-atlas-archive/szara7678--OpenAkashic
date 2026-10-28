import json,os,pathlib,socket,subprocess
out={'uid':os.getuid(),'cwd':os.getcwd(),'forbidden_paths_present':{p:pathlib.Path(p).exists() for p in ['/home/insu','/mnt/c','/root/.codex','/var/run/docker.sock','/home/eval/.codex/auth.json']},'home_files':[p.name for p in pathlib.Path('/home/eval').glob('*')]}
try:pathlib.Path('/etc/oa-isolation-probe').write_text('probe');out['root_write_blocked']=False
except OSError:out['root_write_blocked']=True
try:
 s=socket.create_connection(('1.1.1.1',443),timeout=1);s.close();out['external_network_blocked']=False
except OSError:out['external_network_blocked']=True
print(json.dumps(out))