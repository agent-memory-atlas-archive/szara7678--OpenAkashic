"""Read-only lookup helper. Same executable exists in both conditions."""
import argparse,json,os,urllib.request,urllib.parse
p=argparse.ArgumentParser();p.add_argument('action',choices=['search','context','get','graph','catalog']);p.add_argument('--situation',default='');p.add_argument('--goal',default='');p.add_argument('--id',default='');p.add_argument('--limit',type=int,default=3);p.add_argument('--offset',type=int,default=0);a=p.parse_args()
if a.action in ('search','context'):
 path=a.action+'?'+urllib.parse.urlencode({'situation':a.situation,'goal':a.goal,'limit':a.limit,'mode':'hybrid'})
elif a.action=='catalog':path='catalog?'+urllib.parse.urlencode({'limit':min(a.limit,24),'offset':a.offset})
else:path=urllib.parse.quote(a.id,safe='')+('/graph' if a.action=='graph' else '')
try:
 with urllib.request.urlopen(os.environ['OA_ENDPOINT']+'/research/api/methods/'+path,timeout=45) as r:print(r.read().decode())
except urllib.error.HTTPError as e:print(json.dumps({'status':e.code,'error':e.read().decode()}));raise SystemExit(1)