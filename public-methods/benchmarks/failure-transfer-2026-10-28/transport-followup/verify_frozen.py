from pathlib import Path
import hashlib,json,sys
p=Path(__file__).resolve().parent
manifest=json.loads((p/'freeze.json').read_text())
assert hashlib.sha256((p/'freeze.json').read_bytes()).hexdigest()==(p/'freeze.sha256').read_text().strip()
for name,digest in manifest['files'].items():
 assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
print(json.dumps({'frozen_inputs_unchanged':True,'files':len(manifest['files'])}))
