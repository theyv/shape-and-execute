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
 canOvr=(t,id)=>!dead(t)&&(!!PLo(t,id)||t.planned_planner===id||(JO(t,id)||{}).status==="pending"),
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

/* ---------- graph cards ([DECISION-STACK-CARDS]): Shape and Plan, job cards with their review and fix rows, one
   Integration card, Finish. The cards are a model first (graph().cards), then SVG; the CSS holds colors and timings ---------- */
// sizes in px (FB, FBS: how far below the cards feedback edges run, and their spacing); character widths: CH mono 12px, CM the model labels' mono 11px, CS sans 12px, CP a status pill's,
// CV a verdict badge's (11px). The owner tunes these in a live viewer.
var GC={NW:240,HH:68,L4:22,RH:24,RS:10,GX:40,GY:16,P:20,DH:8,FB:14,FBS:6,CH:7.3,CM:6.7,CS:6.6,CP:6.4,CV:5.9},
 // card IDs no job ID can take (job IDs are upper case and start with a letter)
 PC={shape:"@shape",plan:"@plan",jobs:"@jobs",integration:"@integration",finish:"@finish"},
 RULE="A row is a review round or a fix job of its card.\nA review lives in the card of what it reviews; the integration review reviews the whole task, so it has the Integration card.\n"+
  "◌ planned · ○ pending · ▷ ready · ◐ running · ● done · ‖ parked · ✕ failed\n✕ changes required: red while open, grey once a later round passed\n✓ pass, or pass with notes",
 ORD=n=>n+(n%100>10&&n%100<14?"th":["th","st","nd","rd"][n%10]||"th"),
 tkT=n=>n<1e3?n+" tk":n<1e6?Math.round(n/1e3)+"k tk":(n/1e6).toFixed(1).replace(/\.0$/,"")+"M tk",
 tmT=s=>s<60?Math.round(s)+"s":s<3600?Math.round(s/60)+"m":Math.floor(s/3600)+"h "+Math.round(s%3600/60)+"m",
 // tokens · time of the jobs' attempts; a number nobody recorded is left out ([EDGE-OLD-TASKS])
 spent=(t,ids)=>{var k=0,d=0;ids.forEach(id=>((JO(t,id)||{}).attempts||[]).forEach(a=>{k+=a.tokens||0;d+=a.duration_s||0}));return[k&&tkT(k),d&&tmT(d)].filter(Boolean).join(" · ")},
 runFor=(t,id)=>{var a=lastA(JO(t,id)||{}),m=a&&mins(a.started);return m>=0?"running for "+span(m):"running"},
 // title and objective from the job file, for the card tooltip ([GRAPH-TOOLTIPS])
 jobDoc=(t,id)=>{var f=t.files&&t.files["jobs/"+id+".md"];if(f==null)return{};var b=stripC(front(f)[1]),h=/^#\s+(.*)$/m.exec(b),o=section(b,"Objective"),ti=h?h[1].trim():"";
  if(ti.indexOf(id+":")===0)ti=ti.slice(id.length+1).trim();return{title:ti,obj:o?trunc(o.trim().split(/\r?\n\s*\r?\n/)[0].replace(/\s+/g," "),320):""}},
 // a status pill: [svg, width]; x is its right edge (end) or its left edge
 gpill=(x,y,h,k,txt,end,v)=>{var w=Math.round(txt.length*(v?GC.CV:GC.CP)+14);return['<g class="sp k-'+k+(v?" v":"")+'" transform="translate('+(end?x-w:x)+","+y+')"><rect width="'+w+'" height="'+h+'" rx="4"/><text x="7" y="'+(h-6)+'">'+esc(txt)+"</text></g>",w]},
 accepted=(t,id)=>{var p="merge "+id+" despite review: ",e=(t.events||[]).filter(e=>e.type==="decision"&&e.job===id&&String(e.summary||"").indexOf(p)===0).pop();return e?e.summary.slice(p.length):null},
 // [WAIT-FRAMES]: a card whose job or row is parked gets the red frame (WAIT-SIGNALS adds the cards an open ask names)
 waitFrame=c=>c.st.k==="parked";

var preExec=(t,id)=>{var j=JS(t)[id];return j.kind==="review"?/^(spec|plan)$/.test(j.target):/^(research|planning)$/.test(j.kind)&&!j.needs.length&&!jf(t,o=>o.needs.includes(id)).length};
// the card of each job: a review or fix row lives in the card of what it reviews; spec and plan reviews, shaping
// research and the planner in the phase cards; every integration round and its fixes in the Integration card
function homes(t){var js=JS(t),ev=t.events||[],at={},sa=-1,ph=t.state.task.phase,H={};
  ev.forEach((e,i)=>{if(e.type==="job.added"&&at[e.job]==null)at[e.job]=i;if(e.type==="spec.approved"&&sa<0)sa=i});
  // shaping research: added before the spec was approved (control.shaping_research); old tasks without events: today's rule
  var shapeR=id=>at[id]==null?preExec(t,id):sa<0?/^(shaping|planning)$/.test(ph)||preExec(t,id):at[id]<sa,
   h=(id,d)=>{if(H[id])return H[id];var j=js[id],r=id;if(!j||d>6)return id;
    if(j.kind==="review")r=j.target==="spec"?PC.shape:j.target==="plan"?PC.plan:j.target==="integration"?PC.integration:js[j.target]&&j.target!==id?h(j.target,d+1):id;
    else if(j.fix_of&&js[j.fix_of]&&j.fix_of!==id)r=h(j.fix_of,d+1);
    else if(j.kind==="planning")r=PC.plan;
    else if(j.kind==="research"&&shapeR(id))r=PC.shape;
    return H[id]=r};
  Object.keys(js).forEach(id=>h(id,0));return{of:id=>H[id]||id,at:at}}

// the rows of a card in order of creation; planned reviews last (after a fix, the server plans the next round).
// settled: the phase gate is approved, so a changes-required spec or plan review was answered (grey, not red)
function rowsOf(t,ids,at,settled){var js=JS(t),acc=null,
   kindOf=id=>{var j=js[id]||{kind:"review"};return j.kind==="review"?"review":j.kind==="research"?"research":"fix"},
   // research first (the Shape card), then by creation; planned reviews do not exist yet
   rs=ids.filter(id=>js[id]).sort((a,b)=>(kindOf(a)==="research"?0:1)-(kindOf(b)==="research"?0:1)||(at[a]==null?1e9:at[a])-(at[b]==null?1e9:at[b])||ids.indexOf(a)-ids.indexOf(b)).concat(ids.filter(id=>!js[id])),L=rs.map(id=>({id:id,k:kindOf(id),planned:!js[id]}));
  var n={},c={};L.forEach(r=>{n[r.k]=(n[r.k]||0)+1});
  L.forEach((r,i)=>{var w={review:"Review",fix:"Fix",research:"Research"}[r.k];c[r.k]=(c[r.k]||0)+1;r.label=n[r.k]>1?w+" "+c[r.k]:w;
    var j=js[r.id],s=j?stOf(t,r.id):"planned";r.s=s;
    // ✕ changes required: grey once a later round of the card passed
    var later=L.slice(i+1).some(x=>x.k==="review"&&js[x.id]&&js[x.id].status==="done"&&/^pass/.test(js[x.id].verdict||""));
    if(j&&s==="done"&&j.kind==="review"&&j.verdict){r.v=j.verdict;if(/^pass/.test(j.verdict)){r.g="✓";r.tone="pass"}else{r.g="✕";r.fixed=later||!!settled;r.tone=r.fixed?"mut":"fail"}}
    else{r.g=r.planned?"◌":GL[s]||"○";r.tone=s}
    r.run=s==="running"});
  return L}

