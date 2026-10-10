/* sae viewer: the Plan graph and the other task tabs (TAB.*), the job panel. */
"use strict";
/* ---------- planned vs actual: graph changes after plan.approved; sae's own changes (by: sae) never count ---------- */
function changes(t){var ev=t.events||[],ap=-1,r={added:{},removed:{},newE:{},oldE:{},changed:{}},needs={};
  ev.forEach((e,i)=>{if(e.type==="plan.approved")ap=i});
  ev.forEach((e,i)=>{var a=ap>=0&&i>ap&&e.by!=="sae",c;
    if(e.type==="job.added"){needs[e.job]=e.needs||[];if(a&&e.kind!=="review")r.added[e.job]=e.reason||""}
    else if(e.type==="job.changed"){if(a)r.changed[e.job]=e.reason||"";if(c=(e.changes||{}).needs){needs[e.job]=c[1];if(a){c[1].forEach(n=>{if(!c[0].includes(n))r.newE[n+">"+e.job]=e.reason||""});c[0].forEach(n=>{if(!c[1].includes(n))r.oldE[n+">"+e.job]=e.reason||""})}}}
    else if(e.type==="job.removed"&&a)r.removed[e.job]={kind:e.kind,reason:e.reason||"",needs:needs[e.job]||[]}});
  return{r:r,ap:ap}}

/* ---------- what will run: routing, planned reviews, review marks, holds (computed by the server, as the CLI) ---------- */
var dead=t=>/^(done|abandoned)$/.test(t.state.task.phase),
 // reviews that sae will add, drawn in their final place; spec and plan reviews sit with the shaping chips
 planned=t=>(t.planned_reviews||[]).filter(p=>!own(JS(t),p.id)),
 PLo=(t,id)=>planned(t).find(p=>p.id===id),
 RT=(t,id)=>{var r=own(t.routing||{},id);return r&&!r.error?r:null},
 // a model's color by its entry; an exact Codex version (cx-2-core) takes its family's color (core)
 mcol=(t,h,m)=>{var L=(t.models||{})[h]||[];return modelColor(t.models,h,L.some(x=>x.model===m)?m:((L.find(x=>x.family&&String(m).endsWith("-"+x.model))||{}).model||m))},
 // model · effort of a node: the last attempt, else what routing (or an override) will give
 modelOf=(t,id)=>{var j=JO(t,id),a=j&&lastA(j),r=RT(t,id),p=PLo(t,id);
  if(a&&a.model)return{h:a.harness||"",m:a.model,e:a.effort||"",ran:1};   // attempts of old tasks may lack the effort
  if(r)return{h:r.harness,m:r.model_entry||r.model,e:r.effort||"",ovr:r.override,routed:r.routed,tier:r.tier,src:r.source};
  return p&&p.model?{h:p.harness,m:p.model,e:p.effort||""}:null},
 // colored words for tooltips and lists (the same palette as the routing panel)
 mwords=(t,x)=>x?'<span class="w"><span class="wm" style="--mc:'+mcol(t,x.h,x.m)+'">'+esc(x.m)+"</span>"+(x.e?"<i> · </i>"+effortWord(x.e):"")+"</span>":"–",
 srcText=x=>!x?"":x.ovr?"override":x.ran?"":[x.tier&&"tier "+x.tier,x.src&&x.src!=="global"&&x.src].filter(Boolean).join(", "),
 canOvr=(t,id)=>!dead(t)&&(!!PLo(t,id)||(JO(t,id)||{}).status==="pending"),
 // the review of a job, existing or planned: its id and model
 reviewOf=(t,id)=>{var rs=reviewsOf(t,id),k=rs.length?rs[rs.length-1]:"REVIEW-"+id;return{id:k,m:modelOf(t,k)}},
 cap1=s=>String(s||"").replace(/^./,c=>c.toUpperCase()),
 MKC={"review":"on","review · forced by settings":"forced","no review · forced by settings":"off"},
 markOf=(t,id)=>{var m=own(t.review_marks||{},id);return m&&m.mark?m:null},
 markTip=(t,id,m)=>{var r=m.reviewed&&reviewOf(t,id);
  return"<b>"+esc(cap1(m.reason))+".</b>"+(r?r.m?"<br>Review "+(r.m.ran?"ran":"planned")+" on "+esc(r.m.h)+" · "+mwords(t,r.m)+(r.m.ovr?' <span class="mut">(override)</span>':""):"<br>Review model: routing is incomplete.":"<br>Check <b>jobs</b> in the review points to review it.")},
 holdsOf=t=>t.state.task.holds||{},
 holdOn=(t,id)=>(t.holds_active||[]).includes(id), // graph.active_holds, served with the task
 holdCmd=(t,id)=>IDX.sae+" hold "+t.state.task.id+" "+id+" --release",
 holdBtn=(t,id)=>dead(t)||!JO(t,id)?"":own(holdsOf(t),id)?'<button class="btn sm" data-act="hold" data-id="'+esc(id)+'" data-v="release" title="Remove the hold: dispatching continues.">Release hold</button>':
  '<button class="btn sm" data-act="hold" data-id="'+esc(id)+'" data-v="set" title="Once this job is done, nothing new is dispatched until you release the hold. Running jobs finish.">Hold after</button>';

