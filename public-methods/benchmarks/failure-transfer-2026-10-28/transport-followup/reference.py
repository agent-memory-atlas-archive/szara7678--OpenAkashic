import sqlite3,hashlib,collections,re,unicodedata,os
SUFFIX=sorted(['\uc5d0\uc11c\ub294', '\uc73c\ub85c\ub294', '\uc5d0\uac8c', '\uc5d0\uc11c', '\uc73c\ub85c', '\uc740', '\ub294', '\uc774', '\uac00', '\uc744', '\ub97c', '\uc640', '\uacfc', '\ub3c4', '\uc758', '\ub85c'],key=lambda x:-len(x))
def tokens(s):
 out=[]
 for t in re.findall('[a-z0-9]+|[\uac00-\ud7a3]+',unicodedata.normalize('NFKC',s).casefold()):
  if re.fullmatch('[\uac00-\ud7a3]+',t):
   for z in SUFFIX:
    if t.endswith(z) and len(t)-len(z)>=2:t=t[:-len(z)];break
  out.append(t)
 return set(out)
def solve_join(p):
 def counts(rows):return collections.Counter(r['key'] for r in rows if r['key'] is not None and r['key'].strip())
 a,b=counts(p['left']),counts(p['right']);shared=a.keys()&b.keys();i=sum(a[k]*b[k] for k in shared);ml=sum(a[k] for k in shared);mr=sum(b[k] for k in shared);ul=len(p['left'])-ml;ur=len(p['right'])-mr
 l=any(a[k]>1 for k in shared);r=any(b[k]>1 for k in shared);actual=('many' if l else 'one')+'_to_'+('many' if r else 'one') if shared else 'none';e=p['expected_cardinality'];ok=None if e is None else (e=='many_to_many' or (e=='one_to_many' and max(a.values(),default=0)<=1) or (e=='many_to_one' and max(b.values(),default=0)<=1) or (e=='one_to_one' and max(a.values(),default=0)<=1 and max(b.values(),default=0)<=1))
 return dict(left_blank=len(p['left'])-sum(a.values()),right_blank=len(p['right'])-sum(b.values()),left_duplicate_rows=sum(v for v in a.values() if v>1),right_duplicate_rows=sum(v for v in b.values() if v>1),matched_left_rows=ml,matched_right_rows=mr,unmatched_left_rows=ul,unmatched_right_rows=ur,inner_rows=i,left_join_rows=i+ul,full_join_rows=i+ul+ur,actual_cardinality=actual,expected_satisfied=ok)
def solve_search(p):
 q=tokens(p['query']);aliases={}
 for k,vs in p['aliases'].items():
  for t in tokens(k):aliases.setdefault(t,set()).update(z for v in vs for z in tokens(v))
 scored=[(sum(bool(({t}|aliases.get(t,set()))&tokens(d['body'])) for t in q),d) for d in p['docs']];scored.sort(key=lambda x:(-x[0],x[1]['id']))
 if not scored or not scored[0][0]:return []
 d=scored[0][1];return [dict(id=d['id'],quote=d['body'][:256],sha256=hashlib.sha256(d['body'].encode()).hexdigest())]
def solve_backup(p):
 fields=['byte_clone','schema_equal','rows_equal','integrity_ok','foreign_key_violations','data_valid']
 if os.path.exists(p['destination_path']):return dict(status='destination_exists',clone_success=False,**dict.fromkeys(fields))
 s=sqlite3.connect('file:'+p['source_path']+'?mode=ro',uri=True);d=sqlite3.connect(p['destination_path']);s.backup(d);d.close();d=sqlite3.connect('file:'+p['destination_path']+'?mode=ro',uri=True)
 schema=lambda c:c.execute("select type,name,tbl_name,sql from sqlite_master where name not like 'sqlite_%' order by type,name").fetchall()
 eq=schema(s)==schema(d);rows=True
 for (t,) in s.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
  quote='"'+t.replace('"','""')+'"';rows &= collections.Counter(s.execute('select * from '+quote).fetchall())==collections.Counter(d.execute('select * from '+quote).fetchall())
 integrity=d.execute('pragma integrity_check').fetchall()==[('ok',)];fk=len(d.execute('pragma foreign_key_check').fetchall());s.close();d.close()
 return dict(status='created',byte_clone=open(p['source_path'],'rb').read()==open(p['destination_path'],'rb').read(),schema_equal=eq,rows_equal=rows,integrity_ok=integrity,foreign_key_violations=fk,clone_success=eq and rows and integrity,data_valid=integrity and fk==0)
def solve(p):return globals()['solve_'+p['family']]({k:v for k,v in p.items() if k!='family'})