// one row's words: full job ID and state; tokens · time, or how long it runs; model · effort
function rowTip(t,r,x,card){var p=PLo(t,r.id),m=card&&markOf(t,card),
   st=r.planned?"planned":r.v?(/^pass/.test(r.v)?r.v.replace(/-/g," "):"changes required"+(r.fixed?", fixed":r.acc?", accepted":"")):r.s;
  return r.id+" · "+st+(r.planned?"":"\n"+(r.run?runFor(t,r.id):spent(t,[r.id])||"no tokens or time recorded"))+(x?"\n"+[x.h,x.m,x.e].filter(Boolean).join(" · ")+(x.ovr?" (override)":""):"")+
   (r.planned?"\nPlanned: sae adds "+(p&&p.round>1?"this round when "+(p.target==="integration"?"its fix jobs are merged":"the fix is done"):p&&p.target==="integration"?"this review when every writer job is merged":p&&/^(spec|plan)$/.test(p.target)?"this review when the "+p.target+" is ready for it":"this review when "+((p||{}).target||"its job")+" is done")+"."+
    (m&&m.forced&&m.reviewed?"\nForced by settings: "+m.reason+".":"")+(canOvr(t,r.id)?"\nClick the model to change it.":""):"")+(r.accReason?"\nMerged despite changes required: "+r.accReason:"")}

// model · effort, right-aligned at xr; a button when it can change ([JOB-MODEL-OVERRIDE])
function mlab(t,id,x,xr,y,room){if(!x)return"";var ed=canOvr(t,id),suf=(x.e?" · "+x.e:"")+(x.ovr?" · override":""),
   mt=trunc(x.m,Math.max(3,Math.floor(room/GC.CM)-suf.length)),w=Math.round((mt.length+suf.length)*GC.CM),
   lab='<tspan class="tm" style="--mc:'+mcol(t,x.h,x.m)+'">'+esc(mt)+"</tspan>"+(x.e?'<tspan> · </tspan><tspan class="te'+(x.e==="ultra"?" u":"")+'" style="--ec:'+effortColor(x.e)+'">'+esc(x.e)+"</tspan>":"")+(x.ovr?'<tspan class="to"> · override</tspan>':""),
   tip=x.ovr?"<b>Override for this job.</b><br>"+esc(x.h)+" · "+mwords(t,x)+(x.routed?"<br>Routing would pick "+esc(x.routed.harness)+" · "+mwords(t,{h:x.routed.harness,m:x.routed.model_entry,e:x.routed.effort}):"")+(ed?"<br>Click to change or clear it.":""):
    "<b>"+(x.ran?"Last attempt":x.next?"Routing of the next round":"Routing")+"</b>: "+esc(x.h)+" · "+mwords(t,x)+(srcText(x)?' <span class="mut">('+esc(srcText(x))+")</span>":"")+(ed?"<br>Click to run it on another model.":"");
  return'<g class="ml'+(ed?" ed":"")+'"'+(ed?' data-act="ovr" data-id="'+esc(id)+'" tabindex="0" role="button" aria-haspopup="dialog" aria-label="'+esc("Model of "+id+": "+[x.h,x.m,x.e].join(" · ")+(x.ovr?", override":"")+". Change")+'"':"")+' data-tiph="'+esc(tip)+'">'+
   '<rect class="hit" x="'+(xr-w-4)+'" y="'+(y-13)+'" width="'+(w+8)+'" height="18" rx="3"/><text class="nm" x="'+xr+'" y="'+y+'" text-anchor="end">'+lab+"</text></g>"}

// the verdict badge of a card with review rows: pass (in which round), changes required while no fix runs, accepted
function verdictOf(rows,fixing,acc){var rv=rows.filter(r=>r.k==="review"&&!r.planned),done=rv.filter(r=>r.v),last=rv[rv.length-1],ld=done[done.length-1];
  if(acc&&ld&&!/^pass/.test(ld.v)){ld.tone="park";ld.acc=1;return["accepted","◆ accepted"]}
  if(last&&last.v&&/^pass/.test(last.v))return["approved","✓ pass"+(rv.length>1?" · "+ORD(rv.length)+" round":"")];
  if(ld&&!/^pass/.test(ld.v)&&!fixing&&!ld.fixed)return["failed","✕ changes required"];
  return null}

/* the card models */
var ST={fixing:"◐",waiting:"○",approved:"✓",blocked:"‖",stopped:"–",planned:"◌"},
 stp1=(k,label)=>({k:k,text:((GL[k]||ST[k]||"")+" "+(label||k)).trim()}),
 stepsOf=(t,ph)=>(t.steps||[]).filter(s=>s.phase===ph),
 stepMark=s=>s.state==="done"?"✓":s.state==="current"?"►":/^(off|none)$/.test(s.state)?"–":"□",
 stepLine=L=>L.map(s=>s.name+" "+stepMark(s)+(s.note?" ("+s.note+")":"")).join(" · "),
 approval=(t,k)=>{var a=(t.state.task.approvals||{})[k],e=evs(t,new RegExp("^"+k+"\\.approved$"))[0];return a||e?{at:(a||e).at,by:(a||e).by}:null};
function phaseCard(t,which,rows){var info=t.state.task,ph=info.phase,js=JS(t),sh=which==="shape",ap=approval(t,sh?"spec":"plan"),
   ok=ap||(sh?/^(planning|executing|done)$/:/^(executing|done)$/).test(ph),cur=ph===(sh?"shaping":"planning"),
   st=ok?stp1("approved"):cur?stp1("running"):ph==="abandoned"?stp1("stopped"):stp1("waiting"),
   steps=stepsOf(t,sh?"shape":"plan"),planner=sh?null:jf(t,j=>j.kind==="planning")[0],ids=rows.filter(r=>!r.planned).map(r=>r.id).concat(planner?[planner]:[]),
   tk=spent(t,ids),c={id:sh?PC.shape:PC.plan,title:sh?"Shape":"Plan",kind:"phase",cls:["phase"],kc:sh?"var(--ph-s)":"var(--ph-p)",st:st,rows:rows,tk:tk,job:planner||null};
  if(sh){var S0=k=>{var s=steps.find(x=>x.key===k);return s?s.state==="done"?"✓":"–":ok?"✓":"–"};c.sub="intake "+S0("intake")+" · spec "+S0("spec")}
  else{c.sub="planner";var pst=steps.find(x=>x.key==="planner");
    if(planner){c.x=modelOf(t,planner);c.xid=planner}else if(t.planned_planner){c.x=modelOf(t,t.planned_planner);c.xid=t.planned_planner}
    else if(pst&&pst.state==="none")c.r3="planned inline"}
  if(tk)c.l3="subagents only";
  if(!ok&&!cur&&ph!=="abandoned")c.cls.push("nyet");
  c.tip=c.title+" — "+st.text+"\n"+(sh?"From your note to an approved spec.":"The job graph, from the approved spec.")+
   (ap?"\nApproved"+(ap.by?" by "+ap.by:"")+(ap.at?" on "+fmt(ap.at):"")+".":"")+(steps.length?"\nSteps: "+stepLine(steps):"")+
   (sh?"\nIntake and spec: written in the main session.":planner?"\nPlanner: "+planner+(spent(t,[planner])?" · "+spent(t,[planner]):""):c.xid?"\nPlanner: "+c.xid+", planned; click its model to change it.":c.r3?"\nPlanned inline: no planner job.":"")+
   (tk?"\nSubagent tokens: "+tk+" (subagents only; the main session is not counted).":"")+(rows.length?"\nThe rows below are its subagent jobs; click one to open it.":"");
  return c}