/* ---------- graph: layer = longest path from a root, barycenter order ---------- */
var preExec=(t,id)=>{var j=JS(t)[id];return j.kind==="review"?/^(spec|plan)$/.test(j.target):/^(research|planning)$/.test(j.kind)&&!j.needs.length&&!jf(t,o=>o.needs.includes(id)).length};
function graph(t){var js=JS(t),ch=changes(t).r,ids=jf(t,(j,id)=>!preExec(t,id)),pl=planned(t).filter(p=>!/^(spec|plan)$/.test(p.target)),PL={},
   lay={},has={},inc={},up={},dn={},cols=[],pos={},xy={},E0=[],par={},at={},
   ghosts=Object.keys(ch.removed).filter(id=>!js[id]),nodes=ids.concat(ghosts,pl.map(p=>p.id)),
   eg=(a,b,c,tip)=>{if((inc[b]||[]).includes(a))return;E0.push([a,b,c,tip]);(inc[b]=inc[b]||[]).push(a)},
   pa=(id,p,c)=>{if(!has[p]||p===id)return;var L=par[id]=par[id]||[];if(!L.some(x=>x[0]===p))L.push([p,c])},
   ints=ids.filter(id=>js[id].kind==="review"&&js[id].target==="integration"),lastInt=ints[ints.length-1];
  pl.forEach(p=>{PL[p.id]=p});nodes.forEach(id=>{has[id]=1});
  (t.events||[]).forEach((e,i)=>{if(e.type==="job.added"&&at[e.job]==null)at[e.job]=i});
  // parents: planner needs, then the edges sae generates ([GENERATED-JOB-EDGES]); "gen" edges are never plan changes
  ids.forEach(id=>{var j=js[id],gen=j.generated?j.needs:(j.generated_needs||[]);
    j.needs.forEach(n=>pa(id,n,gen.includes(n)?"gen":""));
    if(/^(decision|review)$/.test(j.kind)&&js[j.target])pa(id,j.target,"tgt");
    if(j.fix_of)pa(id,j.fix_of,"gen");
    // a task of the old sae added the integration review without needs: it follows the writers added before it
    if(j.kind==="review"&&j.target==="integration"&&!j.needs.length)ids.filter(k=>WR[js[k].kind]&&!(at[k]>at[id])).forEach(k=>pa(id,k,"gen"));
    if(j.final&&lastInt)pa(id,lastInt,"gen")});
  pl.forEach(p=>{(p.needs||[]).forEach(n=>pa(p.id,n,"pl"));(p.needed_by||[]).forEach(k=>pa(k,p.id,"pl"))});
  // an integration review draws edges from the last writers only: the others reach it through them
  var anc={},A=id=>{if(anc[id])return anc[id];var o=anc[id]={};(par[id]||[]).forEach(x=>{o[x[0]]=1;Object.assign(o,A(x[0]))});return o};
  nodes.forEach(id=>{var j=js[id]||PL[id],P=par[id];if(j&&j.target==="integration"&&P)par[id]=P.filter(x=>x[1]===""||!P.some(y=>y[0]!==x[0]&&A(y[0])[x[0]]))});
  nodes.forEach(id=>(par[id]||[]).forEach(x=>{var nw=x[1]===""||x[1]==="tgt"?ch.newE[x[0]+">"+id]:null;eg(x[0],id,(nw!=null?"new ":"")+x[1],nw!=null?"Edge added after plan approval: "+nw:"")}));
  ghosts.forEach(id=>ch.removed[id].needs.filter(n=>has[n]).forEach(x=>eg(x,id,"old")));
  Object.keys(ch.oldE).map(k=>k.split(">")).filter(e=>has[e[0]]&&has[e[1]]&&!(inc[e[1]]||[]).includes(e[0])).forEach(e=>eg(e[0],e[1],"old","Edge removed after plan approval: "+ch.oldE[e.join(">")]));
  // [AMEND-4] a job added during execution without parents starts in the column of the rightmost job
  // dispatched (running or done) before it was added; from the event log, so it never moves later
  var ev=t.events||[],ap=ev.findIndex(e=>e.type==="plan.approved"),
   floor=(id,seen)=>{if(inc[id]||!js[id]||ap<0||!(at[id]>ap))return 0;var v=0;
    ev.slice(0,at[id]).forEach(e=>{if(e.type==="job.dispatched"&&has[e.job]&&e.job!==id)v=Math.max(v,L(e.job,seen))});return v};
  var L=(id,seen)=>{if(lay[id]!=null)return lay[id];if(seen[id])return 0;seen[id]=1;var v=floor(id,seen);(inc[id]||[]).forEach(x=>{v=Math.max(v,L(x,seen)+1)});seen[id]=0;return lay[id]=v};
  nodes.forEach(id=>{L(id,{})});
  // a long edge gets one waypoint per layer it crosses, so it never passes under a node
  var chains=E0.map((e,n)=>{var c=[e[0]];for(var k=lay[e[0]]+1;k<lay[e[1]];k++){var d="~"+n+"~"+k;lay[d]=k;c.push(d)}c.push(e[1]);
    for(var i=1;i<c.length;i++){(up[c[i]]=up[c[i]]||[]).push(c[i-1]);(dn[c[i-1]]=dn[c[i-1]]||[]).push(c[i])}return c});
  Object.keys(lay).forEach(id=>(cols[lay[id]]=cols[lay[id]]||[]).push(id));cols=cols.filter(Boolean);
  var ix=()=>cols.forEach(c=>c.forEach((id,i)=>{pos[id]=i-(c.length-1)/2})),
   bary=(c,rel)=>{var b={};c.forEach(id=>{var r=(rel[id]||[]).filter(x=>pos[x]!=null);b[id]=r.length?r.reduce((s,x)=>s+pos[x],0)/r.length:pos[id]});c.sort((a,z)=>b[a]-b[z]||pos[a]-pos[z])};
  ix();for(var n=0;n<4;n++){for(var l=1;l<cols.length;l++){bary(cols[l],up);ix()}for(l=cols.length-2;l>=0;l--){bary(cols[l],dn);ix()}}
  // nodes with a review or hold mark get a fourth line; then every node is that tall
  var tall=nodes.some(id=>markOf(t,id)||own(holdsOf(t),id)),NW=240,NH=tall?90:68,DH=8,GX=40,GY=16,P=20,h=id=>id[0]==="~"?DH:NH,colH=c=>c.reduce((s,id)=>s+h(id)+GY,-GY),max=Math.max(NH,...cols.map(colH)),Hh=P*2+max,Wd=P*2+cols.length*NW+(cols.length-1)*GX;
  cols.forEach((c,l)=>{var y=P+(max-colH(c))/2;c.forEach(id=>{xy[id]=[P+l*(NW+GX),y];y+=h(id)+GY})});
  var cy=id=>xy[id][1]+(id[0]==="~"?DH/2:34),
   port=(id,other,list)=>{if(id[0]==="~")return cy(id);var o=list[id].slice().sort((a,b)=>cy(a)-cy(b)),k=o.length,sp=Math.min(12,44/Math.max(1,k-1));return cy(id)+(o.indexOf(other)-(k-1)/2)*sp},
   E=chains.map((c,n)=>{var e=E0[n],y0=port(c[0],c[1],dn),d="M"+(xy[c[0]][0]+NW)+" "+y0;
    for(var i=1;i<c.length;i++){var x0=xy[c[i-1]][0]+NW,x1=xy[c[i]][0],last=i===c.length-1,y1=last?port(c[i],c[i-1],up):cy(c[i]),m=(x1-x0)/2;
      d+="C"+(x0+m)+" "+y0+" "+(x1-m)+" "+y1+" "+x1+" "+y1+(last?"":"H"+(x1+NW));y0=y1}
    return'<path class="e '+e[2]+'" d="'+d+'">'+(e[3]?"<title>"+esc(e[3])+"</title>":"")+"</path>"});
  var N=nodes.map(id=>node(t,id,ch,PL[id],xy[id],NW,NH));
  return{svg:'<svg width="'+Wd+'" height="'+Hh+'" viewBox="0 0 '+Wd+" "+Hh+'" role="group" aria-label="Job graph">'+E.join("")+N.join("")+"</svg>",inner:E.join("")+N.join(""),w:Wd,h:Hh,layer:lay,n:nodes.length,ch:ch,pl:pl.length,edges:E0}}

/* ---------- graph canvas ([AMEND-4]): the view {x, y, k} lives per task in GV, so a refresh keeps it ---------- */
var GV={},GZ=[.2,2],gvK=k=>Math.min(GZ[1],Math.max(GZ[0],k)),
 gvT=v=>"translate("+v.x+" "+v.y+") scale("+v.k+")",
 gvFit=(W,H,w,h)=>{var k=gvK(Math.min(1,(W-32)/w,(H-32)/h));return{x:(W-w*k)/2,y:(H-h*k)/2,k:k}},
 // zoom by factor f around the point (px, py) of the canvas: that point stays under the pointer
 gvZoom=(v,px,py,f)=>{var k=gvK(v.k*f),r=k/v.k;return{x:px-(px-v.x)*r,y:py-(py-v.y)*r,k:k}};
function gvCanvas(g){var v=GV[S.task];
  return'<div class="gwrap" data-task="'+esc(S.task)+'" data-w="'+g.w+'" data-h="'+g.h+'" style="height:min(70vh,'+Math.max(260,g.h+40)+'px)">'+
   '<svg class="gcv" width="100%" height="100%" role="group" aria-label="Job graph"><g class="gv"'+(v?' transform="'+gvT(v)+'"':"")+">"+g.inner+"</g></svg>"+
   '<div class="gz"><button class="btn ic sm" data-gz="in" aria-label="Zoom in">+</button><button class="btn ic sm" data-gz="out" aria-label="Zoom out">−</button>'+
   '<button class="btn sm" data-gz="fit" aria-label="Fit the whole graph">fit</button></div></div>'}
// after each render: the first open of a task fits the graph; then the stored view is applied
function gvMount(){var w=$(".gwrap");if(!w||w.dataset.task!==S.task)return;var W=w.clientWidth,H=w.clientHeight;
  if(!GV[S.task]){if(!(W>0&&H>0))return;GV[S.task]=gvFit(W,H,+w.dataset.w,+w.dataset.h)}
  var v=GV[S.task],g=w.querySelector(".gv");if(g)g.setAttribute("transform",gvT(v));
  // the dot grid follows pan and zoom: dots move closer when zoomed out
  w.style.backgroundSize=16*v.k+"px "+16*v.k+"px";w.style.backgroundPosition=v.x+"px "+v.y+"px"}
var gvSet=v=>{GV[S.task]=v;gvMount()},gvDrag=null;
D.addEventListener("wheel",e=>{var w=e.target.closest&&e.target.closest(".gwrap"),v=GV[S.task];if(!w||!v)return;e.preventDefault();
  var r=w.getBoundingClientRect();
  // Cmd+scroll (Ctrl+scroll elsewhere, and trackpad pinch) zooms around the pointer; plain scroll pans
  gvSet(e.ctrlKey||e.metaKey?gvZoom(v,e.clientX-r.left,e.clientY-r.top,Math.exp(-e.deltaY*.0015)):{x:v.x-e.deltaX,y:v.y-e.deltaY,k:v.k})},{passive:false});
D.addEventListener("pointerdown",e=>{var w=e.target.closest&&e.target.closest(".gwrap"),v=GV[S.task];
  if(!w||!v||e.button!==0||e.target.closest(".nd,.gz"))return;gvDrag={x:e.clientX,y:e.clientY,v:v};w.classList.add("drag")});
D.addEventListener("pointermove",e=>{if(gvDrag)gvSet({x:gvDrag.v.x+e.clientX-gvDrag.x,y:gvDrag.v.y+e.clientY-gvDrag.y,k:gvDrag.v.k})});
D.addEventListener("pointerup",()=>{if(!gvDrag)return;gvDrag=null;var w=$(".gwrap");if(w)w.classList.remove("drag")});
D.addEventListener("click",e=>{var b=e.target.closest&&e.target.closest("[data-gz]"),w=$(".gwrap"),v=GV[S.task];if(!b||!w||!v)return;
  var W=w.clientWidth,H=w.clientHeight,z=b.dataset.gz;
  gvSet(z==="fit"?gvFit(W,H,+w.dataset.w,+w.dataset.h):gvZoom(v,W/2,H/2,z==="in"?1.25:.8))});
