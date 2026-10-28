import json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
m=json.loads((p/'bundle-manifest.json').read_text())
for name,sha in m['files'].items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==sha,name
assert len(json.loads((p/'blind-grades.json').read_text()))==18
for c in ['unaided','flat_same_records','compact_same_records']:
 assert len(json.loads((p/(c+'-output.json')).read_text()))==6
print('All public bundle hashes and 18 answer/rating counts match.')