function jobCard(t,id,rows,ch){var js=JS(t),j=js[id],s=stOf(t,id),live=rows.filter(r=>!r.planned).map(r=>js[r.id]),
   fixing=rows.some(r=>r.k==="fix"&&!r.planned&&js[r.id].status==="running"),
   k=live.some(r=>r.status==="parked")?"parked":live.some(r=>r.status==="failed")?"failed":fixing?"fixing":s,
   ar=j.merged&&accepted(t,id),v=rows.length?verdictOf(rows,fixing,ar!=null&&ar!==false):null,mk=ch.added[id]!=null?"added":ch.changed[id]!=null?"changed":"",
   sm=staleM(t,id),rm=markOf(t,id),hasRev=rows.some(r=>r.k==="review"),doc=jobDoc(t,id),
   sub=j.kind+(/^(review|decision)$/.test(j.kind)?" → "+(j.target||""):j.difficulty?" · "+j.difficulty:""),
   c={id:id,job:id,title:id,kind:"job",cls:[],kc:"var(--kd-"+j.kind+")",st:stp1(k),rows:rows,sub:sub,tk:s==="running"?"":spent(t,[id]),
    x:modelOf(t,id),xid:id,v:v,merged:j.merged,l3:[mk==="changed"&&"changed",sm&&"no activity "+span(sm)].filter(Boolean).join(" · ")};
  if(ar)rows.forEach(r=>{if(r.acc)r.accReason=ar});
  if(mk==="added")c.cls.push("added");if(mk==="changed")c.bar=1;if(s==="pending")c.cls.push("nyet");
  // review marks ([JOB-REVIEW-FLAG-HONESTY]): a review that will run is a row; a flagged job whose review will not run keeps its mark
  if(rm&&(!rm.reviewed||!hasRev))c.mark=rm;
  if(own(holdsOf(t),id))c.hold=own(holdsOf(t),id);
  c.tip=id+" — "+c.st.text.replace(/^\S+ /,"")+(s==="pending"&&waits(t,id).length?"\nWaits for: "+waits(t,id).join("; "):"")+(mk?"\n"+(mk==="added"?"Added":"Changed")+" after plan approval: "+(ch.added[id]||ch.changed[id]):"")+
   (sm?"\nNo activity for "+span(sm)+". "+staleTip(t,id):"")+(doc.title?"\n"+doc.title:"")+(doc.obj?"\nObjective: "+doc.obj:"")+(j.summary?"\nResult: "+j.summary:"")+(c.tk?"\n"+c.tk:"")+
   (rows.length?"\nIts reviews and fixes are the rows below; click a row to open that job.":"");
  return c}
function intCard(t,rows){var js=JS(t),live=rows.filter(r=>!r.planned).map(r=>js[r.id]),rv=rows.filter(r=>r.k==="review"&&!r.planned),
   fixing=rows.some(r=>r.k==="fix"&&!r.planned&&js[r.id].status==="running"),last=rv[rv.length-1],
   k=!live.length?"planned":live.some(r=>r.status==="parked")?"parked":live.some(r=>r.status==="failed")?"failed":fixing?"fixing":last?stOf(t,last.id):"pending",
   c={id:PC.integration,title:"Integration",kind:"integration",cls:[],kc:"var(--kd-review)",st:stp1(k),rows:rows,sub:"review → integration",tk:spent(t,live.map(r=>r.id).filter(Boolean)),v:verdictOf(rows,fixing,false)};
  if(!live.length){c.cls.push("planned","nyet");c.l3="after every writer is merged"}else if(k==="pending")c.cls.push("nyet");
  c.tip="Integration — "+c.st.text.replace(/^\S+ /,"")+"\nThe integration review checks the whole change once every writer job is merged.\nIts rounds and fixes are the rows below; click a row to open that job."+(c.tk?"\n"+c.tk:"");
  return c}
function finishCard(t){var ph=t.state.task.phase,f=t.finish||{state:ph==="done"?"done":ph==="abandoned"?"abandoned":"waiting"},s=f.state,
   fin=evs(t,/^task\.finished$/)[0],why=String(f.reason||"").split(/\r?\n/)[0],
   c={id:PC.finish,title:"Finish",kind:"finish",cls:["phase"],kc:"var(--line2)",rows:[],sub:"merge · final report",
    st:s==="abandoned"?stp1("stopped","abandoned"):stp1(s==="blocked"?"blocked":s==="ready"?"ready":s==="done"?"done":"waiting")};
  if(s==="done")c.st={k:"approved",text:"✓ done"};
  if(s==="waiting")c.cls.push("nyet");
  c.l3=s==="blocked"?why:s==="ready"?"its gates pass":s==="done"&&fin?"finished "+fmt(fin.at):"";
  c.tip="Finish — "+c.st.text.replace(/^\S+ /,"")+"\nsae finish: merge the rest, commit the task record, print the final report."+(s==="ready"?"\nEvery gate of sae finish passes.":"")+(f.reason?"\n"+f.reason:"");
  return c}