// one node: ID and status; kind and difficulty; model · effort (a button when it can change); review and hold marks
function node(t,id,ch,p,at,NW,NH){var js=JS(t),g=!js[id]&&!p,j=js[id]||(p?{kind:"review",target:p.target,needs:[]}:{kind:ch.removed[id].kind,needs:[]}),
   s=g?"removed":p?"planned":stOf(t,id),pw=Math.round(s.length*6.6+24),x=!g&&modelOf(t,id),ed=canOvr(t,id),
   mk=!p&&(ch.added[id]!=null?"added":ch.changed[id]!=null?"changed":""),r=g||p?{}:revInfo(t,id),vp=r.v?Math.round(r.v.length*6.6+24):0,sm=g||p?0:staleM(t,id),
   right=[mk,r.x!=="review due"&&r.x,sm&&"no activity "+span(sm)].filter(Boolean).join(" · "),
   sub=j.kind+(/^(review|decision)$/.test(j.kind)?" → "+(j.target||""):j.difficulty?" · "+j.difficulty:""),
   tip=id+" — "+s+(s==="pending"&&waits(t,id).length?"\nWaits for: "+waits(t,id).join("; "):"")+(p?"\nPlanned: sae adds this review when "+(p.target==="integration"?"every writer job is merged":p.target+" is done")+". Not counted in progress.":"")+
    (g?". Removed after plan approval: "+ch.removed[id].reason:mk?". "+(mk==="added"?"Added":"Changed")+" after plan approval: "+(ch.added[id]||ch.changed[id]):"")+(sm?". No activity for "+span(sm)+". "+staleTip(t,id):""),
   room=Math.max(6,Math.floor((NW-30-vp-right.length*6.4)/7.3)),mt=x?trunc(x.m,Math.max(3,room-x.e.length-3-(x.ovr?11:0))):"",
   lab=x?'<tspan class="tm" style="--mc:'+mcol(t,x.h,x.m)+'">'+esc(mt)+"</tspan>"+(x.e?'<tspan> · </tspan><tspan class="te'+(x.e==="ultra"?" u":"")+'" style="--ec:'+effortColor(x.e)+'">'+esc(x.e)+"</tspan>":"")+(x.ovr?'<tspan class="to"> · override</tspan>':""):"–",
   ltip=x&&x.ovr?"<b>Override for this job.</b><br>"+esc(x.h)+" · "+mwords(t,x)+(x.routed?"<br>Routing would pick "+esc(x.routed.harness)+" · "+mwords(t,{h:x.routed.harness,m:x.routed.model_entry,e:x.routed.effort}):"")+(ed?"<br>Click to change or clear it.":""):
    x?"<b>"+(x.ran?"Last attempt":"Routing")+"</b>: "+esc(x.h)+" · "+mwords(t,x)+(srcText(x)?' <span class="mut">('+esc(srcText(x))+")</span>":"")+(ed?"<br>Click to run it on another model.":""):"",
   lw=Math.min(NW-20-vp-(right?right.length*6.4+8:0),Math.round(((x?mt.length+3+x.e.length+(x.ovr?11:0):1))*7.3+8)),
   rm=!g&&!p&&markOf(t,id),hd=!g&&!p&&own(holdsOf(t),id),y4=66,m4="",cx=10;
  if(rm){var w=Math.round(rm.mark.length*6.4+16);m4+='<g class="mk '+(MKC[rm.mark]||"on")+'" transform="translate('+cx+","+y4+')" tabindex="0" role="note" aria-label="'+esc(rm.mark+": "+rm.reason)+'" data-tiph="'+esc(markTip(t,id,rm))+'"><rect width="'+w+'" height="18" rx="4"/><text x="8" y="13">'+esc(rm.mark)+"</text></g>";cx+=w+6}
  if(hd){var on=holdOn(t,id),ht=on?"⏸ hold active":"⏸ hold after",hw=Math.round(ht.length*6.4+16);
    [on?"⏸ active":"⏸ hold","⏸"].forEach(v=>{if(cx+hw>NW-8){ht=v;hw=Math.round(v.length*6.4+16)}}); // beside a long review mark; the tooltip says it all
    m4+='<g class="mk hold'+(on?" on":"")+'" transform="translate('+cx+","+y4+')" tabindex="0" role="note" aria-label="'+esc(on?"hold active":"hold after this job")+'" data-tiph="'+esc("<b>"+(on?"Hold active: nothing new is dispatched.":"Hold after "+id+": once it is done"+(WR[j.kind]?" and merged":"")+", nothing new is dispatched.")+"</b>"+(hd.reason?"<br>"+esc(hd.reason):"")+"<br>Release: "+esc(holdCmd(t,id)))+'"><rect width="'+hw+'" height="18" rx="4"/><text x="8" y="13">'+esc(ht)+"</text></g>"}
  return'<g class="nd k-'+s+(g?" ghost":"")+(p?" planned":"")+(S.job===id?" sel":"")+'" style="--kc:var(--kd-'+esc(j.kind)+')" transform="translate('+at+')"'+(p?"":' tabindex="0" role="button"'+dataJ("job",id))+' aria-label="'+esc(tip)+'" data-tip="'+esc(tip)+'">'+
    '<rect class="ring" x="-3" y="-3" width="'+(NW+6)+'" height="'+(NH+6)+'" rx="7"/><rect class="nb" width="'+NW+'" height="'+NH+'" rx="5"/>'+(mk?'<rect class="nbar" x="1" y="8" width="2" height="'+(NH-16)+'"/>':"")+'<text class="nid" x="10" y="21">'+esc(trunc(id,j.merged?17:19))+"</text>"+
    (j.merged?'<text x="'+(NW-pw-24)+'" y="21">✓</text>':"")+'<g class="sp" transform="translate('+(NW-pw-8)+',7)"><rect width="'+pw+'" height="20" rx="4"/><text x="7" y="14">'+(p?"◌":GL[s])+" "+s+"</text></g>"+
    '<text class="nk" x="10" y="40">'+esc(trunc(sub,32))+"</text>"+
    '<g class="ml'+(ed?" ed":"")+'"'+(ed?' data-act="ovr" data-id="'+esc(id)+'" tabindex="0" role="button" aria-haspopup="dialog" aria-label="'+esc("Model of "+id+": "+(x?x.h+" · "+x.m+" · "+x.e+(x.ovr?", override":""):"none")+". Change")+'"':"")+(ltip?' data-tiph="'+esc(ltip)+'"':"")+'><rect class="hit" x="6" y="45" width="'+Math.max(16,lw)+'" height="18" rx="3"/><text class="nm" x="10" y="58">'+lab+"</text></g>"+
    (vp?'<g class="sp k-'+VC[r.v]+'" transform="translate('+(NW-8-vp)+',44)"><rect width="'+vp+'" height="18" rx="4"/><text x="7" y="13">'+(r.v[0]==="c"?"✕ ":"✓ ")+r.v+"</text></g>":"")+
    (right?'<text x="'+(NW-(vp?vp+14:10))+'" y="58" text-anchor="end">'+esc(right)+"</text>":"")+m4+"</g>"}

/* ---------- tabs ---------- */
var TAB={};
TAB.overview=t=>{var js=JS(t),ids=Object.keys(js),info=t.state.task,c={},tok=0,L=[],R="",need=[],plan=t.files["plan.md"];
  ids.forEach(id=>{var s=stOf(t,id);c[s]=(c[s]||0)+1;tok+=tokens(js[id])});
  var out='<div class="kpis">'+[["Done",(c.done||0)+"<span> / "+ids.length+"</span>"],["Running",c.running||0],["Parked",c.parked||0],["Ready",c.ready||0],["Tokens",num(tok)]].map(k=>'<div class="kpi"><div>'+k[0]+"</div><b>"+k[1]+"</b></div>").join("")+"</div>";
  if(info.phase==="done")L.push(report(t));
  else if(info.phase==="abandoned")L.push(sec("Abandoned",box([line(esc((evs(t,/^task\.abandoned$/)[0]||{}).reason))])));
  else{var nx=next(t);if(nx)need.push(line(nx[0],nx[1]&&code(nx[1])));
    jf(t,j=>j.status==="parked").forEach(id=>{var dj=jf(t,j=>j.kind==="decision"&&j.target===id);
      need.push(jrow(t,id,[ask(t,id),dj.length&&"Decision job: "+dj.map(k=>esc(k)+" ("+stOf(t,k)+")").join(", ")].filter(Boolean).join("<br>"),agoH(js[id].last_change)))});
    jf(t,j=>j.status==="failed").forEach(id=>need.push(jrow(t,id,"",agoH(js[id].last_change))));
    L.push(sec("Needs you",box(need,"Nothing needs you.")));
    var ru=jf(t,j=>j.status==="running").map(id=>{var a=lastA(js[id]);return jrow(t,id,esc(js[id].kind)+(a?" · "+code(model(a))+" · "+esc(a.harness+" "+tierOf(a)):""),stale(t,id)||"last change "+agoH(js[id].last_change))}),
     re=ids.filter(id=>stOf(t,id)==="ready").map(id=>{var j=js[id];return jrow(t,id,esc(j.kind+(j.target?" → "+j.target:" · "+j.difficulty)))});
    if(ru.length)L.push(sec("Running",box(ru)));if(re.length)L.push(sec("Ready",box(re)))}
  var ra=section(stripC(plan),"Riskiest assumptions");
  if(plan!=null)R+=sec("Riskiest assumptions",filled(ra)?'<div class="box pad">'+md(ra,{meta:false})+"</div>":box([],"None recorded in plan.md."));
  R+=sec("To check before you merge",box(evs(t,FT.decisions).filter(e=>e.by==="agent").map(e=>row("",'<span class="tag">'+esc(e.type)+"</span>",(e.id?code(e.id)+" ":"")+esc(e.summary),agoH(e.at),[e["class"],J(e.job)].filter(Boolean).join(" · "))),"No agent decisions or amendments."));
  return out+'<div class="cols"><div>'+L.join("")+"</div><div>"+R+"</div></div>"};
