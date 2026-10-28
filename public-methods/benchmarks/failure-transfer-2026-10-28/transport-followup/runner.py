import json,sqlite3,pathlib,subprocess,sys,hashlib,os
f=json.load(open('/bundle/input.json'));p=f['payload'];before={}
if f['family']=='backup':
 s=pathlib.Path('/tmp/source.sqlite');d=pathlib.Path('/tmp/dest.sqlite');c=sqlite3.connect(s);c.executescript(f['setup_sql']);c.close();s.chmod(0o444)
 if f['preexisting_destination']:d.write_bytes(b'preexisting-destination-guard');d.chmod(0o444)
 p=dict(source_path=str(s),destination_path=str(d));before={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (s,d) if x.exists()}
p['family']=f['family']
code="import importlib.util,json,sys; s=importlib.util.spec_from_file_location('candidate','/bundle/candidate.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); p=json.load(sys.stdin); p.pop('family',None); before=json.dumps(p,sort_keys=True); result=m.solve(p); print(json.dumps({'value':result,'input_unchanged':before==json.dumps(p,sort_keys=True)},ensure_ascii=False))"
if f.get('reference'):code=code.replace("p.pop('family',None); ","")
r=subprocess.run([sys.executable,'-I','-c',code],input=json.dumps(p),text=True,capture_output=True,timeout=7)
unchanged=all(pathlib.Path(x).exists() and hashlib.sha256(pathlib.Path(x).read_bytes()).hexdigest()==h for x,h in before.items())
input_unchanged=False
try:
 envelope=json.loads(r.stdout);out=envelope['value'];input_unchanged=envelope['input_unchanged']
except Exception:out={'invalid_output':r.stdout[:400]}
observed=None
if f['family']=='backup' and not f['preexisting_destination'] and d.exists():
 try:
  import collections
  a=sqlite3.connect('file:'+str(s)+'?mode=ro',uri=True);b=sqlite3.connect('file:'+str(d)+'?mode=ro',uri=True)
  query="select type,name,tbl_name,sql from sqlite_master where name not like 'sqlite_%' order by type,name"
  schema_equal=a.execute(query).fetchall()==b.execute(query).fetchall();rows_equal=True
  for (name,) in a.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
   quoted='"'+name.replace('"','""')+'"'
   rows_equal=rows_equal and collections.Counter(a.execute('select * from '+quoted).fetchall())==collections.Counter(b.execute('select * from '+quoted).fetchall())
  integrity=b.execute('pragma integrity_check').fetchall()==[('ok',)];fk=len(b.execute('pragma foreign_key_check').fetchall())
  observed=dict(schema_equal=schema_equal,rows_equal=rows_equal,integrity_ok=integrity,foreign_key_violations=fk,clone_success=schema_equal and rows_equal and integrity,data_valid=integrity and fk==0);a.close();b.close()
 except Exception:observed=None
actual_byte = (s.read_bytes()==d.read_bytes()) if f['family']=='backup' and not f['preexisting_destination'] and d.exists() else None
print(json.dumps(dict(output=out,unchanged=unchanged,actual_byte=actual_byte,backup_observed=observed,input_unchanged=input_unchanged,returncode=r.returncode,stderr=r.stderr[:1000])))