/* ---------- graph: layer = longest path from a root, barycenter order ---------- */
function graph(t){var js=JS(t),info=t.state.task,ph=info.phase,ch=changes(t).r,HM=homes(t),hm=HM.of,at=HM.at,ev=t.events||[],
   pls=planned(t),PL={},mem={},C={},has={},inc={},par={},E0=[],lay={},up={},dn={},cols=[],pos={},xy={},
   phome=p=>p.target==="spec"?PC.shape:p.target==="plan"?PC.plan:p.target==="integration"?PC.integration:js[p.target]?hm(p.target):null,
   cardOf=id=>js[id]?hm(id):PL[id]?phome(PL[id]):id,
   ghosts=Object.keys(ch.removed).filter(id=>!js[id]&&ch.removed[id].kind!=="review"),
   jc=Object.keys(js).filter(id=>hm(id)===id);
  pls.forEach(p=>{PL[p.id]=p;var c=phome(p);if(c)(mem[c]=mem[c]||[]).push(p.id)});
  Object.keys(js).forEach(id=>{var c=hm(id);if(c!==id&&!(c===PC.plan&&js[id].kind==="planning"))(mem[c]=mem[c]||[]).push(id)});
  var cards=[];
  cards.push(phaseCard(t,"shape",rowsOf(t,mem[PC.shape]||[],at,approval(t,"spec")||/^(planning|executing|done)$/.test(ph))),phaseCard(t,"plan",rowsOf(t,mem[PC.plan]||[],at,approval(t,"plan")||/^(executing|done)$/.test(ph))));
  if(!jc.length&&/^(shaping|planning)$/.test(ph))cards.push({id:PC.jobs,title:"Jobs",kind:"holder",cls:["holder","nyet"],kc:"var(--line2)",rows:[],st:stp1("waiting"),sub:"appear after planning",
   tip:"Jobs — not planned yet\nThe planner draws the jobs here once the plan is written."});
  jc.forEach(id=>cards.push(jobCard(t,id,rowsOf(t,mem[id]||[],at),ch)));
  ghosts.forEach(id=>cards.push({id:id,job:id,title:id,kind:"ghost",cls:["ghost"],kc:"var(--kd-"+ch.removed[id].kind+")",rows:[],st:stp1("removed"),sub:ch.removed[id].kind,
   tip:id+" — removed\nRemoved after plan approval: "+ch.removed[id].reason}));
  if((mem[PC.integration]||[]).length)cards.push(intCard(t,rowsOf(t,mem[PC.integration],at)));
  cards.push(finishCard(t));
  cards.forEach(c=>{C[c.id]=c;has[c.id]=1;var r4=c.mark||c.hold;c.hh=GC.HH+(r4?GC.L4:0);c.h=c.hh+(c.rows.length?GC.RS+c.rows.length*GC.RH:0);if(waitFrame(c))c.cls.push("wait")});
  // edges at job level: planner needs, edges sae generates ([GENERATED-JOB-EDGES]), targets, fixes; each end then moves to its card
  var JP=[],jp=(id,p,c)=>{if(p!==id)JP.push([p,id,c])},ints=Object.keys(js).filter(id=>js[id].kind==="review"&&js[id].target==="integration"),lastInt=ints[ints.length-1],
   rank={"":0,gen:1,tgt:2,pl:3},
   pa=(id,p,c,ja,jb)=>{if(!has[p]||!has[id]||p===id)return;var L=par[id]=par[id]||[],o=L.find(x=>x[0]===p);if(!o)L.push([p,c,ja,jb]);else if(rank[c]<rank[o[1]]){o[1]=c;o[2]=ja;o[3]=jb}},
   eg=(a,b,c,tip)=>{if((inc[b]||[]).includes(a))return;E0.push([a,b,c,tip]);(inc[b]=inc[b]||[]).push(a)};
  Object.keys(js).forEach(id=>{var j=js[id],gen=j.generated?j.needs:(j.generated_needs||[]);
    j.needs.forEach(n=>jp(id,n,gen.includes(n)?"gen":""));
    if(/^(decision|review)$/.test(j.kind)&&js[j.target])jp(id,j.target,"tgt");
    if(j.fix_of)jp(id,j.fix_of,"gen");
    // a task of the old sae added the integration review without needs: it follows the writers added before it
    if(j.kind==="review"&&j.target==="integration"&&!j.needs.length)Object.keys(js).filter(k=>WR[js[k].kind]&&!(at[k]>at[id])).forEach(k=>jp(id,k,"gen"));
    if(j.final&&lastInt)jp(id,lastInt,"gen")});
  pls.forEach(p=>{(p.needs||[]).forEach(n=>jp(p.id,n,"pl"));(p.needed_by||[]).forEach(k=>jp(k,p.id,"pl"))});
  JP.forEach(e=>pa(cardOf(e[1]),cardOf(e[0]),e[2],e[0],e[1]));
  // card cycles: rows in cards can close a cycle that the job graph has not (A → REVIEW-A → CHECK → A-FIX-1 makes
  // A ⇄ CHECK). Inside a cycle, an edge into a card that starts earlier in the job graph is a feedback edge: drawn
  // below the cards, outside the layers; the Plan and Finish edges come from the job graph (see the phase edges)
  var jpar={},jd={},dep=id=>{if(jd[id]!=null)return jd[id];jd[id]=0;var v=0;(jpar[id]||[]).forEach(p=>{if(js[p]||PL[p])v=Math.max(v,dep(p)+1)});return jd[id]=v},
   cd={},cix={},succ={},num={},low={},on={},stk=[],scc={},sN=[],FB=[],nx=0;
  JP.forEach(e=>(jpar[e[1]]=jpar[e[1]]||[]).push(e[0]));
  Object.keys(js).concat(pls.map(p=>p.id)).forEach(id=>{var c=cardOf(id);(cd[c]=cd[c]||[]).push(dep(id))});
  cards.forEach((c,i)=>{cix[c.id]=i;(par[c.id]||[]).forEach(x=>(succ[x[0]]=succ[x[0]]||[]).push(c.id))});
  var first=id=>Math.min.apply(null,cd[id]||[1e9]),
   before=(a,b)=>first(a)<first(b)||first(a)===first(b)&&cix[a]<cix[b],
   tj=v=>{num[v]=low[v]=nx++;stk.push(v);on[v]=1;(succ[v]||[]).forEach(w=>{if(num[w]==null){tj(w);low[v]=Math.min(low[v],low[w])}else if(on[w])low[v]=Math.min(low[v],num[w])});
    if(low[v]===num[v]){var w,k=sN.length;sN.push(0);do{w=stk.pop();on[w]=0;scc[w]=k;sN[k]++}while(w!==v)}};
  cards.forEach(c=>{if(num[c.id]==null)tj(c.id)});
  cards.forEach(c=>{if(par[c.id])par[c.id]=par[c.id].filter(x=>{var f=scc[x[0]]===scc[c.id]&&before(c.id,x[0]);if(f)FB.push([x[0],c.id,x[2],x[3]]);return!f})});
  // the Integration card draws edges from the last writers only: the others reach it through them
  var anc={},A=id=>{if(anc[id])return anc[id];var o=anc[id]={};(par[id]||[]).forEach(x=>{o[x[0]]=1;Object.assign(o,A(x[0]))});return o},IP=par[PC.integration];
  if(IP)par[PC.integration]=IP.filter(x=>x[1]===""||!IP.some(y=>y[0]!==x[0]&&A(y[0])[x[0]]));
  cards.forEach(c=>(par[c.id]||[]).forEach(x=>{var nw=x[1]===""||x[1]==="tgt"?ch.newE[x[2]+">"+x[3]]:null;eg(x[0],c.id,(nw!=null?"new ":"")+x[1],nw!=null?"Edge added after plan approval: "+nw:"")}));
  ghosts.forEach(id=>ch.removed[id].needs.map(cardOf).filter(n=>has[n]&&n!==id).forEach(x=>eg(x,id,"old")));
  Object.keys(ch.oldE).map(k=>k.split(">")).forEach(e=>{var a=cardOf(e[0]),b=cardOf(e[1]);if(has[a]&&has[b]&&a!==b&&!(inc[b]||[]).includes(a))eg(a,b,"old","Edge removed after plan approval: "+ch.oldE[e.join(">")])});
  // phase edges: Shape → Plan → the first jobs of the plan; the last cards → Finish. Both come from the job graph,
  // not the card graph, whose cycles hide them: Plan → every card that holds an entry job (no needs among the jobs,
  // planned before plan approval); every card that holds a terminal job (nothing needs it) → Finish. Outside a card
  // cycle a card with an edge out needs no Finish edge: its terminal jobs (review rows) never follow the cards after it
  var pa0=ev.findIndex(e=>e.type==="plan.approved"),src={},jkid={},inG=id=>(js[id]||PL[id])&&C[cardOf(id)],
   ends=(rel,ok)=>{var o={};Object.keys(js).concat(pls.map(p=>p.id)).forEach(id=>{var c=cardOf(id);
    if(C[c]&&/^(job|integration)$/.test(C[c].kind)&&ok(c,id)&&!(rel[id]||[]).some(inG))o[c]=1});return o};
  JP.forEach(e=>(jkid[e[0]]=jkid[e[0]]||[]).push(e[1]));E0.forEach(e=>{src[e[0]]=1});
  var entry=ends(jpar,(c,id)=>pa0<0||C[c].kind!=="job"||at[id]==null||at[id]<pa0),last=ends(jkid,c=>sN[scc[c]]>1||!src[c]);
  eg(PC.shape,PC.plan,"");
  cards.forEach(c=>{if(entry[c.id])eg(PC.plan,c.id,"")});
  if(C[PC.jobs])eg(PC.plan,PC.jobs,"pl");
  var sinks=cards.filter(c=>last[c.id]||c.kind==="holder");
  if(sinks.length)sinks.forEach(c=>eg(c.id,PC.finish,c.kind==="holder"?"pl":""));else eg(PC.plan,PC.finish,"");
  var nF=E0.length;FB.forEach(x=>E0.push([x[0],x[1],"fb","Feedback edge: "+x[3]+" follows "+x[2]+". "+C[x[1]].title+" starts before "+C[x[0]].title+", so the edge runs back below the cards."]));
  // [AMEND-4] a card added during execution without parents starts in the column of the rightmost job
  // dispatched (running or done) before it was added; from the event log, so it never moves later
  var base=id=>id===PC.shape?0:id===PC.plan?1:2,
   floor=(id,seen)=>{if(inc[id]||!js[id]||pa0<0||!(at[id]>pa0))return 0;var v=0;
    ev.slice(0,at[id]).forEach(e=>{var k=e.type==="job.dispatched"&&cardOf(e.job);if(k&&has[k]&&k!==id)v=Math.max(v,L(k,seen))});return v};
  var L=(id,seen)=>{if(lay[id]!=null)return lay[id];if(seen[id])return 0;seen[id]=1;var v=Math.max(base(id),floor(id,seen));(inc[id]||[]).forEach(x=>{v=Math.max(v,L(x,seen)+1)});seen[id]=0;return lay[id]=v};
  cards.forEach(c=>{L(c.id,{})});
  // a long edge gets one waypoint per layer it crosses, so it never passes under a card
  var chains=E0.map((e,n)=>{if(n>=nF)return null;var c=[e[0]];for(var k=lay[e[0]]+1;k<lay[e[1]];k++){var d="~"+n+"~"+k;lay[d]=k;c.push(d)}c.push(e[1]);
    for(var i=1;i<c.length;i++){(up[c[i]]=up[c[i]]||[]).push(c[i-1]);(dn[c[i-1]]=dn[c[i-1]]||[]).push(c[i])}return c});
  Object.keys(lay).forEach(id=>(cols[lay[id]]=cols[lay[id]]||[]).push(id));cols=cols.filter(Boolean);
  var ix=()=>cols.forEach(c=>c.forEach((id,i)=>{pos[id]=i-(c.length-1)/2})),
   bary=(c,rel)=>{var b={};c.forEach(id=>{var r=(rel[id]||[]).filter(x=>pos[x]!=null);b[id]=r.length?r.reduce((s,x)=>s+pos[x],0)/r.length:pos[id]});c.sort((a,z)=>b[a]-b[z]||pos[a]-pos[z])};
  ix();for(var n=0;n<4;n++){for(var l=1;l<cols.length;l++){bary(cols[l],up);ix()}for(l=cols.length-2;l>=0;l--){bary(cols[l],dn);ix()}}
  var NW=GC.NW,GX=GC.GX,GY=GC.GY,P=GC.P,DH=GC.DH,h=id=>id[0]==="~"?DH:C[id].h,colH=c=>c.reduce((s,id)=>s+h(id)+GY,-GY),max=Math.max(GC.HH,...cols.map(colH)),Hh=P*2+max,Wd=P*2+cols.length*NW+(cols.length-1)*GX;
  cols.forEach((c,l)=>{var y=P+(max-colH(c))/2;c.forEach(id=>{xy[id]=[P+l*(NW+GX),y];y+=h(id)+GY})});
  // a feedback edge: from the bottom of its card down, along below every card of the columns it spans, up into the card
  var fbD=(e,k)=>{var a=e[0],b=e[1],l0=Math.min(lay[a],lay[b]),l1=Math.max(lay[a],lay[b]),lo=0;
    cols.slice(l0,l1+1).forEach(c=>c.forEach(id=>{lo=Math.max(lo,xy[id][1]+h(id))}));
    var yb=lo+GC.FB+k*GC.FBS,sx=xy[a][0]+NW/2,tx=xy[b][0]+NW/2,dr=tx<sx?-1:1,r=Math.min(6,Math.abs(tx-sx)/2);Hh=Math.max(Hh,yb+P);
    return"M"+sx+" "+(xy[a][1]+h(a))+"V"+(yb-r)+"Q"+sx+" "+yb+" "+(sx+dr*r)+" "+yb+"H"+(tx-dr*r)+"Q"+tx+" "+yb+" "+tx+" "+(yb-r)+"V"+(xy[b][1]+h(b))};
  var cy=id=>xy[id][1]+h(id)/2,
   port=(id,other,list)=>{if(id[0]==="~")return cy(id);var o=list[id].slice().sort((a,b)=>cy(a)-cy(b)),k=o.length,sp=Math.min(12,(h(id)-24)/Math.max(1,k-1));return cy(id)+(o.indexOf(other)-(k-1)/2)*sp},
   E=chains.map((c,n)=>{var e=E0[n],ny=C[e[1]]&&C[e[1]].cls.includes("nyet"),y0=c&&port(c[0],c[1],dn),d=c?"M"+(xy[c[0]][0]+NW)+" "+y0:fbD(e,n-nF);
    for(var i=1;c&&i<c.length;i++){var x0=xy[c[i-1]][0]+NW,x1=xy[c[i]][0],last=i===c.length-1,y1=last?port(c[i],c[i-1],up):cy(c[i]),m=(x1-x0)/2;
      d+="C"+(x0+m)+" "+y0+" "+(x1-m)+" "+y1+" "+x1+" "+y1+(last?"":"H"+(x1+NW));y0=y1}
    return'<path class="e '+e[2]+(ny?" ny":"")+'" data-i="'+n+'" d="'+d+'">'+(e[3]?"<title>"+esc(e[3])+"</title>":"")+"</path>"});
  var N=cards.map(c=>cardSvg(t,c,xy[c.id])),
   defs='<defs><pattern id="g-added" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="hb" width="7" height="7"/><line class="hs" x1="0" y1="0" x2="0" y2="7"/></pattern></defs>',
   inner=defs+E.join("")+N.join("");
  GE=E0.map(e=>[e[0],e[1]]);
  return{svg:'<svg width="'+Wd+'" height="'+Hh+'" viewBox="0 0 '+Wd+" "+Hh+'" role="group" aria-label="Job graph">'+inner+"</svg>",inner:inner,w:Wd,h:Hh,layer:lay,n:cards.length,ch:ch,pl:pls.length,edges:E0,cards:cards}}