function next(t){var i=t.state.task,p=i.phase,rd=jf(t,(j,k)=>stOf(t,k)==="ready"),run=jf(t,j=>j.status==="running").length,park=jf(t,j=>j.status==="parked").length;
  if(/^(shaping|planning)$/.test(p)){if(rd.length)return["Next: dispatch "+rd[0],"sae dispatch "+i.id+" "+rd[0]];if(run)return null;
    if(p==="shaping")return["Spec gate: check, then approve the spec.","sae approve "+i.id+" spec"];
    return i.approvals&&i.approvals.plan?["Plan approved — waiting for start.","sae start "+i.id]:["Plan gate: review the Plan tab, then approve.","sae approve "+i.id+" plan"]}
  if(!jf(t,j=>j.status!=="done").length)return["All jobs done.","sae finish "+i.id];
  return!run&&!rd.length&&!park?["Nothing can run. Adapt the graph, resume a failed job, or finish with --with-open."]:null}
function report(t){var js=JS(t),i=t.state.task,fin=evs(t,/^task\.finished$/)[0]||{},rows=[],fj=jf(t,j=>j.final)[0],b=i.base||{};
  if(fj)rows.push(row("",pill(js[fj].status),"Final validation "+J(fj)+" — "+esc(js[fj].summary)));
  evs(t,FT.reviews).forEach(e=>rows.push(row("",vpill(e.verdict),J(e.job)+" → "+tgt(t,e.target),esc(e.provider||"")+" "+code(e.model))));
  jf(t,j=>/pending|parked|failed/.test(j.status)).forEach(k=>rows.push(jrow(t,k)));
  var made=evs(t,/^(finding|backlog)\.created$/).map(e=>code(e.finding||e.file));if(made.length)rows.push(line("Findings and backlog items: "+made.join(", ")));
  rows.push(line(i.git?code(i.branch)+" (base "+esc(b.branch||"–")+" @ "+code(b.commit)+")"+(fin.commit?", head "+code(fin.commit):"")+". Nothing was pushed. Merge or open a merge request yourself.":"No git: the changes are in the working folder."));
  return sec("Final report",box(rows),agoH(fin.at))}
var KINDS=["research","planning","implementation","integration","validation","review","decision"];
TAB.plan=t=>{var js=JS(t),g=graph(t),ch=g.ch,pre=jf(t,(j,id)=>preExec(t,id)),pp=planned(t).filter(p=>/^(spec|plan)$/.test(p.target)),n=o=>Object.keys(o).length,
   ln=(c,l)=>'<span><svg width="22" height="8" aria-hidden="true"><path class="e '+c+'" d="M0 4H22"/></svg> '+l+"</span>",
   act=jf(t,(j,id)=>own(holdsOf(t),id)&&holdOn(t,id));
  var out=NOTE&&NOTE.task===S.task?'<p class="note'+(NOTE.err?" err":"")+'" role="status">'+esc(NOTE.text)+"</p>":"";
  if(act.length)out+='<div class="hbar" role="status"><b>⏸ Hold after '+act.map(esc).join(", ")+" is active.</b> Nothing new is dispatched until you release it; running jobs finish."+act.map(id=>holdBtn(t,id)).join("")+"</div>";
  out+='<div class="gh"><h2 class="lbl">Graph</h2><div class="legend">'+["pending","ready","running","done","parked","failed"].map(pill).join("")+"<span>✓ merged</span>"+(g.pl||pp.length?pill("planned").replace(/<i[^>]*><\/i>/,'<i aria-hidden="true">◌</i>'):"")+"</div></div>";
  out+=g.n?gvCanvas(g):box([],"No execution jobs yet.");
  out+='<div class="legend kinds" aria-label="Legend">'+KINDS.map(k=>'<span><i class="ks" style="--kc:var(--kd-'+k+')"></i>'+k+"</span>").join("")+'<span><i class="ks run"></i>running</span><span><i class="ks pl"></i>planned</span>'+
   (n(ch.newE)?ln("new","edge added after approval"):"")+(n(ch.oldE)||n(ch.removed)?ln("old","removed after approval"):"")+(n(ch.added)||n(ch.changed)?'<span class="lgb">added or changed after approval</span>':"")+"</div>";
  if(pre.length||pp.length)out+='<div class="chips"><span class="mut">Shaping and planning</span>'+pre.map(id=>'<button class="chip"'+dataJ("job",id)+">"+code(id)+stp(t,id)+"</button>").join("")+
   pp.map(p=>{var x=modelOf(t,p.id);return'<span class="chip planned" title="Planned: sae adds this review when the '+esc(p.target)+' is ready for it.">'+code(p.id)+pill("planned").replace(/<i[^>]*><\/i>/,'<i aria-hidden="true">◌</i>')+
    (canOvr(t,p.id)?'<button class="lnk" data-act="ovr" data-id="'+esc(p.id)+'" aria-haspopup="dialog" aria-label="Model of '+esc(p.id)+': change">'+mwords(t,x)+"</button>":mwords(t,x))+"</span>"}).join("")+"</div>";
  if(t.state.task.phase==="executing")out+=nextUp(t);
  var gl=jf(t,(j,id)=>j.kind!=="review"&&!/^(INTEGRATE|DECISION)-/.test(id)).map(id=>{var o=stripC(section(front(t.files["jobs/"+id+".md"])[1],"Objective")).trim().split(/\r?\n/)[0];
    return'<button class="row two"'+dataJ("job",id)+"><span>"+code(id)+' <span class="ink2">— '+(o?inl(o):'<span class="mut">no objective</span>')+"</span></span></button>"});
  var pr=reviewsOf(t,"plan").map(k=>row("",stp(t,k),code(k),byM(lastA(js[k])),"",k));
  out+='<div class="cols"><div>'+sec("Jobs at a glance",box(gl,"No jobs yet."))+"</div><div>"+sec("Plan review",box(pr,"No plan review."))+"</div></div>";
  var dd=["plan.md","brief.md"].filter(f=>t.files[f]!=null);
  return out+(dd.length?sec("Documents",docs("d:",dd,t.files)):"")};
// [VIEWER-NEXT-UP]: the ready list of `sae next` (the server runs the same code), running jobs, holds
function nextUp(t){var nx=t.next;if(!nx)return"";if(nx.error)return sec("Next up",box([line('<span class="err">'+esc(nx.error)+"</span>")]));
  var rt=r=>({h:r.harness,m:r.model_entry||r.model,e:r.effort,ovr:r.override,tier:r.tier,src:r.source}),rows=[],
   hs=(nx.holds||[]).filter(h=>!(nx.holds_active||[]).includes(h.job));
  (nx.ready||[]).forEach(r=>{var x=r.routing?rt(r.routing):null;
    rows.push(row("fx",pill("ready"),J(r.id)+' <span class="ink2">'+esc(r.kind+(r.difficulty?" · "+r.difficulty:""))+"</span>",holdBtn(t,r.id),
     (x?esc(x.h)+" · "+mwords(t,x)+(srcText(x)?' <span class="mut">('+esc(srcText(x))+")</span>":""):esc(r.model||""))+(r.workspace?' <span class="mut">· '+esc(r.workspace)+"</span>":"")+(r.blocked?'<br><span class="mut">waits: '+esc(r.blocked)+"</span>":"")))});
  (nx.running||[]).forEach(r=>{var x=modelOf(t,r.id);rows.push(row("fx",pill("running"),J(r.id)+sp(stale(t,r.id)),holdBtn(t,r.id),x?esc(x.h)+" · "+mwords(t,x):""))});
  var h=sec("Next up",box(rows,(nx.holds_active||[]).length?"Nothing starts: a hold is active.":"No job is ready."),nx.slots?esc(nx.slots):"");
  if(hs.length)h+=sec("Holds",box(hs.map(x=>row("",'<span class="tag">⏸ hold</span>',"after "+J(x.job)+(x.reason?' <span class="ink2">— '+esc(x.reason)+"</span>":""),holdBtn(t,x.job),"Active once "+esc(x.job)+" is done; then nothing new starts."))));
  if(nx.integration)h+=sec("Integration review",'<div class="box pad"><pre class="cmd">'+esc(nx.integration)+"</pre></div>");
  return h}

