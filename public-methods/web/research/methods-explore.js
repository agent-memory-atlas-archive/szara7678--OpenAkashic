"use strict";
(() => {
  const $ = id => document.getElementById(id), base = "/research/api/methods", NS="http://www.w3.org/2000/svg";
  const types={method:"방법",category:"편집상 분야",source:"출처",outcome:"적용 보고",opinion:"의견"};
  const relations={categorized_as:"분야 분류",documented_by:"출처로 등록됨",reported_application:"이 버전의 적용 보고",has_opinion:"이 버전에 남긴 의견",comments_on:"이 보고에 남긴 의견"};
  let graph, selected=null, visible=[], points=new Map(), version=0, detailVersion=0, zoom=1, shift={x:0,y:0}, dragging=null;
  const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const svg=(tag,attrs)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e;};
  const get=async path=>{const response=await fetch(base+path,{credentials:"omit"});if(!response.ok)throw Error("unavailable");return response.json();};
  const hash=text=>{let n=2166136261;for(const c of text)n=Math.imul(n^c.charCodeAt(0),16777619);return n>>>0;};
  function section(title,content,tag="p"){const s=el("section",undefined,"record-section");s.append(el("h3",title));if(Array.isArray(content)){const l=el(tag);content.forEach(x=>l.append(el("li",x)));s.append(l);}else s.append(el(tag,content));return s;}
  function neighbors(id){return graph.edges.filter(e=>e.source===id||e.target===id).map(e=>({id:e.source===id?e.target:e.source,relation:e.relation}));}
  function view(fit=false){
    if(!graph)return;
    const domain=$("atlas-domain").value,q=$("atlas-filter").value.trim().toLocaleLowerCase();
    let methods=graph.nodes.filter(n=>n.kind==="method"&&(!domain||n.domain===domain)&&(!q||[n.label,n.situation,n.goal].some(x=>x?.toLocaleLowerCase().includes(q))));
    const ids=new Set(methods.map(n=>n.id));
    for(const e of graph.edges)if(ids.has(e.source)||ids.has(e.target)){const a=graph.nodes.find(n=>n.id===e.source),b=graph.nodes.find(n=>n.id===e.target);if(a?.kind!=="method")ids.add(a.id);if(b?.kind!=="method")ids.add(b.id);}
    let allowed=new Set(graph.nodes.filter(n=>ids.has(n.id)&&(n.kind!=="source"||$("atlas-sources").checked)&&(!["outcome","opinion"].includes(n.kind)||$("atlas-feedback").checked)).map(n=>n.id));
    const depth=Number($("atlas-depth").value);
    if(depth&&selected&&allowed.has(selected.id)){let reached=new Set([selected.id]),front=[selected.id];for(let i=0;i<depth;i++){const next=[];for(const id of front)for(const n of neighbors(id))if(allowed.has(n.id)&&!reached.has(n.id)){reached.add(n.id);next.push(n.id);}front=next;}allowed=reached;}
    visible=graph.nodes.filter(n=>allowed.has(n.id));if(selected&&!allowed.has(selected.id)){selected=null;++detailVersion;$("atlas-record-title").textContent="현재 지도에서 골라보세요.";$("atlas-record").replaceChildren(el("p","필터가 바뀌었습니다. 현재 지도에 있는 기록을 선택하면 연결과 상세 내용을 볼 수 있습니다.","quiet"));const u=new URL(location.href);u.searchParams.delete("node");history.replaceState(history.state,"",u);}methods=visible.filter(n=>n.kind==="method");
    draw();if(fit)fitVisible();const list=$("atlas-list");list.replaceChildren();for(const n of methods){const b=el("button",n.label);b.type="button";b.setAttribute("aria-pressed",String(selected?.id===n.id));b.onclick=()=>choose(n.id);list.append(b);}
    $("atlas-list-count").textContent=methods.length;
    $("atlas-visible").textContent=`${visible.length}개 노드 · ${graph.edges.filter(e=>allowed.has(e.source)&&allowed.has(e.target)).length}개 연결`;
    $("atlas-empty").hidden=visible.length>0;
    $("atlas-status").textContent=`방법 ${methods.length}개 표시${depth&&selected?` · 선택한 노드에서 ${depth}단계`:""}${graph.scope.truncated?` · 상한 ${graph.scope.method_limit}개 적용됨`:""}`;
  }
  function layout(){
    const groups=graph.nodes.filter(n=>n.kind==="category").sort((a,b)=>a.label.localeCompare(b.label));
    groups.forEach((n,i)=>{const a=(i/groups.length)*Math.PI*2-Math.PI/2;points.set(n.id,{x:500+Math.cos(a)*350,y:380+Math.sin(a)*270,fixed:true});});
    for(const g of groups){const ms=graph.edges.filter(e=>e.target===g.id).map(e=>graph.nodes.find(n=>n.id===e.source));ms.forEach((m,i)=>{const a=(i/ms.length)*Math.PI*2+(hash(g.id)%7);const p=points.get(g.id);points.set(m.id,{x:p.x+Math.cos(a)*65,y:p.y+Math.sin(a)*65});});}
    for(const n of graph.nodes)if(!points.has(n.id)){const ps=neighbors(n.id).map(x=>points.get(x.id)).filter(Boolean);points.set(n.id,{x:ps.length?ps.reduce((a,p)=>a+p.x,0)/ps.length:500,y:ps.length?ps.reduce((a,p)=>a+p.y,0)/ps.length:380});const p=points.get(n.id);p.x+=(hash(n.id)%101)-50;p.y+=(hash(n.id+"y")%101)-50;}
    // Deterministic, finite layout. No continual animation or opaque similarity edges.
    const ns=graph.nodes;
    for(let step=0;step<160;step++){
      const moves=new Map(ns.map(n=>[n.id,{x:0,y:0}]));
      for(let i=0;i<ns.length;i++)for(let j=i+1;j<ns.length;j++){const a=points.get(ns[i].id),b=points.get(ns[j].id),dx=a.x-b.x||.1,dy=a.y-b.y||.1,d=Math.max(12,Math.hypot(dx,dy)),f=Math.min(4,1800/(d*d));moves.get(ns[i].id).x+=dx/d*f;moves.get(ns[i].id).y+=dy/d*f;moves.get(ns[j].id).x-=dx/d*f;moves.get(ns[j].id).y-=dy/d*f;}
      for(const e of graph.edges){const a=points.get(e.source),b=points.get(e.target),dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy)),rest=e.relation==="categorized_as"?85:60,f=(d-rest)*.018;moves.get(e.source).x+=dx/d*f;moves.get(e.source).y+=dy/d*f;moves.get(e.target).x-=dx/d*f;moves.get(e.target).y-=dy/d*f;}
      for(const n of ns){const p=points.get(n.id),m=moves.get(n.id);if(!p.fixed){p.x=Math.max(30,Math.min(970,p.x+m.x));p.y=Math.max(35,Math.min(725,p.y+m.y));}}
    }
  }
  function draw(){
    const ids=new Set(visible.map(n=>n.id)),links=graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),edges=$("atlas-edges"),nodes=$("atlas-nodes");edges.replaceChildren();nodes.replaceChildren();
    for(const e of links){const a=points.get(e.source),b=points.get(e.target);const l=svg("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:"network-edge"+(e.relation==="categorized_as"?" category":""),"data-source":e.source,"data-target":e.target});l.append(svg("title",{}));l.firstChild.textContent=relations[e.relation]||e.relation;edges.append(l);}
    for(const n of visible){const p=points.get(n.id),degree=neighbors(n.id).length,g=svg("g",{class:"network-node "+n.kind,"data-node-id":n.id,transform:`translate(${p.x} ${p.y})`,tabindex:"0",role:"button","aria-label":`${types[n.kind]}: ${n.label.length>120?n.label.slice(0,120)+"…":n.label}`,"aria-pressed":String(selected?.id===n.id)});const radius=n.kind==="category"?10:n.kind==="method"?5.5:3.7;
      g.append(svg("circle",{r:radius}));const t=svg("title",{});t.textContent=`${types[n.kind]} · ${n.label} · 연결 ${degree}개`;g.append(t);
      if(["method","category"].includes(n.kind)){const text=svg("text",{x:0,y:n.kind==="category"?-18:18,"text-anchor":"middle"});text.textContent=n.label.length>15?n.label.slice(0,15)+"…":n.label;g.append(text);}
      g.onclick=()=>choose(n.id);g.onkeydown=event=>{if(["Enter"," "].includes(event.key)){event.preventDefault();choose(n.id,true,true);}};g.onmouseenter=()=>highlight(n.id);g.onmouseleave=()=>highlight(selected?.id);nodes.append(g);
    }
    highlight(selected?.id);
  }
  function highlight(id){const around=new Set(id?[id,...neighbors(id).map(n=>n.id)]:[]);for(const n of $("atlas-nodes").children){const k=n.dataset.nodeId;n.classList.toggle("dim",Boolean(id)&&!around.has(k));n.classList.toggle("selected",k===selected?.id);n.classList.toggle("neighbor",Boolean(id)&&around.has(k));}for(const e of $("atlas-edges").children){const active=e.dataset.source===id||e.dataset.target===id;e.classList.toggle("dim",Boolean(id)&&!active);e.classList.toggle("highlight",active);}}
  async function choose(id,push=true,keyboard=false){
    const n=graph.nodes.find(x=>x.id===id);if(!n)return;selected=n;if(n.kind==="method"&&($("atlas-domain").value&&$("atlas-domain").value!==n.domain||$("atlas-filter").value)){$("atlas-domain").value="";$("atlas-filter").value="";}if(n.kind==="source")$("atlas-sources").checked=true;if(["outcome","opinion"].includes(n.kind))$("atlas-feedback").checked=true;const request=++detailVersion;
    $("atlas-record-title").textContent=["outcome","opinion"].includes(n.kind)?`${types[n.kind]} · ${n.status||n.opinion_kind}`:n.label;const panel=$("atlas-record");panel.replaceChildren(el("span",types[n.kind],"record-kind"),el("code",n.id,"record-id"));
    const url=new URL(location.href);url.searchParams.set("node",id);url.searchParams.delete("method");url.searchParams.set("depth",$("atlas-depth").value);const step=history.state?.atlasStep||0;if(push&&new URL(location.href).searchParams.get("node")!==id)history.pushState({atlasStep:step+1},"",url);else history.replaceState({atlasStep:step},"",url);$("atlas-back").disabled=!(history.state?.atlasStep);
    if(n.kind==="method"){
      panel.append(el("p","내용을 불러오는 중입니다.","quiet"));
      try{const d=await get("/"+encodeURIComponent(n.method_id));if(request!==detailVersion)return;panel.lastChild.remove();panel.append(section("지금 상황",d.situation),section("이루려는 목적",d.goal),section("해보는 순서",d.steps,"ol"),section("성공 기준",d.success_criteria,"ul"),section("적용 조건과 한계",[...d.constraints,...d.limitations],"ul"));const link=el("a","전체 방법 · 적용 보고 · 의견 읽기 ↗","record-source");link.href="/research/methods/library/?method="+encodeURIComponent(d.id);panel.append(link);}
      catch(_){if(request===detailVersion)panel.append(el("p","상세 내용을 불러오지 못했습니다. 잠시 후 다시 선택해 주세요.","quiet"));}
    }else if(n.kind==="source"){
      const u=new URL(n.url);if(["http:","https:"].includes(u.protocol)){const a=el("a","원래 출처 열기 ↗","record-source");a.href=u.href;a.target="_blank";a.rel="noopener noreferrer";panel.append(a);}panel.append(section("이 연결의 의미","아래 방법들이 이 URL을 출처로 등록했습니다. 각각의 적용 조건을 확인하세요. 같은 출처를 사용해도 독립적인 성공 검증은 아닙니다."));
    }else if(n.kind==="category")panel.append(section("이 연결의 의미","등록된 태그를 모은 편집상 분야입니다. 같은 분야의 방법들이 동일한 효과를 낸다는 뜻은 아닙니다."));
    else{panel.append(section("작성자가 남긴 내용",n.label),section("기록 상태",n.kind==="outcome"?`상태: ${n.status} · 방법 버전 ${n.method_version} · 작성자 ${n.reported_by}`:`의견 종류: ${n.opinion_kind} · 방법 버전 ${n.method_version}`));}
    if(request!==detailVersion)return;
    const related=el("section",undefined,"record-section record-neighbors");related.append(el("h3",n.kind==="source"?"이 출처를 공유하는 방법":"연결을 따라가기"));for(const item of neighbors(id)){const target=graph.nodes.find(x=>x.id===item.id),b=el("button");b.type="button";b.append(el("small",relations[item.relation]||item.relation),el("span",target.label.length>90?target.label.slice(0,90)+"…":target.label));b.onclick=()=>choose(target.id);related.append(b);}panel.append(related,el("p","기록 연결을 보여줍니다. 효과·전문가 신원·내용의 진실성은 별도 검증 대상입니다.","record-warning"));view(Number($("atlas-depth").value)>0);if(keyboard){const chosen=[...$("atlas-nodes").children].find(x=>x.dataset.nodeId===id);chosen?.focus({preventScroll:true});}
  }
  function transform(){ $("atlas-viewport").setAttribute("transform",`translate(${500+shift.x} ${380+shift.y}) scale(${zoom}) translate(-500 -380)`);}
  function fitVisible(){if(!visible.length)return;const ps=visible.map(n=>points.get(n.id)),xs=ps.map(p=>p.x),ys=ps.map(p=>p.y),minX=Math.min(...xs)-85,maxX=Math.max(...xs)+85,minY=Math.min(...ys)-55,maxY=Math.max(...ys)+55;zoom=Math.min(2.8,1000/(maxX-minX),760/(maxY-minY))*.9;shift={x:(500-(minX+maxX)/2)*zoom,y:(380-(minY+maxY)/2)*zoom};transform();}
  function scale(f){zoom=Math.max(.45,Math.min(4,zoom*f));transform();}
  ["atlas-domain","atlas-depth","atlas-sources","atlas-feedback"].forEach(id=>$(id).addEventListener("change",()=>{if(id==="atlas-depth"&&Number($(id).value)&&!selected){$("atlas-status").textContent="먼저 노드를 하나 선택해 주세요.";return;}const u=new URL(location.href);u.searchParams.set("depth",$("atlas-depth").value);history.replaceState(history.state,"",u);view(true);}));
  $("atlas-filter").addEventListener("input",()=>view(true));
  $("atlas-zoom-in").onclick=()=>scale(1.25);$("atlas-zoom-out").onclick=()=>scale(.8);$("atlas-fit").onclick=fitVisible;
  const map=$("atlas-map");map.addEventListener("keydown",e=>{if(e.target!==map)return;const shifts={ArrowLeft:[30,0],ArrowRight:[-30,0],ArrowUp:[0,30],ArrowDown:[0,-30]};if(["+","=","-","Escape",...Object.keys(shifts)].includes(e.key)){e.preventDefault();if(e.key==="Escape"){$("atlas-depth").value="0";view();}else if(shifts[e.key]){shift.x+=shifts[e.key][0];shift.y+=shifts[e.key][1];transform();}else scale(e.key==="-"?.8:1.25);}});
  map.addEventListener("pointerdown",e=>{if(e.target.closest(".network-node"))return;dragging={x:e.clientX,y:e.clientY,old:{...shift}};map.setPointerCapture(e.pointerId);});map.addEventListener("pointermove",e=>{if(!dragging)return;const rect=map.getBoundingClientRect();shift={x:dragging.old.x+(e.clientX-dragging.x)*1000/rect.width,y:dragging.old.y+(e.clientY-dragging.y)*760/rect.height};transform();});map.addEventListener("pointerup",()=>dragging=null);map.addEventListener("pointercancel",()=>dragging=null);
  $("atlas-back").onclick=()=>history.back();
  window.addEventListener("popstate",()=>{if(!graph)return;const q=new URLSearchParams(location.search);$("atlas-depth").value=["0","1","2"].includes(q.get("depth"))?q.get("depth"):"0";const n=q.get("node");if(n&&graph.nodes.some(x=>x.id===n))choose(n,false);else{selected=null;++detailVersion;$("atlas-record-title").textContent="하나의 연결부터。";$("atlas-record").replaceChildren(el("p","노드를 선택하면 상세 내용과 연결을 볼 수 있습니다.","quiet"));view(true);}$("atlas-back").disabled=!(history.state?.atlasStep);});
  $("atlas-start").onclick=()=>{const m=graph.nodes.find(n=>n.kind==="outcome"),edge=m&&graph.edges.find(e=>e.target===m.id&&e.relation==="reported_application");if(edge)choose(edge.source);else if(graph.nodes.some(n=>n.kind==="method"))choose(graph.nodes.find(n=>n.kind==="method").id);};
  (async()=>{const request=++version;try{const data=await get("/network?limit=80");if(request!==version)return;graph=data;$("atlas-total").textContent=data.scope.total_methods;for(const d of data.domains){const option=el("option",`${d.name} · ${d.count}`);option.value=d.name;$("atlas-domain").append(option);}layout();view(true);const q=new URLSearchParams(location.search),n=q.get("node"),m=q.get("method");$("atlas-depth").value=["0","1","2"].includes(q.get("depth"))?q.get("depth"):"0";if(n&&data.nodes.some(x=>x.id===n))choose(n,false);else if(m){const match=data.nodes.find(x=>x.method_id===m);if(match)choose(match.id);}}catch(_){$("atlas-status").textContent="지도를 불러오지 못했습니다. 새로고침하거나 상황으로 검색을 이용해 주세요.";$("atlas-empty").hidden=false;$("atlas-start").disabled=true;}})();
})();