// one card: title and status; line 2 kind (or steps) with tokens · time; line 3 verdict or note, and model · effort on the right;
// an optional line 4 with review and hold marks; below the separator, the rows
function cardSvg(t,c,at){var NW=GC.NW,HH=c.hh,o=[],sel=c.job&&S.job===c.job,
   sp=gpill(NW-8,7,20,c.st.k,c.st.text,1),idRoom=Math.floor((NW-18-sp[1]-(c.merged?16:0))/GC.CH),
   tkW=c.tk?Math.round(c.tk.length*GC.CS)+8:0,sub=trunc(c.sub||"",Math.max(6,Math.floor((NW-20-tkW)/GC.CS))),
   v=c.v?gpill(10,44,18,c.v[0],c.v[1],0,1):["",0],r3=c.r3?Math.round(c.r3.length*GC.CS):0,
   xRoom=NW-28-(v[1]?v[1]:c.l3?Math.min(110,Math.round(c.l3.length*GC.CS)+8):0),
   l3=!v[1]&&c.l3?trunc(c.l3,Math.max(6,Math.floor((NW-20-(c.x?Math.min(xRoom,120):r3?r3+8:0))/GC.CS))):"";
  o.push('<g class="nd k-'+c.st.k+" c-"+c.kind+(c.cls.length?" "+c.cls.join(" "):"")+(sel?" sel":"")+'" data-card="'+esc(c.id)+'" style="--kc:'+c.kc+'" transform="translate('+at+')"'+
   (c.job?' tabindex="0" role="button"'+dataJ("job",c.job):' tabindex="0" role="group"')+' aria-label="'+esc(c.tip)+'" data-tip="'+esc(c.tip)+'">');
  o.push('<rect class="wf" x="-5" y="-5" width="'+(NW+10)+'" height="'+(c.h+10)+'" rx="8"/><rect class="ring" x="-3" y="-3" width="'+(NW+6)+'" height="'+(c.h+6)+'" rx="7"/><rect class="nb" width="'+NW+'" height="'+c.h+'" rx="5"/>'+
   (c.bar?'<rect class="nbar" x="1" y="8" width="2" height="'+(HH-16)+'"/>':""));
  o.push('<text class="nid" x="10" y="21">'+esc(trunc(c.title,idRoom))+"</text>"+(c.merged?'<text x="'+(NW-sp[1]-24)+'" y="21">✓</text>':"")+sp[0]);
  o.push('<text class="nk" x="10" y="40">'+esc(sub)+"</text>"+(c.tk?'<text class="tk" x="'+(NW-10)+'" y="40" text-anchor="end">'+esc(c.tk)+"</text>":""));
  o.push(v[0]+(l3?'<text class="n3" x="10" y="58">'+esc(l3)+"</text>":"")+(c.x?mlab(t,c.xid,c.x,NW-12,58,xRoom):c.r3?'<text class="n3" x="'+(NW-12)+'" y="58" text-anchor="end">'+esc(c.r3)+"</text>":""));
  if(c.mark||c.hold)o.push(marks(t,c));
  if(c.rows.length){o.push('<line class="sep" x1="8" x2="'+(NW-8)+'" y1="'+(HH+2)+'" y2="'+(HH+2)+'"/>');
    c.rows.forEach((r,i)=>o.push(rowSvg(t,r,HH+GC.RS-2+i*GC.RH,c)))}
  return o.join("")+"</g>"}