/* ---------- per-job override ([JOB-MODEL-OVERRIDE]) and holds ([HOLD-AFTER-JOB]): both run the sae command on the server ---------- */
var NOTE=null,OVR=null,
 note=(text,err)=>{NOTE={task:S.task,text:text,err:!!err};render()},
 ovrClose=f=>{var m=$(".ovm");if(m)m.remove();var o=OVR;OVR=null;if(f&&o)refocus(D,o.k)},
 // a planned review of a job is overridden as "<job> --review"; the others by their own ID
 ovrBody=(t,id)=>{var p=PLo(t,id);return p&&!/^(spec|plan|integration)$/.test(p.target)?{job:p.target,review:true}:{job:id}};
function ovrOpen(btn){var t=T(),id=btn.dataset.id;if(!t)return;ovrClose();var x=modelOf(t,id),ms=t.models||{},cur=x&&x.ovr?[x.h,x.m,x.e].join("|"):"",
   opts=Object.keys(ms).map(h=>(ms[h]||[]).filter(m=>m.enabled!==false).map(m=>'<optgroup label="'+esc(h+" · "+m.model)+'">'+(m.efforts||[]).map(e=>{var v=[h,m.model,e].join("|");return'<option value="'+esc(v)+'"'+(v===cur?" selected":"")+">"+esc(m.model+" · "+e)+"</option>"}).join("")+"</optgroup>").join("")).join(""),
   r=btn.getBoundingClientRect(),m=D.createElement("div");
  OVR={id:id,k:fkey(btn),repo:S.repo,task:S.task};m.className="ovm";m.setAttribute("role","dialog");m.setAttribute("aria-label","Model of "+id);
  m.innerHTML='<div class="oh"><b class="mono">'+esc(id)+'</b><button class="btn ic sm" data-act="oclose" aria-label="Close">✕</button></div>'+
   '<div class="ink2">'+(x?(x.ovr?"Override: ":"Now: ")+esc(x.h)+" · "+mwords(t,x):"No model yet.")+(x&&x.routed?'<br><span class="mut">Routing: '+esc(x.routed.harness)+" · </span>"+mwords(t,{h:x.routed.harness,m:x.routed.model_entry,e:x.routed.effort}):"")+"</div>"+
   '<label class="ink2">Run it on<select data-act="ovs" aria-label="Model and effort for '+esc(id)+'"><option value=""'+(cur?"":" selected")+">routing (no override)</option>"+opts+"</select></label>"+
   '<div class="mut">Applies from the next dispatch. The server runs <span class="mono">sae job override</span>.</div><div class="om" role="status"></div>';
  D.body.appendChild(m);m.style.top=Math.min(r.bottom+6,W.innerHeight-m.offsetHeight-8)+"px";m.style.left=Math.max(8,Math.min(r.left,W.innerWidth-m.offsetWidth-8))+"px";
  m.querySelector("select").focus()}
function ovrSave(sel){var o=OVR,t=o&&o.repo===S.repo&&o.task===S.task?T():null,v=sel.value.split("|"),om=$(".ovm .om");if(!t)return;sel.disabled=true;om.textContent="Saving…";
  post("override",Object.assign({repo:o.repo,task:o.task},ovrBody(t,o.id),v[0]?{harness:v[0],model:v[1],effort:v[2]}:{clear:true})).then(r=>{
    if(!r.ok){sel.disabled=false;om.textContent=(r.error||"Not saved.").split("\n")[0];om.className="om err";return}
    ovrClose(true);note((v[0]?"Override for "+o.id+": "+v.join(" · "):"Override for "+o.id+" cleared")+". It applies from the next dispatch.");loadTask()})}
function holdSet(btn){var id=btn.dataset.id,rel=btn.dataset.v==="release";btn.disabled=true;
  post("hold",{repo:S.repo,task:S.task,job:id,release:rel}).then(r=>{note(r.ok?(rel?"Released the hold after "+id+".":"Hold after "+id+": once it is done, nothing new is dispatched."):(r.error||"Not saved.").split("\n")[0],!r.ok);loadTask()})}
D.addEventListener("click",ev=>{var e=ev.target.closest("[data-act]"),a=e&&e.dataset.act;
  if(ev.target.closest(".ovm"))ev.stopPropagation();else if(OVR&&a!=="ovr")ovrClose();
  if(a==="ovr"){ev.stopPropagation();if(OVR&&OVR.id===e.dataset.id)ovrClose(true);else ovrOpen(e)}
  else if(a==="oclose")ovrClose(true);
  else if(a==="hold")holdSet(e)},true);
D.addEventListener("change",ev=>{if(ev.target.dataset&&ev.target.dataset.act==="ovs")ovrSave(ev.target)});
D.addEventListener("keydown",ev=>{if(ev.key==="Escape"&&OVR){ev.stopPropagation();ovrClose(true)}},true);
function jobOrder(t){var js=JS(t),ids=Object.keys(js),lay={},kids={},base=[],out=[],seen={},
   att=id=>{var j=js[id],p=j.fix_of||((/^(review|decision)$/.test(j.kind)||/^INTEGRATE-/.test(id))&&j.target);return p&&js[p]&&p!==id?p:null},
   L=id=>lay[id]!=null?lay[id]:(lay[id]=0,lay[id]=Math.max(0,...js[id].needs.filter(n=>js[n]).map(n=>L(n)+1)));
  ids.forEach(id=>{var p=att(id);L(id);if(p)(kids[p]=kids[p]||[]).push(id);else base.push(id)});
  var mx=Math.max(0,...ids.map(id=>lay[id])),key=id=>preExec(t,id)?-1:js[id].target==="integration"?mx-.5:lay[id],
   add=(id,d)=>{if(seen[id])return;seen[id]=1;out.push([id,d]);(kids[id]||[]).forEach(k=>add(k,1))};
  base.sort((a,b)=>key(a)-key(b)||ids.indexOf(a)-ids.indexOf(b)).forEach(id=>add(id,0));ids.forEach(id=>add(id,0));return out}
TAB.jobs=t=>{var js=JS(t);if(!Object.keys(js).length)return empty("No jobs yet.");
  return tbl("nw","ID,-Kind,Status,Last change,~Attempts,Models,~Tokens,Review",jobOrder(t).map(x=>{var id=x[0],j=js[id],op=S.job===id,tk=tokens(j);
    return tr([[x[1]?"mono mut":"mono",esc(id)],["hm",esc(j.kind)+'<span class="mut"> · '+esc(j.difficulty)+"</span>"],jpill(t,id),["ink2",agoH(j.last_change)],["n",j.attempts.length],["mono ink2",esc([...new Set(j.attempts.map(model))].join(", ")||"–")],["n",tk?num(tk):"–"],(r=>r.v?vpill(r.v):r.x?'<span class="mut">'+r.x+"</span>":"")(revInfo(t,id))],
      ' class="r1'+(op?" open":"")+'"'+dataJ("row",id)+' tabindex="0" aria-expanded="'+op+'"')+(op?'<tr><td colspan="8" class="xd">'+jobBody(t,id)+"</td></tr>":"")}))};
