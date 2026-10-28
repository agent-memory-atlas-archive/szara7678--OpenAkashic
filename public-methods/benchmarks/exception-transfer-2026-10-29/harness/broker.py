#!/usr/bin/env python3
"""Trusted host broker: no credential or private source enters candidate containers."""
import os,sys,json,time,re,sqlite3,hashlib,socketserver,http.server,http.client,urllib.parse,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNS={}
LOCK=threading.Lock()
APP=None

def append(path,obj):
    with LOCK:
        with path.open('a',encoding='utf-8') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')

def digest(data):return hashlib.sha256(data).hexdigest()

class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def send_bytes(self,status,data,ctype='application/json'):
        self.send_response(status);self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def fail(self,status,message):self.send_bytes(status,json.dumps({'error':message}).encode())
    def do_GET(self):
        bits=self.path.split('/',2)
        if len(bits)<3 or bits[1] not in RUNS or bits[1]!=self.server.run_id:return self.fail(403,'unknown run')
        run=RUNS[bits[1]];route='/'+bits[2]
        if not run['oa']:return self.fail(403,'Knowledge retrieval is unavailable in this condition')
        path=urllib.parse.urlsplit(route).path
        if not re.fullmatch(r'/research/api/methods/(?:search|context|catalog|network|[A-Za-z0-9_:-]+(?:/graph)?)',path):return self.fail(403,'route not allowed')
        if path.endswith(('/evaluation','/report','/graph','/network')):return self.fail(403,'evaluation not exposed')
        run['gets']+=1
        if run['gets']>20:return self.fail(429,'20 retrieval request budget reached')
        t=time.monotonic()
        try:
            from fastapi.testclient import TestClient
            with TestClient(APP) as client:
                if run.get('arm')=='flat':
                    from flat_view import flat_response
                    status,b=flat_response(client,route)
                else:
                    response=client.get(route);status,b=response.status_code,response.content
            append(run['dir']/'retrieval.jsonl',{'route':route,'status':status,'seconds':time.monotonic()-t,'response_bytes':len(b),'sha256':digest(b),'body':json.loads(b)})
            self.send_bytes(status,b)
        except Exception as e:
            append(run['dir']/'retrieval.jsonl',{'route':route,'error_type':type(e).__name__})
            self.fail(502,'retrieval failed: '+type(e).__name__)
    def do_POST(self):
        bits=self.path.split('/',2)
        if len(bits)<3 or bits[1] not in RUNS or bits[1]!=self.server.run_id:return self.fail(403,'unknown run')
        run=RUNS[bits[1]]
        if bits[2]!='model/responses':return self.fail(403,'route not allowed')
        n=int(self.headers.get('Content-Length','0'))
        if n<1 or n>2000000:return self.fail(413,'request size')
        body=self.rfile.read(n);data=json.loads(body)
        if data.get('model')!=run['model']:return self.fail(403,'model mismatch')
        run['calls']+=1
        if run['calls']>24:return self.fail(429,'model request budget reached')
        # Read only on the trusted host; token values are never serialized to logs.
        auth=json.loads(Path('/home/insu/.codex/auth.json').read_text())
        tokens=auth.get('tokens',{})
        access=tokens.get('access_token')
        if not access:return self.fail(503,'signed-in auth unavailable')
        headers={k:v for k,v in self.headers.items() if k.lower() not in {'host','authorization','content-length','connection','accept-encoding','content-type','accept','content-encoding'}}
        headers['Authorization']='Bearer '+access
        if tokens.get('account_id'):headers['ChatGPT-Account-Id']=tokens['account_id']
        headers['Content-Type']='application/json';headers['Accept']='text/event-stream'
        data['store']=False;body=json.dumps(data).encode()
        append(run['dir']/'request-audit.jsonl',{'call':run['calls'],'model':data.get('model'),'previous_response_id_present':bool(data.get('previous_response_id')),'store':data.get('store'),'tools':[v.get('name',v.get('type')) for v in data.get('tools',[])],'input_items':len(data.get('input',[]))})
        t=time.monotonic();c=http.client.HTTPSConnection('chatgpt.com',timeout=120)
        try:
            c.request('POST','/backend-api/codex/responses',body,headers)
            r=c.getresponse()
            if r.status!=200:
                b=r.read(100000)
                append(run['dir']/'model-receipts.jsonl',{'status':r.status,'seconds':time.monotonic()-t,'response_sha256':digest(b),'call':run['calls']})
                return self.send_bytes(r.status,b,r.getheader('Content-Type','application/json'))
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            event=b'';buf=b'';response_meta={};events=0
            while True:
                chunk=r.read1(32768)
                if not chunk:break
                self.wfile.write(chunk);self.wfile.flush();buf+=chunk
                while b'\n' in buf:
                    line,buf=buf.split(b'\n',1)
                    if line.startswith(b'data: '):
                        try:
                            e=json.loads(line[6:]);events+=1
                            resp=e.get('response',{})
                            if resp.get('model'):response_meta['model']=resp['model']
                            if resp.get('usage'):response_meta['usage']={k:v for k,v in resp['usage'].items() if k!='attribution'}
                            if e.get('type')=='response.completed':response_meta['completed']=True
                        except (ValueError,TypeError):pass
            append(run['dir']/'model-receipts.jsonl',{'status':200,'call':run['calls'],'seconds':time.monotonic()-t,'events':events,**response_meta})
        except Exception as e:
            append(run['dir']/'model-receipts.jsonl',{'error_type':type(e).__name__,'call':run['calls'],'seconds':time.monotonic()-t})
        finally:c.close();self.close_connection=True

def main():
    global APP
    spec=json.loads(Path(sys.argv[1]).read_text())
    for run in spec['runs']:
        run['dir']=Path(run['dir']);run['dir'].mkdir(parents=True,exist_ok=True)
        run.update(calls=0,gets=0);RUNS[run['id']]=run
    if spec.get('snapshot'):
        os.environ.update(spec['env'])
        sys.path.insert(0,spec['api_path'])
        from app.research_main import app
        APP=app
    servers=[]
    for ident in RUNS:
        sock=Path('/tmp/oa-exception-20261029')/'bridges'/ident/'broker.sock';sock.parent.mkdir(parents=True,exist_ok=True)
        if sock.exists():sock.unlink()
        server=Server(str(sock),Handler);server.run_id=ident;os.chmod(sock,0o666)
        threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
    print(json.dumps({'ready':True,'runs':len(RUNS),'per_run_socket':True}),flush=True)
    threading.Event().wait()
if __name__=='__main__':main()