// review and hold marks on line 4: no [?]; hover or focus shows why
function marks(t,c){var id=c.id,j=JS(t)[id],y4=GC.HH-2,m4="",cx=10,NW=GC.NW,rm=c.mark,hd=c.hold;
  if(rm){var w=Math.round(rm.mark.length*6.4+16);m4+='<g class="mk '+(MKC[rm.mark]||"on")+'" transform="translate('+cx+","+y4+')" tabindex="0" role="note" aria-label="'+esc(rm.mark+": "+rm.reason)+'" data-tiph="'+esc(markTip(t,id,rm))+'"><rect width="'+w+'" height="18" rx="4"/><text x="8" y="13">'+esc(rm.mark)+"</text></g>";cx+=w+6}
  if(hd){var on=holdOn(t,id),ht=on?"⏸ hold active":"⏸ hold after",hw=Math.round(ht.length*6.4+16);
    [on?"⏸ active":"⏸ hold","⏸"].forEach(v=>{if(cx+hw>NW-8){ht=v;hw=Math.round(v.length*6.4+16)}}); // beside a long review mark; the tooltip says it all
    m4+='<g class="mk hold'+(on?" on":"")+'" transform="translate('+cx+","+y4+')" tabindex="0" role="note" aria-label="'+esc(on?"hold active":"hold after this job")+'" data-tiph="'+esc("<b>"+(on?"Hold active: nothing new is dispatched.":"Hold after "+id+": once it is done"+(WR[j.kind]?" and merged":"")+", nothing new is dispatched.")+"</b>"+(hd.reason?"<br>"+esc(hd.reason):"")+"<br>Release: "+esc(holdCmd(t,id)))+'"><rect width="'+hw+'" height="18" rx="4"/><text x="8" y="13">'+esc(ht)+"</text></g>"}
  return m4}
// one row: glyph, short label, model · effort on the right; a click opens that job's panel ([EDGE-LONG-IDS]: the full ID is in the tooltip)
function rowSvg(t,r,y,c){var NW=GC.NW,RH=GC.RH,x=modelOf(t,r.id),p=r.planned&&PLo(t,r.id),
   tip=rowTip(t,r,x,c.kind==="job"?c.id:null);
  if(x&&p&&p.round>1)x.next=1;r.tip=tip;
  return'<g class="rw t-'+r.tone+(r.planned?" planned":"")+(S.job===r.id?" sel":"")+'" transform="translate(0,'+y+')"'+(r.planned?' role="note"':' tabindex="0" role="button"'+dataJ("job",r.id))+' aria-label="'+esc(tip)+'" data-tip="'+esc(tip)+'">'+
   '<rect class="hitr" x="4" y="0" width="'+(NW-8)+'" height="'+RH+'" rx="3"/><text class="rg'+(r.run?" pulse":"")+'" x="12" y="16">'+r.g+'</text><text class="rl" x="28" y="16">'+esc(r.label)+"</text>"+
   mlab(t,r.id,x,NW-12,16,NW-46-Math.round(r.label.length*GC.CH))+"</g>"}