/* ---------- timeline overview: one row per job, one bar per attempt; long idle gaps are cut out of the axis ---------- */
function gantt(t){var js=JS(t),ev=t.events||[],info=t.state.task,M=v=>Date.parse(v),now=Date.now();
  if(!ev.length||!Object.keys(js).length)return"";
  var live=!/^(done|abandoned)$/.test(info.phase),t0=M(ev[0].at),tEnd=live?Math.max(now,M(ev[ev.length-1].at)):M(ev[ev.length-1].at),
   rows=[{id:"",d:0}].concat(jobOrder(t).map(x=>({id:x[0],d:x[1]}))),RI={},bars=[],mks=[],oc={},cur={},pts=[t0,tEnd];
  rows.forEach((r,i)=>{RI[r.id]=i});
  // outcome of an attempt: its collected status, or failed when verify failed after it
  ev.forEach(e=>{if(e.type==="job.dispatched")cur[e.job]=e.attempt;else if(e.type==="job.collected")oc[e.job+"#"+e.attempt]=e.status;else if(e.type==="job.verify_failed"&&cur[e.job]!=null)oc[e.job+"#"+cur[e.job]]="failed"});
  rows.forEach((r,i)=>{var j=js[r.id];if(!j)return;j.attempts.forEach((a,x)=>{var s0=M(a.started);if(isNaN(s0))return;
    var last=x===j.attempts.length-1,st=oc[r.id+"#"+a.n]||(last?j.status:"removed"),d=(a.duration_s||0)*1e3,
     e=a.ended?Math.max(M(a.ended),s0+d):st==="running"?now:s0+d,tail=st==="running"&&last&&staleM(t,r.id)?now:0;
    if(tail)e=Math.max(s0,M(j.last_change));
    bars.push({i:i,s:s0,e:e,tail:tail,st:st,a:a,id:r.id});pts.push(s0,e)})});
  var mk=(i,at,c,g,tip)=>{var v=M(at);if(i==null||isNaN(v))return;mks.push({i:i,t:v,c:c,g:g,tip:tip});pts.push(v)};
  ev.forEach(e=>{var ty=e.type;
    if(ty==="job.verify_failed")mk(own(RI,e.job),e.at,"k-failed","✕","Verify failed for "+e.job+(e.count?" ("+e.count+")":"")+"\n"+e.command+", exit "+e.exit_code);
    else if(ty==="review.completed")mk(own(RI,e.job),e.at,"k-"+(VC[e.verdict]||"pending"),/^c/.test(e.verdict)?"✕":"✓",e.job+" on "+e.target+": "+e.verdict+"\n"+[e.provider,e.model].filter(Boolean).join(" "));
    else if(ty==="decision"||ty==="amendment")mk(own(RI,e.job)!=null?RI[e.job]:0,e.at,"k-parked","◆",(ty==="decision"?"Decision"+(e["class"]?" ("+e["class"]+")":""):"Amendment "+(e.id||""))+" by "+e.by+"\n"+e.summary);
    else if(/^(spec|plan)\.approved$/.test(ty))mk(0,e.at,"k-gate","◆",SP(e)+" approved by "+e.by);
    else if(/^task\.(finished|abandoned)$/.test(ty))mk(0,e.at,"k-gate","◆",ty==="task.finished"?"Task finished":"Task abandoned: "+e.reason)});
  var ph=[["shaping",t0]],PH={"spec.approved":"planning","execution.started":"executing"},fin=ev.filter(e=>/^task\.(finished|abandoned)$/.test(e.type)).pop();
  ev.forEach(e=>{var p=PH[e.type];if(p&&ph[ph.length-1][0]!==p){ph.push([p,M(e.at)]);pts.push(M(e.at))}});
  // clusters of activity; a gap longer than GAP becomes a fixed-width break
  var GAP=Math.max(15*6e4,(tEnd-t0)/24),iv=bars.map(b=>[b.s,b.e]).concat(pts.map(v=>[v,v])).filter(v=>!isNaN(v[0])).sort((a,b)=>a[0]-b[0]),cl=[];
  iv.forEach(v=>{var c=cl[cl.length-1];if(c&&v[0]-c[1]<=GAP)c[1]=Math.max(c[1],v[1]);else cl.push([v[0],v[1]])});
  var mob=W.innerWidth<=860,LW=mob?112:176,avail=Math.max(200,Math.min(($("#main").clientWidth||1200)-(mob?32:48),1280)-LW-3),
   // one time scale k (px per minute) for every cluster; a short cluster keeps a minimum width
   GW=24,MW=56,PD=6,PX=8,ng=cl.length-1,wOf=k=>cl.reduce((v,c)=>v+Math.max(MW,(c[1]-c[0])/6e4*k+2*PD),0),lo=0,hi=1e4,k,seg=[],x=PX,
   // narrow screens and crowded tasks get a wider chart that scrolls, never bars squeezed to nothing
   room=Math.max(Math.max(avail,760)-2*PX-ng*GW,wOf(0)*1.6);
  for(var n=0;n<50;n++){var m=(lo+hi)/2;if(wOf(m)>room)hi=m;else lo=m}k=lo;
  cl.forEach((c,q)=>{var w=Math.max(MW,(c[1]-c[0])/6e4*k+2*PD);seg.push({a:c[0],b:c[1],x:x,w:w});x+=w;if(q<ng){seg.push({a:c[1],b:cl[q+1][0],x:x,w:GW,gap:1});x+=GW}});
  var Wd=Math.round(Math.max(avail,x+PX)),ROW=24,TOP=54,H=TOP+rows.length*ROW,o=[],lab={1:[],2:[]},
   X=v=>{for(var q=0;q<seg.length;q++){var g=seg[q];if(v<=g.b||q===seg.length-1)return v<g.a?g.x+(g.gap?0:PD):g.gap?g.x+(v-g.a)/(g.b-g.a)*g.w:g.x+PD+Math.min(v-g.a,g.b-g.a)/6e4*k}return PX},
   R=v=>Math.round(v*10)/10,txt=(x,y,c,s,a)=>'<text x="'+R(x)+'" y="'+y+'"'+(c?' class="'+c+'"':"")+(a?' text-anchor="'+a+'"':"")+">"+esc(s)+"</text>",
   put=(r,x0,w,html)=>{if(lab[r].some(l=>x0<l[1]+8&&x0+w>l[0]-8))return false;lab[r].push([x0,x0+w]);if(html)o.push(html);return true},
   tw=s=>s.length*6.6;
  seg.forEach(g=>{if(g.gap){var c=g.x+GW/2;o.push('<rect class="gp" x="'+R(g.x)+'" y="24" width="'+GW+'" height="'+(H-24)+'"/><g data-tip="'+esc("No activity for "+span((g.b-g.a)/6e4)+"\n"+fmt(new Date(g.a).toISOString())+" → "+fmt(new Date(g.b).toISOString()))+'"><rect x="'+R(g.x)+'" y="24" width="'+GW+'" height="'+(TOP-24)+'" fill="transparent"/><path class="brk" d="M'+R(c-4)+" 44l4-9M"+R(c)+" 44l4-9"+'"/></g>');put(1,c-5,10);put(2,c-5,10)}});
  rows.forEach((r,i)=>o.push('<line class="rl" x1="0" x2="'+Wd+'" y1="'+(TOP+i*ROW+.5)+'" y2="'+(TOP+i*ROW+.5)+'"/>'));
  // phase bands across the top
  ph.forEach((p,q)=>{var a=X(p[1]),b=q<ph.length-1?X(ph[q+1][1]):X(fin?M(fin.at):tEnd);
    o.push('<g class="p-'+p[0]+'"><line class="pl" x1="'+R(a)+'" x2="'+R(Math.max(a+2,b))+'" y1="19" y2="19"/>'+(b-a>tw(p[0])+6||q===ph.length-1?txt(a,13,"pt",p[0]):"")+"</g>");
    if(q)o.push('<line class="pb" x1="'+R(a)+'" x2="'+R(a)+'" y1="14" y2="'+H+'"/>')});
  // axis: times on the lower row (every cluster start first, then round times inside long clusters), dates above them where the day changes
  var step=[5,10,15,30,60,120,180,360,720,1440].map(v=>v*6e4).find(v=>v/6e4*k>=90)||864e5,tz=new Date(t0).getTimezoneOffset()*6e4,tk=[],shown=[],day="";
  seg.forEach(g=>{if(g.gap)return;tk.push([g.a,1]);if(k)for(var v=Math.ceil((g.a-tz)/step)*step+tz;v<g.b;v+=step)if(X(v)-X(g.a)>40&&X(g.b)-X(v)>8)tk.push([v,2])});
  tk.sort((a,b)=>a[1]-b[1]||a[0]-b[0]).forEach(p=>{var d=new Date(p[0]),s1=pad(d.getHours())+":"+pad(d.getMinutes()),x0=X(p[0]);
    if(put(2,x0+3,tw(s1),txt(x0+3,46,"",s1)))shown.push([p[0],x0]);o.push('<line class="tk" x1="'+R(x0)+'" x2="'+R(x0)+'" y1="'+(TOP-5)+'" y2="'+TOP+'"/>')});
  shown.sort((a,b)=>a[0]-b[0]).forEach(p=>{var d=new Date(p[0]),ds=d.toDateString(),s1=d.toLocaleDateString("en",{month:"short",day:"numeric"});if(ds!==day&&put(1,p[1]+3,tw(s1),txt(p[1]+3,32,"dl",s1)))day=ds});
  if(live)o.push('<line class="now" x1="'+R(X(now))+'" x2="'+R(X(now))+'" y1="24" y2="'+H+'"/>');
  // rows: bars per attempt, then markers
  rows.forEach((r,i)=>{var y=TOP+i*ROW,b=bars.filter(v=>v.i===i),ends=[];
    o.push('<g class="gr'+(r.id&&S.job===r.id?" sel":"")+'" data-row="'+esc(r.id)+'"'+(r.id?dataJ("job",r.id):"")+'><rect class="rb" x="0" y="'+(y+1)+'" width="'+Wd+'" height="'+(ROW-1)+'"/>');
    b.forEach(v=>{var x0=X(v.s),x1=Math.max(x0+3,X(v.e)),a=v.a,sm=v.tail?staleM(t,v.id):0,
      tip=v.id+" #"+a.n+" · "+v.st+"\n"+[model(a),a.harness&&a.harness+" "+tierOf(a)].filter(Boolean).join(" · ")+"\n"+fmt(a.started)+" → "+(v.st==="running"&&!sm?"now":fmt(new Date(v.e).toISOString()))+(a.duration_s?" · "+dur(a.duration_s):"")+(a.tokens?" · "+num(a.tokens)+" tokens":"")+(sm?"\nNo activity for "+span(sm)+". "+staleTip(t,v.id):"");
      ends.push(x1);o.push('<g class="k-'+v.st+'" data-tip="'+esc(tip)+'"><rect class="ab" x="'+R(x0)+'" y="'+(y+8)+'" width="'+R(x1-x0)+'" height="9" rx="2"/>'+(v.tail?'<line class="dt" x1="'+R(x1+3)+'" x2="'+R(Math.max(x1+3,X(v.tail)))+'" y1="'+(y+12.5)+'" y2="'+(y+12.5)+'"/><rect x="'+R(x1)+'" y="'+(y+4)+'" width="'+R(Math.max(4,X(v.tail)-x1))+'" height="17" fill="transparent"/>':"")+"</g>")});
    var used=[];mks.filter(m=>m.i===i).sort((a,b)=>a.t-b.t).forEach(m=>{var x0=X(m.t);ends.forEach(e=>{if(x0>e-6&&x0<e+6)x0=e+7});while(used.some(u=>Math.abs(u-x0)<10))x0+=10;used.push(x0);
      o.push('<g data-tip="'+esc(m.tip+"\n"+fmt(new Date(m.t).toISOString()))+'"><rect x="'+R(x0-6)+'" y="'+(y+4)+'" width="12" height="17" fill="transparent"/>'+txt(x0,y+16.5,"mk "+m.c,m.g,"middle")+"</g>")});
    o.push("</g>")});
  var L='<div class="gtl"><div class="gth" style="height:'+TOP+'px">Job</div>'+rows.map(r=>r.id?'<button class="gtr'+(r.d?" sub":"")+(S.job===r.id?" sel":"")+'" data-row="'+esc(r.id)+'"'+dataJ("job",r.id)+' title="'+esc(r.id)+'">'+esc(r.id)+"</button>":'<div class="gtr tk" data-row="">task</div>').join("")+"</div>";
  var lg=["done","running","parked","failed"].map(v=>'<span class="k-'+v+'"><i class="lsw"></i> '+v+"</span>").join("")+'<span><b class="lg k-failed">✕</b> verify failed</span><span><b class="lg k-done">✓</b> review</span><span><b class="lg k-parked">◆</b> decision</span><span><b class="lg k-gate">◆</b> approval</span>';
  return'<div class="gh"><h2 class="lbl">Jobs over time</h2><div class="legend">'+lg+'</div></div><div class="gt">'+L+'<div class="gts"><svg class="gx" width="'+Wd+'" height="'+H+'" viewBox="0 0 '+Wd+" "+H+'" role="img" aria-label="Jobs over time">'+o.join("")+"</svg></div></div>"}
