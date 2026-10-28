const {QueryClient,QueryObserver,skipToken}=require('/opt/probe/node_modules/@tanstack/query-core');
const version=require('/opt/probe/node_modules/@tanstack/query-core/package.json').version;
const tick=()=>new Promise(r=>setImmediate(r));
const out=[];
function state(c,k){const s=c.getQueryState(k);return s?{status:s.status,fetchStatus:s.fetchStatus,data:s.data,error:s.error?{name:s.error.name,message:s.error.message}:null,isInvalidated:s.isInvalidated}:null;}
function client(){return new QueryClient({defaultOptions:{queries:{retry:false,gcTime:Infinity}}});}
async function cancellation(mode){
 const c=client(),k=['cancel',mode];c.setQueryData(k,'previous-data');
 const transport={started:0,completed:0,aborted:0,signalRead:false}; let resolveTransport,signal;
 const o=new QueryObserver(c,{queryKey:k,queryFn:ctx=>{
  transport.started++;
  if(mode!=='unread'){signal=ctx.signal;transport.signalRead=true;}
  return new Promise((resolve,reject)=>{
   resolveTransport=()=>{if(!transport.aborted){transport.completed++;resolve('new-data');}};
   if(mode==='consumed'){signal.addEventListener('abort',()=>{transport.aborted++;const e=new Error('simulated transport abort');e.name='AbortError';reject(e);},{once:true});}
  });
 }});
 const unsub=o.subscribe(()=>{});await tick();const before=state(c,k);unsub();await tick();
 const afterUnsubscribe=state(c,k),signalAbortedAfterUnsubscribe=signal?.aborted??null;
 resolveTransport();await tick();await tick();
 out.push({id:'query-cancel-'+mode,mode,transportKind:'manually resolved promise; optional local AbortSignal listener; no HTTP',before,afterUnsubscribe,signalAbortedAfterUnsubscribe,afterTransportSettlement:state(c,k),transport});c.clear();
}
async function disabled(){
 const c=client(),k=['disabled-empty'];let calls=0;
 const o=new QueryObserver(c,{queryKey:k,enabled:false,queryFn:async()=>{calls++;return 'manual-data';}}),u=o.subscribe(()=>{});
 const initial={state:state(c,k),calls};await c.invalidateQueries({queryKey:k});await c.refetchQueries({queryKey:k});
 const afterInvalidationAndClientRefetch={state:state(c,k),calls};const r=await o.refetch();
 out.push({id:'query-disabled-valid-function',initial,afterInvalidationAndClientRefetch,afterObserverManualRefetch:{state:state(c,k),calls,resultStatus:r.status}});u();c.clear();
}
async function cached(){const c=client(),k=['disabled-cached'];c.setQueryData(k,'preexisting-cache');let calls=0;
 const o=new QueryObserver(c,{queryKey:k,enabled:false,queryFn:async()=>{calls++;return 'new';}}),u=o.subscribe(()=>{});
 out.push({id:'query-disabled-cached',state:state(c,k),calls});u();c.clear();}
async function skip(){const c=client(),k=['skip'];const o=new QueryObserver(c,{queryKey:k,queryFn:skipToken}),u=o.subscribe(()=>{});
 const initial=state(c,k);await c.invalidateQueries({queryKey:k});const afterInvalidation=state(c,k);const r=await o.refetch();
 out.push({id:'query-skipToken-manual-refetch',initial,afterInvalidation,afterObserverManualRefetch:state(c,k),result:{status:r.status,error:r.error?{name:r.error.name,message:r.error.message}:null}});u();c.clear();}
(async()=>{for(const mode of ['unread','read-only','consumed'])await cancellation(mode);await disabled();await cached();await skip();process.stdout.write(JSON.stringify({package:'@tanstack/query-core',version,node:process.version,observations:out},null,2)+'\n');})().catch(e=>{console.error(e);process.exitCode=1});