/* ---------- graph canvas ([AMEND-4]): the view {x, y, k} lives per task in GV, so a refresh keeps it ---------- */
var GV={},GZ=[.2,2],GE=[],GHI=null,gvK=k=>Math.min(GZ[1],Math.max(GZ[0],k)),
 // wheel zoom ([GRAPH-ZOOM]): Cmd/Ctrl + scroll at `wheel`; a trackpad pinch arrives as Ctrl + small deltas,
 // about -100·ln(scale) in Chromium, so `pinch` .01 follows the fingers. Mouse wheels (deltas of 100) keep `wheel`.
 GZR={wheel:.0015,pinch:.01,pinchMax:50},
 gvRate=e=>(e.ctrlKey&&!e.metaKey&&!e.deltaMode&&Math.abs(e.deltaY)<GZR.pinchMax?GZR.pinch:GZR.wheel)*(e.deltaMode===1?16:1),
 gvT=v=>"translate("+v.x+" "+v.y+") scale("+v.k+")",
 gvFit=(W,H,w,h)=>{var k=gvK(Math.min(1,(W-32)/w,(H-32)/h));return{x:(W-w*k)/2,y:(H-h*k)/2,k:k}},
 // zoom by factor f around the point (px, py) of the canvas: that point stays under the pointer
 gvZoom=(v,px,py,f)=>{var k=gvK(v.k*f),r=k/v.k;return{x:px-(px-v.x)*r,y:py-(py-v.y)*r,k:k}},
 // [GRAPH-EDGE-HOVER]: the edges into and out of a card, and the cards at their ends
 gvLinks=(E,id)=>{var e=[],c={};c[id]=1;E.forEach((x,i)=>{if(x[0]===id||x[1]===id){e.push(i);c[x[0]]=c[x[1]]=1}});return{edges:e,cards:Object.keys(c)}},
 FIT_ICON='<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
function gvCanvas(g){var v=GV[S.task];
  return'<div class="gwrap" data-task="'+esc(S.task)+'" data-w="'+g.w+'" data-h="'+g.h+'" style="height:min(70vh,'+Math.max(260,g.h+40)+'px)">'+
   '<svg class="gcv" width="100%" height="100%" role="group" aria-label="Job graph"><g class="gv"'+(v?' transform="'+gvT(v)+'"':"")+">"+g.inner+"</g></svg>"+
   '<div class="gz"><button class="btn ic sm" data-gz="in" aria-label="Zoom in">+</button><button class="btn ic sm" data-gz="out" aria-label="Zoom out">−</button>'+
   '<button class="btn ic sm" data-gz="fit" aria-label="Fit the whole graph" title="Fit the whole graph">'+FIT_ICON+"</button></div></div>"}
// after each render: the first open of a task fits the graph; then the stored view is applied
function gvMount(){var w=$(".gwrap");if(!w||w.dataset.task!==S.task)return;var W=w.clientWidth,H=w.clientHeight;
  if(!GV[S.task]){if(!(W>0&&H>0))return;GV[S.task]=gvFit(W,H,+w.dataset.w,+w.dataset.h)}
  var v=GV[S.task],g=w.querySelector(".gv");if(g)g.setAttribute("transform",gvT(v));
  // the dot grid follows pan and zoom: dots move closer when zoomed out
  w.style.backgroundSize=16*v.k+"px "+16*v.k+"px";w.style.backgroundPosition=v.x+"px "+v.y+"px";
  if(GHI)gvHi(GHI)}