TAB.timeline=t=>{var ap=changes(t).ap,ph="shaping",G={},order=[],P={"spec.approved":"planning","execution.started":"executing","task.finished":"done","task.abandoned":"abandoned"};
  var ev=(t.events||[]).map((e,i)=>({e:e,p:ph=P[e.type]||ph,i:i})),cnt=f=>f==="all"?ev.length:ev.filter(x=>FT[f].test(x.e.type)).length;
  var sel=ev.filter(x=>S.f==="all"||FT[S.f].test(x.e.type)).reverse();sel.forEach(x=>{if(!G[x.p]){G[x.p]=[];order.push(x.p)}G[x.p].push(x)});
  var gt=gantt(t),out=(gt?gt+'<div class="sec">':"<div>")+'<div class="gh"><h2 class="lbl">Events</h2><div class="seg" role="radiogroup" aria-label="Filter events">'+FILTERS.map(f=>'<button role="radio" aria-checked="'+(S.f===f[0])+'" data-act="filter" data-f="'+f[0]+'">'+f[1]+"<i>"+cnt(f[0])+"</i></button>").join("")+"</div></div></div>";
  if(!sel.length)return out+empty(ev.length?"No events of this kind.":"No events.");
  return out+order.map(p=>sec('<i class="pd p-'+p+'" aria-hidden="true">'+(p==="done"?"✓":p==="abandoned"?"–":"")+"</i>"+p,'<div class="box">'+G[p].map(x=>{var e=x.e,pva=ap>=0&&x.i>ap&&FT.graph.test(e.type)&&e.by!=="sae"&&!(e.type==="job.added"&&e.kind==="review");
    return'<div class="ev'+(pva?" pva":"")+'"><span class="ink2" title="'+esc(e.at)+'">'+esc(fmt(e.at))+'</span><span class="mono ty '+fam(e.type)+'">'+esc(e.type)+"</span>"+(x=>'<span class="et" title="'+x.replace(/<[^>]+>/g,"")+'">'+x+"</span>")(evText(t,e))+"<span>"+(pva?'<span class="tag">planned vs actual</span>':"")+"</span></div>"}).join("")+"</div>",plural(G[p].length,"event"))).join("")};
var rsn=e=>e.reason?' <span class="ink2">— '+esc(e.reason)+"</span>":"",
 vv=v=>esc(Array.isArray(v)?"["+v.join(", ")+"]":v),
 chg=(c,sep)=>Object.keys(c).map(k=>code(k)+" "+vv(c[k][0])+" → "+vv(c[k][1])).join(sep),
 SP=e=>e.type[0]==="s"?"Spec":"Plan",
 EV={"task.created":e=>"Task created by "+esc(e.author)+(e.from?" from "+code(e.from.file):""),
  "backlog.created":e=>"Backlog item "+code(e.file),
  "spec.checked":e=>SP(e)+" check: "+plural(e.errors||0,"error")+", "+plural(e.warnings||0,"warning"),
  "settings.changed":e=>"Settings changed "+(e.by==="external"?"in the file":e.by==="viewer"?"in the viewer":"with sae set")+": "+chg(e.changes||{},", "),
  "spec.approved":e=>SP(e)+" approved by "+esc(e.by),
  "job.added":(e,t)=>"Added "+J(e.job)+" ("+esc(e.kind)+(e.difficulty?", "+esc(e.difficulty):"")+")"+(e.needs&&e.needs.length?", needs "+e.needs.map(J).join(", "):"")+(e.target?", target "+tgt(t,e.target):"")+rsn(e),
  "job.changed":e=>"Changed "+J(e.job)+": "+chg(e.changes||{},"; ")+rsn(e),
  "job.removed":e=>"Removed "+J(e.job)+rsn(e),
  "execution.started":e=>"Execution "+(e.resumed?"resumed":"started")+(e.branch?" on "+code(e.branch):"")+", layout "+esc(e.layout),
  "job.dispatched":e=>"Dispatched "+J(e.job)+" #"+esc(e.attempt)+" → "+code(model(e))+' <span class="mut">'+esc(e.harness+" "+tierOf(e))+"</span>"+rsn(e),
  "job.collected":e=>"Collected "+J(e.job)+" #"+esc(e.attempt)+": "+esc(e.status)+(e.summary?" — "+esc(e.summary):"")+(e.tokens?' <span class="mut">· '+num(e.tokens)+" tokens</span>":""),
  "job.verify_failed":e=>"Verify failed for "+J(e.job)+(e.count?" ("+e.count+")":"")+": "+code(e.command)+", exit "+esc(e.exit_code),
  "job.scope_warning":e=>J(e.job)+" changed files outside its scope: "+(e.files||[]).map(code).join(", "),
  "job.merged":e=>"Merged "+J(e.job)+" "+code(e.commit),
  "merge.conflict":e=>"Merge conflict in "+J(e.job)+": "+(e.files||[]).map(code).join(", ")+" → "+J(e.integration_job),
  "review.completed":(e,t)=>J(e.job)+" on "+tgt(t,e.target)+": "+vpill(e.verdict)+' <span class="mut">'+esc(e.provider||"")+"</span> "+code(e.model),
  decision:e=>"Decision"+(e["class"]?" ("+esc(e["class"])+")":"")+" by "+esc(e.by)+": "+esc(e.summary)+(e.job?" · "+J(e.job):""),
  amendment:e=>"Amendment "+code(e.id)+" by "+esc(e.by)+": "+esc(e.summary),
  note:e=>esc(e.text)+(e.job?" · "+J(e.job):""),
  "finding.created":e=>"Finding "+code(e.finding),
  "task.finished":e=>"Task finished"+(e.branch?" on "+code(e.branch):"")+(e.commit?" @ "+code(e.commit):""),
  "task.abandoned":e=>"Abandoned: "+esc(e.reason),
  "hold.set":e=>"Hold after "+J(e.job)+" set"+(e.by==="viewer"?" in the viewer":"")+rsn(e),
  "hold.released":e=>"Hold after "+J(e.job)+" released"+(e.by==="viewer"?" in the viewer":""),
  "override.set":e=>"Override for "+code(e.job)+": "+esc([e.harness,e.model,e.effort].filter(Boolean).join(" · "))+(e.by==="viewer"?" (in the viewer)":"")+rsn(e),
  "override.cleared":e=>"Override for "+code(e.job)+" cleared"+(e.by==="viewer"?" (in the viewer)":"")+rsn(e)};
EV["plan.checked"]=EV["spec.checked"];EV["plan.approved"]=EV["spec.approved"];
var evText=(t,e)=>(EV[e.type]||(e=>esc(JSON.stringify(e))))(e,t);
TAB.reviews=t=>{var js=JS(t),ids=jf(t,j=>j.kind==="review");if(!ids.length)return empty("No reviews yet.");
  return box(ids.map(id=>{var j=js[id],txt=t.files["reviews/"+id+".md"],fs=[];
    if(txt)stripC(front(txt)[1]).replace(/^###\s+(\d+)\.\s+(.*?)(?:\s+[—-]\s+(blocking|major|minor))?\s*$/gm,(_,n,ti,sv)=>{fs.push("<div>"+n+". "+inl(ti)+(sv?' <span class="tag">'+esc(sv)+"</span>":"")+"</div>")});
    return row("fv",stp(t,id),code(id)+' <span class="ink2">on '+esc(j.target)+(j.round?" · round "+j.round:"")+"</span>",byM(lastA(j)),fs.join("")||(txt?"No numbered findings.":"No review file yet."),id)}))};
TAB.decisions=t=>{var js=JS(t),dj=jf(t,j=>j.kind==="decision"),ev=evs(t,FT.decisions).reverse(),d=s=>esc(s||"–");
  return sec("Decision jobs",dj.length?tbl("","ID,For,Status,Question or decision",dj.map(k=>{var j=js[k],q=js[j.target]?ask(t,j.target):"";return tr([["mono nw",esc(k)],["mono nw",esc(j.target)],["nw",jpill(t,k)],["w",j["class"]?esc(j.decision)+' <span class="mut">· '+esc(j["class"])+" · "+esc(j.recommendation)+"</span>":'<span class="ink2">'+(q||"–")+"</span>"]],' class="r1'+(S.job===k?" open":"")+'"'+dataJ("job",k)+' tabindex="0"')})):box([],"No decision jobs."))+
   drafts()+sec("Decisions and amendments",ev.length?tbl("","When,Type,Class,By,Summary",ev.map(e=>tr([["ink2 nw",esc(fmt(e.at))],esc(e.type)+" "+code(e.id),d(e["class"]),'<span class="tag">'+d(e.by)+"</span>",["w",esc(e.summary)+(e.job?" · "+J(e.job):"")]]))):box([],"No decisions or amendments logged."))};
// [VIEWER-DECISIONS-AND-PROTOTYPES]: decision-record drafts of the repository (.tasks/adr/), readable here
function drafts(){var L=IDX.drafts||[];return sec("Decision-record drafts",L.length?'<div class="box docs">'+L.map(d=>dt("a:"+d.file,d.title,'<p class="mut mono">'+esc(d.file)+(d.type?" · "+esc(d.type):"")+" · "+esc(d.status||"proposed")+(d.source?" · from "+esc(slug(d.source)):"")+"</p>"+md(d.text,{meta:false}))).join("")+"</div>":box([],"No drafts in .tasks/adr/."),IDX.open_drafts?IDX.open_drafts+" open":"")}
var protos=t=>(t.prototypes||[]).length?sec("Prototypes",'<div class="box">'+t.prototypes.map(p=>'<div class="row two"><a class="mono" href="'+esc(p.url)+'" target="_blank" rel="noopener">'+esc(p.path.replace(/^prototypes\//,""))+'</a><span class="r">'+esc(num(p.size))+" B</span></div>").join("")+"</div>","open in a new tab"):"";
TAB.spec=t=>{var f=t.files,has=[["intent","intent.md"],["spec","specs.md"]].filter(d=>f[d[1]]!=null);if(!has.length)return protos(t)+empty("No intent.md.");
  var d=(has.find(x=>x[0]===S.doc)||has[has.length-1]),am=evs(t,/^amendment$/).length;
  var rv=reviewsOf(t,"spec").map(k=>"<span>Spec review "+J(k)+" "+stp(t,k)+" "+byM(lastA(JS(t)[k]))+"</span>").join("");
  return'<div class="gh"><div class="seg" role="radiogroup" aria-label="Document">'+has.map(x=>'<button role="radio" aria-checked="'+(d===x)+'" data-act="doc" data-d="'+x[0]+'">'+x[1]+"</button>").join("")+'</div><div class="legend">'+(rv||"<span>No spec review.</span>")+(am?"<span>"+plural(am,"amendment")+"</span>":"")+"</div></div>"+
    protos(t)+'<div class="sec">'+md(f[d[1]],{amend:true})+"</div>"};
TAB.findings=()=>{var fs=IDX.findings||[],cr=String(IDX.closed_findings||"").split(/\r?\n/).filter(l=>/^\s*-\s/.test(l)).map(l=>{var p=l.replace(/^\s*-\s*/,"").split(" · ");return p.length>3?[p[0],p[1],p.slice(2,-1).join(" · "),p[p.length-1]]:["","",p.join(" · "),""]}).reverse();
  return sec("Open findings",fs.length?tbl("","Type,Title,Source,Confidence,Filed",fs.map(f=>{var op=S.job==="f:"+f.file;
    return tr(['<span class="tag">'+esc(f.type||"–")+"</span>",["w",esc(f.title)],["mono ink2 nw",esc(f.source?slug(f.source):"–")],["ink2",esc(f.confidence||"–")],["ink2 nw",agoH(f.created)]],' class="r1'+(op?" open":"")+'"'+dataJ("row","f:"+f.file)+' tabindex="0" aria-expanded="'+op+'"')+
      (op?'<tr><td colspan="5" class="xd"><p class="mono mut">'+esc(f.file)+"</p>"+md(f.text)+"</td></tr>":"")})):box([],"No open findings."))+
   sec("Closed",cr.length?tbl("","Title,Outcome,Closed",cr.map(c=>tr([["ink2 w",esc(c[2])],["ink2",esc(c[3])],["mut nw",esc(c[0])]]))):box([],"No closed findings."))};
function jobBody(t,id){var js=JS(t),j=own(js,id),f=t.files;
  if(!j){var g=own(changes(t).r.removed,id)||{},rf="jobs/"+id+".removed.md";return dl([["Status",pill("removed")],["Reason",esc(g.reason)]])+(f[rf]!=null?docs("j:",[rf],f):"")}
  var rs=reviewsOf(t,id),dj=jf(t,o=>o.kind==="decision"&&o.target===id),out=dl([["Status",jpill(t,id)],["Summary",esc(j.summary)],["Decision request",j.status==="parked"&&ask(t,id)],["Waits for",j.status==="pending"&&esc(waits(t,id).join(", "))],
    ["Needs",j.needs.map(J).join(", ")],["Target",j.target&&tgt(t,j.target)],["Fix of",J(j.fix_of)],["Reviews",rs.map(k=>J(k)+" "+stp(t,k)).join(" ")],["Decision jobs",dj.map(J).join(", ")],["Hold",dead(t)?"":(own(holdsOf(t),id)?'<span class="tag">⏸ '+(holdOn(t,id)?"hold active":"hold after this job")+"</span> ":"")+holdBtn(t,id)],["Commits",(j.commits||[]).map(c=>code(c.slice(0,7))).join(" ")],["Last change",agoH(j.last_change)]].map(p=>[p[0],p[1]||""]));
  if(j.attempts.length)out+=sec("Attempts",tbl("nw","~#,Model,Harness,Started,~Duration,~Tokens,Reason",j.attempts.map(a=>tr([["n",a.n],["mono",esc(model(a))],esc(a.harness+" "+tierOf(a)),["ink2",esc(fmt(a.started))],["n",esc(dur(a.duration_s)||(a.ended?"–":"running"))],["n",a.tokens?num(a.tokens):"–"],esc(a.reason||"")]))));
  var dd=[...new Set(["jobs/"+id+".md",resultPath(id,j),"jobs/"+id+".verify.log"].concat(dj.map(k=>"decisions/"+k+".md")))].filter(d=>f[d]!=null);
  return out+sec("Files",dd.length?docs("j:",dd,f):box([],"No files yet."))}