// hover or keyboard focus on a card: its edges in the highlight color, its neighbours at full strength, the rest dimmed
function gvHi(id){var g=$(".gwrap .gv");GHI=id||null;if(!g||!g.classList)return;g.querySelectorAll(".on").forEach(x=>x.classList.remove("on"));
  var k=id&&g.querySelector('.nd[data-card="'+String(id).replace(/["\\]/g,"\\$&")+'"]');g.classList.toggle("hov",!!k);if(!k)return;
  var ln=gvLinks(GE,id);ln.edges.forEach(i=>{var p=g.querySelector('.e[data-i="'+i+'"]');if(p)p.classList.add("on")});
  ln.cards.forEach(c=>{var n=g.querySelector('.nd[data-card="'+c.replace(/["\\]/g,"\\$&")+'"]');if(n)n.classList.add("on")})}
var gvSet=v=>{GV[S.task]=v;gvMount()},gvDrag=null;
D.addEventListener("wheel",e=>{var w=e.target.closest&&e.target.closest(".gwrap"),v=GV[S.task];if(!w||!v)return;e.preventDefault();
  var r=w.getBoundingClientRect();
  // Cmd+scroll (Ctrl+scroll elsewhere, and trackpad pinch) zooms around the pointer; plain scroll pans
  gvSet(e.ctrlKey||e.metaKey?gvZoom(v,e.clientX-r.left,e.clientY-r.top,Math.exp(-e.deltaY*gvRate(e))):{x:v.x-e.deltaX,y:v.y-e.deltaY,k:v.k})},{passive:false});
D.addEventListener("pointerdown",e=>{var w=e.target.closest&&e.target.closest(".gwrap"),v=GV[S.task];
  if(!w||!v||e.button!==0||e.target.closest(".nd,.gz"))return;gvDrag={x:e.clientX,y:e.clientY,v:v};w.classList.add("drag")});
D.addEventListener("pointermove",e=>{if(gvDrag)gvSet({x:gvDrag.v.x+e.clientX-gvDrag.x,y:gvDrag.v.y+e.clientY-gvDrag.y,k:gvDrag.v.k})});
D.addEventListener("pointerup",()=>{if(!gvDrag)return;gvDrag=null;var w=$(".gwrap");if(w)w.classList.remove("drag")});
D.addEventListener("click",e=>{var b=e.target.closest&&e.target.closest("[data-gz]"),w=$(".gwrap"),v=GV[S.task];if(!b||!w||!v)return;
  var W=w.clientWidth,H=w.clientHeight,z=b.dataset.gz;
  gvSet(z==="fit"?gvFit(W,H,+w.dataset.w,+w.dataset.h):gvZoom(v,W/2,H/2,z==="in"?1.25:.8))});
D.addEventListener("mouseover",e=>{var n=e.target.closest&&e.target.closest(".gwrap .nd"),id=n?n.dataset.card:null;if(id!==GHI)gvHi(id)});
D.addEventListener("focusin",e=>{var n=e.target.closest&&e.target.closest(".gwrap .nd");if(n)gvHi(n.dataset.card)});
D.addEventListener("focusout",e=>{if(e.target.closest&&e.target.closest(".gwrap .nd"))gvHi(null)});

// the process map of `sae status` ([VIEWER-PROCESS-MAP]): the server sends its lines, the page only shows them
var pmap=t=>(t.map||[]).length?'<pre class="pmap" aria-label="Process map">'+esc(t.map.join("\n"))+"</pre>":"";

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
TAB.plan=t=>{var js=JS(t),g=graph(t),ch=g.ch,n=o=>Object.keys(o).length,
   ln=(c,l)=>'<span><svg width="22" height="8" aria-hidden="true"><path class="e '+c+'" d="M0 4H22"/></svg> '+l+"</span>",
   act=jf(t,(j,id)=>own(holdsOf(t),id)&&holdOn(t,id));
  var out=NOTE&&NOTE.task===S.task?'<p class="note'+(NOTE.err?" err":"")+'" role="status">'+esc(NOTE.text)+"</p>":"";
  if(act.length)out+='<div class="hbar" role="status"><b>⏸ Hold after '+act.map(esc).join(", ")+" is active.</b> Nothing new is dispatched until you release it; running jobs finish."+act.map(id=>holdBtn(t,id)).join("")+"</div>";
  // the rows' glyphs, and the rule where a review lives, in the legend's tooltip ([GRAPH-INTEGRATION-CARD])
  out+='<div class="gh"><h2 class="lbl">Graph</h2><div class="legend">'+["pending","ready","running","done","parked","failed"].map(pill).join("")+"<span>✓ merged</span>"+
   '<span class="lgr" tabindex="0" role="note" aria-label="'+esc(RULE)+'" data-tip="'+esc(RULE)+'">Rows: <i class="t-planned">◌</i> planned · <i class="t-running">◐</i> running · <i class="t-pass">✓</i> pass · <i class="t-fail">✕</i> changes required</span></div></div>';
  out+=gvCanvas(g);
  out+='<div class="legend kinds" aria-label="Legend">'+KINDS.map(k=>'<span><i class="ks" style="--kc:var(--kd-'+k+')"></i>'+k+"</span>").join("")+'<span><i class="ks run"></i>running</span><span><i class="ks ny"></i>cannot start yet</span>'+
   (g.cards.some(c=>c.cls.includes("added"))?'<span><i class="ks hatch"></i>added after approval</span>':"")+(g.cards.some(c=>c.bar)?'<span class="lgb">changed after approval</span>':"")+
   (g.edges.some(e=>e[2]==="fb")?ln("fb","runs back to a later row"):"")+(n(ch.newE)?ln("new","edge added after approval"):"")+(n(ch.oldE)||n(ch.removed)?ln("old","removed after approval"):"")+"</div>";
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
 // a planned review of a job is overridden as "<job> --review"; a next integration round by its override key
 // (REVIEW-INTEGRATION: every round); the others, the planned planner too, by their own ID
 ovrBody=(t,id)=>{var p=PLo(t,id);return p&&!/^(spec|plan|integration)$/.test(p.target)?{job:p.target,review:true}:{job:p&&p.key||id}};
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
    return tr([[x[1]?"mono mut":"mono",esc(id)],["hm",esc(j.kind)+'<span class="mut"> · '+esc(difOf(t,id))+"</span>"],jpill(t,id),["ink2",agoH(j.last_change)],["n",j.attempts.length],["mono ink2",esc([...new Set(j.attempts.map(model))].join(", ")||"–")],["n",tk?num(tk):"–"],(r=>r.v?vpill(r.v):r.x?'<span class="mut">'+r.x+"</span>":"")(revInfo(t,id))],
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
  return sec("Decision jobs",dj.length?tbl("","ID,For,Status,Question or decision",dj.map(k=>{var j=js[k],q=js[j.target]?ask(t,j.target):"";return tr([["mono nw",esc(k)],["mono nw",esc(j.target)],["nw",jpill(t,k)],["long",j["class"]?esc(j.decision)+' <span class="mut">· '+esc(j["class"])+" · "+esc(j.recommendation)+"</span>":'<span class="ink2">'+(q||"–")+"</span>"]],' class="r1'+(S.job===k?" open":"")+'"'+dataJ("job",k)+' tabindex="0"')})):box([],"No decision jobs."))+
   drafts()+sec("Decisions and amendments",ev.length?tbl("","When,Type,Class,By,Summary",ev.map(e=>tr([["ink2 nw",esc(fmt(e.at))],esc(e.type)+" "+code(e.id),d(e["class"]),'<span class="tag">'+d(e.by)+"</span>",["long",esc(e.summary)+(e.job?" · "+J(e.job):"")]]))):box([],"No decisions or amendments logged."))};
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
    return tr(['<span class="tag">'+esc(f.type||"–")+"</span>",["long",esc(f.title)],["mono ink2 nw",esc(f.source?slug(f.source):"–")],["ink2",esc(f.confidence||"–")],["ink2 nw",agoH(f.created)]],' class="r1'+(op?" open":"")+'"'+dataJ("row","f:"+f.file)+' tabindex="0" aria-expanded="'+op+'"')+
      (op?'<tr><td colspan="5" class="xd"><p class="mono mut">'+esc(f.file)+"</p>"+md(f.text)+"</td></tr>":"")})):box([],"No open findings."))+
   sec("Closed",cr.length?tbl("","Title,Outcome,Closed",cr.map(c=>tr([["ink2 long",esc(c[2])],["ink2",esc(c[3])],["mut nw",esc(c[0])]]))):box([],"No closed findings."))};
function jobBody(t,id){var js=JS(t),j=own(js,id),f=t.files;
  if(!j){var g=own(changes(t).r.removed,id)||{},rf="jobs/"+id+".removed.md";return dl([["Status",pill("removed")],["Reason",esc(g.reason)]])+(f[rf]!=null?docs("j:",[rf],f):"")}
  var rs=reviewsOf(t,id),dj=jf(t,o=>o.kind==="decision"&&o.target===id),out=dl([["Status",jpill(t,id)],["Summary",esc(j.summary)],["Decision request",j.status==="parked"&&ask(t,id)],["Waits for",j.status==="pending"&&esc(waits(t,id).join(", "))],
    ["Needs",j.needs.map(J).join(", ")],["Target",j.target&&tgt(t,j.target)],["Fix of",J(j.fix_of)],["Reviews",rs.map(k=>J(k)+" "+stp(t,k)).join(" ")],["Decision jobs",dj.map(J).join(", ")],["Hold",dead(t)?"":(own(holdsOf(t),id)?'<span class="tag">⏸ '+(holdOn(t,id)?"hold active":"hold after this job")+"</span> ":"")+holdBtn(t,id)],["Commits",(j.commits||[]).map(c=>code(c.slice(0,7))).join(" ")],["Last change",agoH(j.last_change)]].map(p=>[p[0],p[1]||""]));
  if(j.attempts.length)out+=sec("Attempts",tbl("nw","~#,Model,Harness,Started,~Duration,~Tokens,Reason",j.attempts.map(a=>tr([["n",a.n],["mono",esc(model(a))],esc(a.harness+" "+tierOf(a)),["ink2",esc(fmt(a.started))],["n",esc(dur(a.duration_s)||(a.ended?"–":"running"))],["n",a.tokens?num(a.tokens):"–"],esc(a.reason||"")]))));
  var dd=[...new Set(["jobs/"+id+".md",resultPath(id,j),"jobs/"+id+".verify.log"].concat(dj.map(k=>"decisions/"+k+".md")))].filter(d=>f[d]!=null);
  return out+sec("Files",dd.length?docs("j:",dd,f):box([],"No files yet."))}
