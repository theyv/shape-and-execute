/* sae viewer: the Settings tab (Task, Project, Global), the routing panel, the model lists and the
   settings card in the task header, editable in place ([VIEWER-SETTINGS-HELP], [VIEWER-ROUTING-PANEL],
   [PROJECT-DEFAULTS]). Every change goes through the server, which runs the sae command:
   Task → sae set, Project → sae project set|unset, Global → sae setup save (the whole config).
   Task and Project save each change at once; Global is one document, so its changes collect in a
   draft until Save. Top-level names start with sx (or SX) so they never collide with app.js or
   task-views.js. */
"use strict";
TABS.push(["settings","Settings"]);
var SX={tab:LSg("sae-stab")||"task",h:LSg("sae-harness")||"claude",cur:null,draft:null,removed:{},msg:"",err:false,cmd:"",q:Promise.resolve()},
 SXTABS=[["task","Task"],["project","Project"],["global","Global"]],
 SXPH=["research","planning","execution","review"],SXD=["mechanical","normal","hard"],SXTIERS=["L1","L2","L3","L4"],
 SXPD={research:SXD,planning:["normal","hard"],execution:SXD,review:["normal","hard"]}, // planning and review are never mechanical
 SXPHN={research:"research jobs",planning:"the planner; its difficulty is the task difficulty",execution:"implementation, integration and validation jobs",review:"job reviews take their job's difficulty; spec, plan and integration reviews take the task difficulty"},
 SXHN={claude:"Claude",codex:"Codex"},SXPROV=[["claude","claude"],["codex","codex"],["cross-harness","cross-harness"]],
 // one row per setting: the `sae set` key → its path in settings.json and in `defaults`, and its key in the server's `sources`
 SXR={interaction:{p:["interaction"],f:"interaction"},research:{p:["levels","research"],f:"levels.research"},planning:{p:["levels","planning"],f:"levels.planning"},
  execution:{p:["levels","execution"],f:"levels.execution"},"review-level":{p:["levels","review"],f:"levels.review"},review:{p:["review","points"],f:"review.points"},
  reviewer:{p:["review","provider"],f:"review.provider"},"max-verify-failures":{p:["max_verify_failures"],f:"max_verify_failures"},"task-difficulty":{p:["task_difficulty"],f:"task_difficulty"}},
 SXLV=[["research","Research level"],["planning","Planning level"],["execution","Execution level"],["review-level","Review level"]],
 sxClone=o=>o==null?o:JSON.parse(JSON.stringify(o)),
 sxGet=(o,p)=>p.reduce((n,k)=>n&&typeof n==="object"?own(n,k):undefined,o),
 sxPut=(o,p,v)=>{var n=o;p.slice(0,-1).forEach(k=>{if(!n[k]||typeof n[k]!=="object")n[k]={};n=n[k]});n[p[p.length-1]]=v},
 sxPts=pts=>POINTS.filter(x=>(pts||[]).includes(x)),
 sxStr=(k,v)=>k==="review"?(v&&v.length?v.join(","):"off"):String(v);

/* ---------- texts behind every [?] ---------- */
var SXMODE={
 "full-auto":"The agent decides everything, spec changes included; nothing waits for you. You review every agent decision in the final report before merging. Two stops still hold: a hold you set after a job, and a second changes-required round of a review.",
 auto:"The agent decides everything inside the spec, risky choices included, and lists each decision in the final report. A change to the spec is never decided: the affected jobs wait for you, and the rest of the work continues.",
 "critical-only":"The agent decides routine choices, clear choices and tradeoffs alone, and lists them in the final report. It asks only about lasting or risky choices (architecture, public API, data model, new dependencies) and about anything that touches the spec. Other work continues while a question waits.",
 collaborative:"The agent decides routine and clear choices alone. It asks you about real tradeoffs, lasting or risky choices and anything that touches the spec. Other work continues while a question waits.",
 interactive:"The agent decides only routine things that follow from the spec or the repository. It asks you about every other choice, even when one option is clearly better. For sessions where you sit at the computer and want to steer each step."},
 sxT=rows=>"<table><tbody>"+rows.map(r=>"<tr><td>"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("")+"</tbody></table>",
 HELP={
 card:"<p><b>Task settings</b> — this task's <code>settings.json</code>. Change them here or in the Settings tab: both run <code>sae set</code> and apply from the next dispatch. Running jobs keep their model.</p><p>Routing, the project's and the global settings are in the Settings tab.</p>",
 tabs:"<p><b>Task</b> — this task only. Changed most often. A new task copies the Project values (or the Global ones) once, at <code>sae new</code>; \"inherits project\" means the value still equals them.</p><p><b>Project</b> — your own defaults for new tasks in this repository, kept in your user config, never in the repository. Anything not set here inherits Global.</p><p><b>Global</b> — your user config: defaults for every repository, the routing tables, tiers and model lists. Its changes are a draft until you press Save.</p><p>Routing tiers and cells are read at every dispatch: the task wins over the project, the project over global. \"set here · reset\" marks a value set on this level; reset goes back to the inherited one.</p>",
 interaction:"<p><b>Interaction mode</b> — when agents ask you during execution. Shaping and the two approvals always involve you. Hard stops (push, deploy, secrets, deleting what the job did not create) happen in no mode.</p>"+sxT(MODES.map(m=>[m,SXMODE[m]])),
 levels:"<p><b>Levels</b> — one per phase. The level picks the row of that phase's routing table; the job's difficulty picks the column. Change it any time, for example plan on premium and execute on economy.</p>"+sxT([["economy","the cheapest row: lighter models or lower efforts, as the routing table below sets them."],["balanced","the middle row, for most work."],["premium","the strongest row, for hard or risky work."]]),
 points:"<p><b>Review points</b> — where an independent agent reviews the work. Each review costs one run of the review model. Its findings are claims: the fixer checks each one before acting on it.</p>",
 spec:"<p><b>spec</b> — reviews the spec before you approve it: gaps, contradictions, requirements that cannot be checked.</p>",
 plan:"<p><b>plan</b> — reviews the job graph before you approve the plan: missing jobs, wrong order, jobs too big for one worker, checks that prove nothing.</p>",
 jobs:"<p><b>jobs</b> — reviews single implementation jobs before they merge into the task branch. The switch next to it picks which jobs.</p>",
 integration:"<p><b>integration</b> — after every job has merged, one review of the whole change. Fixes get another round. The task cannot finish while it says changes-required.</p>",
 "jobs-mode":"<p><b>Which jobs get a review</b></p>"+sxT([["agent-selected jobs","only jobs the planner flags as risky. The plan card lists them before you approve. Stored as <code>selected-jobs</code>."],["all jobs","every implementation job, flagged or not. Slower and costlier; for risky or unfamiliar code. Stored as <code>all-jobs</code>."]]),
 provider:"<p><b>Review provider</b> — which harness reviews. The review model comes from that harness's review table.</p>"+sxT([["claude","Claude reviews."],["codex","Codex reviews."],["cross-harness","the other harness reviews: Codex when Claude orchestrates, Claude when Codex does. A second model family does not share the author's blind spots. When the other harness's CLI fails, the review runs in the orchestrator's harness."]]),
 verify:"<p><b>Verify limit</b> — how many failed check runs (the job's <code>verify</code> commands) a job may have before sae marks it failed and stops it. An integer from 1 to 10.</p>",
 ask:"<p><b>Ask signal</b> — whether <code>sae next</code> reminds the orchestrator to record each question it puts to you during execution, so the graph and the browser tab show that the task waits for you.</p>"+sxT([["mode default","on in full-auto, auto and critical-only; off in collaborative and interactive, where you expect questions. Follows a change of the interaction mode."],["on","always reminds."],["off","never reminds."]])+"<p>Parked jobs, a parked task and holds show in every mode; this setting changes only the reminder.</p>",
 difficulty:"<p><b>Task difficulty</b> — the column of the routing tables that the planner and the spec, plan and integration reviews use. Job reviews take their own job's difficulty (a mechanical job counts as normal).</p>"+sxT([["normal","most tasks."],["hard","a large or risky task: the planner and those reviews run on the hard column."]]),
 routing:"<p><b>Routing</b> — which model and effort run a job. One table per phase: rows are the levels set above, columns the difficulty the planner gives each job. Planning and reviews are never mechanical, so their mechanical cell is not used.</p><p>Changes apply from the next dispatch. Running jobs keep their model.</p>",
 harness:"<p><b>Claude | Codex</b> — each harness has its own model list, tiers and tables. Jobs run on the orchestrator's harness; reviews on the harness the review provider names.</p>",
 tiers:"<p><b>Tiers</b> — four presets, each a model · effort, colored by number: L1 blue, L2 yellow, L3 orange, L4 red.</p>"+sxT([["on","every cell picks a tier; editing a tier changes every cell that uses it."],["off","cells pick a model · effort directly; the tiers are greyed out."]])+"<p>A cell can keep both a tier and a model · effort; the switch picks which one counts. Switching off below Global writes each tier's model · effort into the cells that had only a tier, on this level.</p>",
 models:"<p><b>Models</b> — the models offered in tiers and tables, lightest first. The order sets the colors: blue, yellow, orange, red, purple, brown. A family entry always means the newest version; sae resolves it at dispatch. Pin an older version only when you need it.</p>"+sxT([["checkbox","ticked: offered in tiers and tables. Unticked: kept in the list (and its color), not offered."],["↑ ↓","change the order, and so the colors."],["✕","remove the entry."]])+"<p>A cell or tier that uses a removed or unticked model shows \"(not in list)\" with a red dashed outline; Save waits until it changes.</p>",
 claudeold:"<p><b>Claude: families only</b> — the Agent tool accepts only family names and always runs the newest version of the family. \"Add family\" offers every Claude family sae knows that is not in the list. A family removed here comes back with its efforts; a new one takes the efforts of the families listed.</p>",
 codexadd:"<p><b>Codex: older versions</b> — offered from the Codex model catalog on this machine (<code>models_cache.json</code>, or <code>codex debug models</code>), with the efforts each version accepts. Nothing is typed by hand.</p>"};

/* ---------- data: GET /api/settings for the task (Task tab) and for the project (Project, Global) ---------- */
function sxLoad(force){var rk=S.repo,id=S.task,key=rk+"|"+id,c=SX.cur;if(!rk||!id)return;
  if(c&&c.key===key&&(c.loading||!force&&Date.now()-c.at<4000))return;
  var n={key:key,loading:true,at:Date.now(),task:c&&c.key===key?c.task:null,proj:c&&c.key===key?c.proj:null,err:"",sig:c&&c.key===key?c.sig:""},left=2,
   done=()=>{if(--left)return;n.loading=false;n.at=Date.now();var sig=(n.task||{}).version+"|"+(n.proj||{}).version+"|"+n.err;if(SX.cur===n&&sig!==n.sig){n.sig=sig;if(S.tab==="settings")renderMain()}};
  SX.cur=n;
  api("/api/settings?repo="+enc(rk)+"&task="+enc(id),(d,e)=>{if(d)n.task=d;if(e)n.err=e;done()});
  api("/api/settings?repo="+enc(rk),(d,e)=>{if(d)n.proj=d;if(e)n.err=e;done()})}
var sxData=()=>SX.cur&&SX.cur.key===S.repo+"|"+S.task?SX.cur:null,
 sxSaved=()=>{var c=sxData(),d=c&&(c.proj||c.task);return d&&d.config&&d.config.schema===2?d.config:null},
 sxProj=()=>{var c=sxData(),d=c&&(c.proj||c.task);return d&&d.project||{}},
 sxConf=()=>SX.draft&&SX.draft.repo===S.repo?SX.draft.c:sxSaved(),            // Global: the draft, if any
 sxModels=sc=>(sc==="global"?sxConf():sxSaved()||{}).models||{},
 sxRO=()=>{var t=T();return!t||/^(done|abandoned)$/.test(t.state.task.phase)}; // a finished record is read-only

/* the value of a setting on one level; Project and Task fall back like `sae new` does */
function sxVal(sc,k){var r=SXR[k],t=T(),c=sxSaved(),v;
  if(sc==="task"){var s=t&&settingsOf(t);if(!s)return undefined;if(k==="max-verify-failures")return vlimit(t,s);if(k==="task-difficulty")return s.task_difficulty||"normal";return sxGet(s,r.p)}
  if(sc==="project"&&(v=sxGet(sxProj().defaults,r.p))!==undefined)return v;
  v=sxGet((sc==="global"?sxConf():c||{}).defaults,r.p);
  return v===undefined&&k==="max-verify-failures"&&t?t.settings_default_max_verify_failures:v}
// where a value comes from: "" on Global, else [source, reset key]
function sxSrc(sc,k){if(sc==="global")return null;
  if(sc==="project")return sxGet(sxProj().defaults,SXR[k].p)!==undefined?"project":"global";
  var c=sxData(),s=c&&c.task&&c.task.sources;return s?s[SXR[k].f]||null:null}
function sxTag(sc,src,k,what){if(sc==="global"||!src)return"";
  if(src===sc)return'<span class="inh set">set here'+(sc==="task"&&sxRO()?"":' · <button class="lnk" data-act="sxr" data-k="'+esc(sc+"|"+what+"|"+k)+'">reset</button>')+"</span>";
  return'<span class="inh">'+(k==="task-difficulty"?"default":"inherits "+esc(src))+"</span>"}

/* ---------- saving ---------- */
function sxMsg(){var m=SX.msg,cl="smsg"+(SX.err?" err":"");D.querySelectorAll(".smsg").forEach(e=>{e.className=cl;e.textContent=m;e.title=SX.cmd||""})}
function sxSay(m,err,cmd){SX.msg=m;SX.err=!!err;SX.cmd=cmd||"";sxMsg()}
// Task: POST set (sae set <task> k=v …); Project: POST project-set / project-unset. Saves run one after another;
// each carries the repository and task it was made for, so a queued one still goes there after a project switch.
function sxSave(sc,pairs,unset){var id=S.task,rk=S.repo,route=sc==="task"?"set":unset?"project-unset":"project-set",
  body=sc==="task"?{repo:rk,task:id,pairs:pairs}:unset?{repo:rk,keys:pairs}:{repo:rk,pairs:pairs};
  sxSay("Saving…");
  SX.q=SX.q.then(()=>post(route,body)).then(r=>{if(S.repo!==rk)return;
    if(!r.ok)sxSay(r.error||"Not saved.",true,r.command);
    else{var s=sc==="task"&&r.result&&r.result.settings;if(s&&own(TASKS,id))TASKS[id].settings=s;
      sxSay("Saved "+(sc==="task"?"for this task":"for this project")+". It applies from the next dispatch"+(sc==="task"?"; running jobs keep their model.":" (new tasks copy the defaults; routing applies to every task of this repository)."),false,r.command)}
    sxLoad(true);render();loadTask()})}
function sxSet(sc,k,v){if(sc==="global")return sxEdit(c=>sxPut(c.defaults,SXR[k].p,v));if(sc==="task"&&sxRO())return;sxSave(sc,[k+"="+sxStr(k,v)])}
function sxReset(sc,what,k){
  if(what==="d"){if(sc==="project")return sxSave(sc,[k],true);var v=k==="task-difficulty"?"normal":sxVal("project",k);if(v!==undefined)sxSave(sc,[k+"="+sxStr(k,v)]);return}
  if(sc==="project")sxSave(sc,[k],true);else sxSave(sc,[k+"=inherit"])}
// Global: a draft of defaults, models and routing; Save sends the freshest config with these three replaced
function sxEdit(fn){var c=sxSaved();if(!c)return;if(!SX.draft||SX.draft.repo!==S.repo)SX.draft={repo:S.repo,c:{defaults:sxClone(c.defaults),models:sxClone(c.models),routing:sxClone(c.routing)}};
  fn(SX.draft.c);var d=SX.draft.c;if(JSON.stringify([d.defaults,d.models,d.routing])===JSON.stringify([c.defaults,c.models,c.routing]))SX.draft=null;sxSay("");renderMain()}
function sxGlobalSave(){var dr=SX.draft,rk=S.repo;if(!dr||dr.repo!==rk)return;sxSay("Saving…");
  api("/api/settings?repo="+enc(rk),(d,e)=>{if(!d||!d.config)return sxSay(e||"The user config cannot be read.",true);
    var c=sxClone(d.config);c.defaults=dr.c.defaults;c.models=dr.c.models;c.routing=dr.c.routing;
    post("global",{repo:rk,config:c}).then(r=>{if(!r.ok)sxSay(r.error||"Not saved.",true,r.command);
      else{if(SX.draft===dr)SX.draft=null;sxSay("Saved the global config. It applies from the next dispatch; running jobs keep their model; new tasks copy the defaults.",false,r.command)}
      sxLoad(true);render();loadTask()})})}

/* ---------- controls ---------- */
var sxHelp=k=>'<button class="btn ic hq" data-act="help" data-h="'+k+'" data-k="h:'+k+'" aria-label="About this setting" aria-expanded="false">?</button>',
 sxSeg=(act,k,opts,v,dis,lab)=>'<div class="seg" role="radiogroup" aria-label="'+esc(lab||k)+'">'+opts.map(o=>'<button role="radio" aria-checked="'+(v===o[0])+'" data-act="'+act+'" data-k="'+esc(k)+'" data-v="'+esc(o[0])+'"'+(dis?" disabled":"")+">"+esc(o[1])+"</button>").join("")+"</div>",
 sxOpt=(v,cur,lab)=>'<option value="'+esc(v)+'"'+(v===cur?" selected":"")+">"+esc(lab)+"</option>",
 sxEntry=(models,h,m)=>((models||{})[h]||[]).find(x=>x.model===m),
 sxOk=(models,h,m,e)=>{var x=sxEntry(models,h,m);return!!(x&&x.enabled!==false&&(x.efforts||[]).includes(e))},
 // one dropdown of model · effort, grouped by model; only listed, ticked models and the efforts each accepts
 sxPreset=(models,h,pair,k,dis,lab)=>{var cur=pair?pair.model+"|"+pair.effort:"",ok=pair&&sxOk(models,h,pair.model,pair.effort),L=((models||{})[h]||[]).filter(x=>x.enabled!==false);
  return'<select data-act="sxs" data-k="'+esc(k)+'" aria-label="'+esc(lab||"Model and effort")+'"'+(dis?" disabled":"")+">"+(pair?ok?"":sxOpt(cur,cur,pair.model+" · "+pair.effort+" (not in list)"):sxOpt("","","— not set —"))+
   L.map(x=>'<optgroup label="'+esc(x.model)+'">'+(x.efforts||[]).map(e=>sxOpt(x.model+"|"+e,cur,x.model+" · "+e)).join("")+"</optgroup>").join("")+"</select>"},
 sxRow=(label,hk,ctl,tag)=>'<div class="srow"><div class="k">'+label+sxHelp(hk)+'</div><div class="c">'+ctl+(tag||"")+"</div></div>";

/* ---------- the ask signal ([ASK-SETTING]): a task setting; the server says what it is now (status.ask_signal) ---------- */
var SXASK=[["unset","mode default"],["on","on"],["off","off"]],
 sxAsk=t=>{var a=t&&t.status&&t.status.ask_signal,s=t&&settingsOf(t);if(a)return a;var v=s&&s.ask_signal;return{on:null,set:v==="on"||v==="off"?v:null,text:v==="on"||v==="off"?v:"mode default"}},
 sxAskNow=a=>a.on==null?"":a.set?"":"now "+(a.on?"on":"off")+" (interaction mode)";

/* ---------- defaults: interaction, levels, review points, provider, verify limit, task difficulty, ask signal ---------- */
function sxDefaults(sc){var ro=sc==="task"&&sxRO(),v=k=>sxVal(sc,k),tg=k=>sxTag(sc,sxSrc(sc,k),k,"d"),pts=v("review")||[],jobs=pts.find(x=>/-jobs$/.test(x)),K=k=>sc+"|"+k,
  name=(PROJ||[]).find(x=>x.key===S.repo),
  head={task:["This task","anything not set here inherits Project; the header card edits the same values"],project:["Defaults for new tasks in "+(name?name.name:"this repository"),"anything not set here inherits Global"],global:["Defaults for new tasks","used where Project sets nothing"]}[sc];
  if(sc==="task"&&!settingsOf(T()))return'<section class="sg">'+empty("settings.json is missing or invalid.")+"</section>";
  return'<section class="sg"><div class="sh"><h3>'+esc(head[0])+'</h3><span class="d">'+esc(head[1])+(ro?" · this task is finished; its settings are read-only":"")+"</span></div>"+
   sxRow("Interaction","interaction",sxSeg("sxv",K("interaction"),MODES.map(m=>[m,m]),v("interaction"),ro,"Interaction mode")+'<p class="mdesc">'+esc(SXMODE[v("interaction")]||"")+"</p>",tg("interaction"))+
   SXLV.map(x=>sxRow(x[1],"levels",sxSeg("sxv",K(x[0]),LEVELS.map(l=>[l,l]),v(x[0]),ro,x[1]),tg(x[0]))).join("")+
   sxRow("Review points","points",'<div class="cbs">'+["spec","plan","jobs","integration"].map(p=>'<span class="cb"><label><input type="checkbox" data-act="sxp" data-k="'+K(p)+'"'+((p==="jobs"?jobs:pts.includes(p))?" checked":"")+(ro?" disabled":"")+">"+p+"</label>"+sxHelp(p)+"</span>").join("")+"</div>"+
    (jobs?'<div class="jsub"><span class="note">jobs:</span>'+sxSeg("sxv",K("jobs"),[["selected-jobs","agent-selected jobs"],["all-jobs","all jobs"]],jobs,ro,"Which jobs get a review")+sxHelp("jobs-mode")+"</div>":""),tg("review"))+
   sxRow("Review provider","provider",sxSeg("sxv",K("reviewer"),SXPROV,v("reviewer"),ro,"Review provider"),tg("reviewer"))+
   (sc!=="project"?sxRow("Verify limit","verify",'<input type="number" min="1" max="10" step="1" data-act="sxn" data-k="'+K("max-verify-failures")+'" value="'+esc(v("max-verify-failures"))+'" aria-label="Failed check runs before a job fails"'+(ro?" disabled":"")+">",tg("max-verify-failures")):"")+
   (sc==="task"?sxRow("Task difficulty","difficulty",sxSeg("sxv",K("task-difficulty"),[["normal","normal"],["hard","hard"]],v("task-difficulty"),ro,"Task difficulty"),tg("task-difficulty")):"")+
   (sc==="task"?sxAskRow(ro):"")+"</section>"}
function sxAskRow(ro){var a=sxAsk(T()),now=sxAskNow(a);
  return sxRow("Ask signal","ask",sxSeg("sxv","task|ask-signal",SXASK,a.set||"unset",ro,"Ask signal")+'<p class="mdesc">Reminds the orchestrator to record its questions to you with <code>sae ask</code>, so the graph shows that the task waits for you.</p>',
   now?'<span class="inh">'+esc(now)+"</span>":a.set?'<span class="inh set">set here</span>':"")}

/* ---------- routing: tiers row and one table per phase, on every level ---------- */
// {tiers_in_cells, tiers, tables} with {value, source} leaves: from the server (Task, Project) or the draft (Global)
function sxRoute(sc,h){if(sc!=="global"){var c=sxData(),d=c&&(sc==="task"?c.task:c.proj);return d&&d.routing?d.routing[h]||null:null}
  var g=(sxConf()||{}).routing,b=g&&g[h],w=v=>({value:v,source:"global"}),o={tiers:{},tables:{}};if(!b)return null;
  o.tiers_in_cells=w(b.tiers_in_cells!==false);Object.keys(b.tiers||{}).forEach(n=>o.tiers[n]=w(b.tiers[n]));
  Object.keys(b.tables||{}).forEach(p=>Object.keys(b.tables[p]||{}).forEach(l=>Object.keys(b.tables[p][l]||{}).forEach(d=>sxPut(o.tables,[p,l,d],w(b.tables[p][l][d])))));return o}
var sxHarn=()=>{var g=(sxConf()||{}).routing||{};return["claude","codex"].filter(h=>own(g,h))};
// what a cell runs on: [tier or "", {model, effort} or null]
function sxUse(R,cell,on){cell=cell||{};if(on&&cell.tier){var t=R.tiers[cell.tier];return[cell.tier,t?t.value:null]}return["",cell.model?{model:cell.model,effort:cell.effort}:null]}
function sxRouting(sc){var hs=sxHarn();if(!hs.length)return'<section class="sg"><div class="sh"><h3>Routing</h3>'+sxHelp("routing")+"</div>"+empty(sxSaved()?"The user config has no routing.":"Routing needs a readable user config (schema 2). Run the skill's setup mode.")+"</section>";
  if(!hs.includes(SX.h))SX.h=hs[0];var h=SX.h,R=sxRoute(sc,h),ro=sc==="task"&&sxRO(),models=sxModels(sc),K=sc+"|",
   hsw=sxSeg("sxh",sc+"|harness",hs.map(x=>[x,SXHN[x]]),h,false,"Harness")+sxHelp("harness");
  if(!R)return'<section class="sg"><div class="sh"><h3>Routing</h3>'+sxHelp("routing")+hsw+"</div>"+empty("Loading…")+"</section>";
  var on=!R.tiers_in_cells||R.tiers_in_cells.value!==false,use={};
  SXPH.forEach(p=>LEVELS.forEach(l=>SXPD[p].forEach(d=>{var c=sxGet(R.tables,[p,l,d]),u=c&&sxUse(R,c.value,on);if(u&&u[0])use[u[0]]=(use[u[0]]||0)+1})));
  var tic=R.tiers_in_cells||{},tk="tiers-in-cells."+h,
   tiers='<div class="tiers'+(on?"":" off")+'"><div class="sh"><h3>Tiers</h3>'+sxHelp("tiers")+'<button class="tgl" role="switch" aria-checked="'+on+'" data-act="sxtic" data-k="'+esc(K+tk)+'"'+(ro?" disabled":"")+"><i></i>Tiers in cells</button>"+sxTag(sc,tic.source,tk,"r")+
    '<span class="d">'+(on?"cells pick a tier":"off — cells pick a model · effort")+'</span></div><div class="trow">'+SXTIERS.map(n=>{var t=R.tiers[n],v=t&&t.value,k="tier."+h+"."+n;
     return'<div class="tcard'+(v&&!sxOk(models,h,v.model,v.effort)?" bad":"")+(t&&sc!=="global"&&t.source===sc?" own":"")+'" style="--mc:'+tierColor(n)+'"><div class="h"><b>'+n+"</b><span>"+(on?"used in "+(use[n]||0):"")+"</span></div>"+
      sxPreset(models,h,v,K+k,ro||!on,n+" model and effort")+(v?routeWords(models,h,v.model,v.effort):'<span class="mut">not set</span>')+(t?sxTag(sc,t.source,k,"r"):"")+"</div>"}).join("")+"</div></div>";
  var tables=SXPH.map(p=>'<div class="rph"><div class="pht"><b>'+p+"</b><span>"+SXPHN[p]+'</span></div><div class="tw"><table class="rt"><thead><tr><th>level</th>'+SXD.map(d=>"<th>"+d+"</th>").join("")+"</tr></thead><tbody>"+
    LEVELS.map(l=>'<tr><td class="lv">'+l+"</td>"+SXD.map(d=>SXPD[p].includes(d)?sxCell(sc,h,R,p,l,d,on,models,ro):'<td class="na"><div>not used</div></td>').join("")+"</tr>").join("")+"</tbody></table></div></div>").join("");
  return'<section class="sg"><div class="sh"><h3>Routing</h3>'+sxHelp("routing")+hsw+'<span class="d">separate per harness</span></div>'+tiers+tables+
   '<p class="foot">Changes apply from the next dispatch. Running jobs keep their model.</p></section>'}
function sxCell(sc,h,R,p,l,d,on,models,ro){var c=sxGet(R.tables,[p,l,d]),cell=c?c.value:null,u=sxUse(R,cell,on),pair=u[1],k="routing."+h+"."+p+"."+l+"."+d,K=sc+"|"+k,
  bad=!pair||!sxOk(models,h,pair.model,pair.effort),ctl;
  if(on){var cur=cell&&cell.tier||"";ctl='<select data-act="sxs" data-k="'+esc(K)+'" data-tier="1" aria-label="'+esc(p+" "+l+" "+d+" tier")+'"'+(ro?" disabled":"")+">"+(cur?"":sxOpt("","",pair?pair.model+" · "+pair.effort+" (no tier)":"— not set —"))+
    SXTIERS.filter(n=>R.tiers[n]).map(n=>{var v=R.tiers[n].value;return sxOpt(n,cur,n+" — "+v.model+" · "+v.effort)}).join("")+"</select>"}
  else ctl=sxPreset(models,h,pair,K,ro,p+" "+l+" "+d+" model and effort");
  return'<td><div class="cell'+(bad?" bad":"")+(c&&sc!=="global"&&c.source===sc?" own":"")+'" style="--mc:'+(on&&u[0]?tierColor(u[0]):pair?modelColor(models,h,pair.model):"var(--cx)")+'">'+ctl+
   (pair?routeWords(models,h,pair.model,pair.effort):'<span class="mut">nothing usable</span>')+(c?sxTag(sc,c.source,k,"r"):"")+"</div></td>"}

/* ---------- model lists (Global only) ---------- */
var sxVer=s=>((/\d+(?:\.\d+)*/.exec(s)||[""])[0]).split(".").filter(Boolean).map(Number),
 sxCmpV=(a,b)=>{for(var i=0;i<Math.max(a.length,b.length);i++){var x=a[i]==null?-1:a[i],y=b[i]==null?-1:b[i];if(x!==y)return x-y}return 0},
 // mirrors family_of and newest_of_family in sae_lib (setup_mode.py, routing.py): a family is the last part of a versioned name
 sxCat=()=>{var c=sxData(),d=c&&(c.proj||c.task);return((d&&d.codex_catalog)||[]).filter(m=>m&&m.model&&(m.visibility==null||m.visibility==="list"))},
 sxFam=s=>{var l=s.split("-").pop();return s.includes("-")&&/^[a-z]+$/i.test(l)&&/\d/.test(s)?l:null},
 sxNewest=f=>sxCat().filter(m=>m.model.endsWith("-"+f)).sort((a,b)=>sxCmpV(sxVer(b.model),sxVer(a.model)))[0]||null,
 // the Claude families sae knows (settings answer, claude_families); a new one takes the efforts of the families listed
 sxCF=()=>{var c=sxData(),d=c&&(c.proj||c.task);return(d&&d.claude_families)||[]},
 sxEff=L=>[...new Set(L.flatMap(x=>x.efforts||[]))];
function sxAddable(h,L){var has=m=>L.some(x=>x.model===m);
  if(h!=="codex"){var rm=(SX.removed[h]||[]).filter(x=>!has(x.model)),back=rm.map(x=>x.model);
    return rm.map(x=>["rm:"+x.model,x.model+" · family"]).concat((sxEff(L).length?sxCF():[]).filter(f=>!has(f)&&!back.includes(f)).map(f=>["cf:"+f,f+" · family"]))}
  var cat=sxCat(),fams=[...new Set(cat.map(m=>sxFam(m.model)).filter(Boolean))].sort(),out=fams.filter(f=>!has(f)).map(f=>["fam:"+f,f+" · newest"]);
  return out.concat(cat.filter(m=>!has(m.model)&&!(sxFam(m.model)&&sxNewest(sxFam(m.model))===m)).sort((a,b)=>a.model<b.model?-1:1).map(m=>["ver:"+m.model,m.model+" · pinned version"]))}
function sxModelsSec(){var h=SX.h,M=(sxConf()||{}).models||{},L=M[h]||[],add=sxAddable(h,L),K="global|";
  return'<section class="sg"><div class="sh"><h3>Models · '+esc(SXHN[h]||h)+"</h3>"+sxHelp("models")+'<span class="d">changed rarely; the order sets the colors</span></div><div class="ml">'+L.map((x,i)=>{var n=x.family&&h==="codex"&&sxNewest(x.model);
   return'<div class="mr'+(x.enabled===false?" off":"")+'"><span class="ix">'+(i+1)+'</span><span class="sw" style="--mc:'+modelColor(M,h,x.model)+'"></span><label><input type="checkbox" data-act="sxmon" data-k="'+K+h+"|"+i+'"'+(x.enabled!==false?" checked":"")+">"+esc(x.model)+
    "<small>"+(x.family?"newest"+(n?" ("+esc(n.model)+")":""):"pinned version")+" · "+esc((x.efforts||[]).join(", "))+"</small></label>"+
    '<button class="btn ar" data-act="sxm" data-op="up" data-k="'+K+h+"|up|"+i+'" aria-label="Move '+esc(x.model)+' up"'+(i?"":" disabled")+'>↑</button><button class="btn ar" data-act="sxm" data-op="dn" data-k="'+K+h+"|dn|"+i+'" aria-label="Move '+esc(x.model)+' down"'+(i<L.length-1?"":" disabled")+'>↓</button><button class="btn ar" data-act="sxm" data-op="rm" data-k="'+K+h+"|rm|"+i+'" aria-label="Remove '+esc(x.model)+'">✕</button></div>'}).join("")+
   '</div><div class="add"><select id="sxadd" aria-label="Add a model"'+(add.length?"":" disabled")+">"+(add.length?add.map(a=>sxOpt(a[0],"",a[1])).join(""):"<option>"+(h==="claude"?"all families listed":"no other models in the catalog")+"</option>")+
   '</select><button class="btn sm" data-act="sxm" data-op="add" data-k="'+K+h+'|add"'+(add.length?"":" disabled")+">"+(h==="codex"?"Add older version":"Add family")+"</button>"+sxHelp(h==="claude"?"claudeold":"codexadd")+"</div></section>"}

/* ---------- the Settings tab ---------- */
TAB.settings=t=>{sxLoad(false);var sc=SXTABS.some(x=>x[0]===SX.tab)?SX.tab:"task",c=sxData(),err=c&&(c.err||(c.proj||c.task||{}).config_error),name=(PROJ||[]).find(x=>x.key===S.repo),dr=SX.draft&&SX.draft.repo===S.repo;
  var body=!c||(!c.task&&!c.proj)?empty(err?esc(err):"Loading…"):
   (err?'<p class="cfgerr">'+esc(err)+"</p>":"")+(sc==="global"&&dr?sxDraftBar():"")+sxDefaults(sc)+sxRouting(sc)+(sc==="global"&&sxHarn().length?sxModelsSec():"");
  return'<div class="box sbox"><div class="tabs stabs" role="tablist" aria-label="Settings level">'+SXTABS.map(x=>'<button role="tab" aria-selected="'+(sc===x[0])+'" data-act="sxt" data-k="'+x[0]+'">'+x[1]+(x[0]==="project"&&name?"<i>"+esc(name.name)+"</i>":x[0]==="global"&&dr?"<i>unsaved</i>":"")+"</button>").join("")+
   '<span class="sp"></span>'+sxHelp("tabs")+'</div><div class="smsg'+(SX.err?" err":"")+'" role="status" aria-live="polite" title="'+esc(SX.cmd)+'">'+esc(SX.msg)+"</div>"+body+"</div>"};
// the cells, tiers and the switch that cannot run as they are (a removed or unticked model, an undefined tier)
function sxBad(){var c=sxConf(),n=0;sxHarn().forEach(h=>{var R=sxRoute("global",h),M=c.models,on=!R.tiers_in_cells||R.tiers_in_cells.value!==false;
  SXTIERS.forEach(t=>{var v=R.tiers[t]&&R.tiers[t].value;if(v&&!sxOk(M,h,v.model,v.effort))n++});
  SXPH.forEach(p=>LEVELS.forEach(l=>SXPD[p].forEach(d=>{var x=sxGet(R.tables,[p,l,d]),u=sxUse(R,x&&x.value,on);if(!u[1]||!sxOk(M,h,u[1].model,u[1].effort))n++})))});return n}
function sxDraftBar(){var n=sxBad();return'<div class="draft"><span>Unsaved changes to the global config.'+(n?' <b class="err">'+plural(n,"marked value")+" to fix first.</b>":"")+'</span><button class="btn sm" data-act="sxg" data-k="discard">Discard</button><button class="btn sm pri" data-act="sxg" data-k="save"'+(n?" disabled":"")+">Save</button></div>"}

/* ---------- the settings card in the task header, editable in place ---------- */
var setPairs=(t,s)=>[["interaction",s.interaction],["research",s.levels.research],["planning",s.levels.planning],["execution",s.levels.execution],["review",s.review.points.length?s.review.points.join(", ")+" · "+s.levels.review+" · "+s.review.provider:"off"],["verify limit",vlimit(t,s)],["ask signal",sxAsk(t).text]];
function headerCard(t){var s=settingsOf(t);if(!s)return'<div class="card" aria-label="Settings"><span>settings.json is missing or invalid</span></div>';
  if(sxRO())return'<div class="card" aria-label="Settings">'+setPairs(t,s).map(p=>"<div><span>"+p[0]+"</span> <b>"+esc(p[1])+"</b></div>").join("")+"</div>";
  var sel=(k,opts,v)=>'<select data-act="hc" data-k="'+k+'" aria-label="'+k+'">'+opts.map(o=>sxOpt(o[0],v,o[1])).join("")+"</select>",pts=s.review.points,jobs=pts.find(x=>/-jobs$/.test(x)),lv=LEVELS.map(l=>[l,l]);
  return'<div class="card hc" aria-label="Task settings"><div><span>interaction</span>'+sel("interaction",MODES.map(m=>[m,m]),s.interaction)+"</div>"+
   [["research","research"],["planning","planning"],["execution","execution"],["review-level","review"]].map(x=>"<div><span>"+x[1]+"</span>"+sel(x[0],lv,sxGet(s,SXR[x[0]].p))+"</div>").join("")+
   "<div><span>reviews</span>"+["spec","plan","jobs","integration"].map(p=>'<label><input type="checkbox" data-act="hcp" data-k="'+p+'"'+((p==="jobs"?jobs:pts.includes(p))?" checked":"")+">"+p+"</label>").join("")+
    (jobs?sel("jobs",[["selected-jobs","agent-selected"],["all-jobs","all jobs"]],jobs):"")+"</div>"+
   "<div><span>reviewer</span>"+sel("reviewer",SXPROV,s.review.provider)+"</div><div><span>verify limit</span> <b>"+esc(vlimit(t,s))+"</b></div>"+
   (a=>"<div><span>ask signal</span>"+sel("ask-signal",SXASK.map(o=>[o[0],o[0]==="unset"&&a.on!=null?"mode default ("+(a.on?"on":"off")+")":o[1]]),a.set||"unset")+"</div>")(sxAsk(t))+'<span class="smsg'+(SX.err?" err":"")+'" role="status" aria-live="polite">'+esc(SX.msg)+"</span></div>"}
// review points after one checkbox: `jobs` stands for selected-jobs or all-jobs
function sxToggle(pts,p,on){var o=(pts||[]).filter(x=>x!==p&&!(p==="jobs"&&/-jobs$/.test(x)));if(on)o.push(p==="jobs"?"selected-jobs":p);return sxPts(o)}
var sxJobs=(pts,mode)=>sxPts((pts||[]).filter(x=>!/-jobs$/.test(x)).concat(mode));

/* ---------- events ---------- */
function sxTierOff(sc,h){ // switching tiers off below Global: cells that hold only a tier get the tier's model · effort on this level
  var R=sxRoute(sc,h),pairs=["tiers-in-cells."+h+"=off"];if(!R)return pairs;
  SXPH.forEach(p=>LEVELS.forEach(l=>SXPD[p].forEach(d=>{var c=sxGet(R.tables,[p,l,d]),v=c&&c.value,t=v&&v.tier&&R.tiers[v.tier];if(v&&!v.model&&t)pairs.push("routing."+h+"."+p+"."+l+"."+d+"="+t.value.model+":"+t.value.effort)})));return pairs}
function sxRouteSet(sc,k,val){ // one routing value: a tier name, "model|effort", or on/off
  if(sc==="task"&&sxRO())return;
  if(sc!=="global"){var v=/\|/.test(val)?val.slice(0,val.lastIndexOf("|"))+":"+val.slice(val.lastIndexOf("|")+1):val;return sxSave(sc,[k+"="+v])}
  var P=k.split("."),pair=/\|/.test(val)?{model:val.slice(0,val.lastIndexOf("|")),effort:val.slice(val.lastIndexOf("|")+1)}:null;
  sxEdit(c=>{var b=c.routing[P[1]];
    if(P[0]==="tier")(b.tiers=b.tiers||{})[P[2]]=pair;
    else if(P[0]==="routing"){var cell=sxGet(b,["tables",P[2],P[3],P[4]])||{};if(pair){cell.model=pair.model;cell.effort=pair.effort}else cell.tier=val;sxPut(b,["tables",P[2],P[3],P[4]],cell)}})}
D.addEventListener("click",ev=>{var e=ev.target.closest("[data-act]"),a=e&&e.dataset.act;if(!a||!/^(sx|hc)/.test(a)||e.disabled)return;var k=e.dataset.k||"",P=k.split("|"),sc=P[0];
  if(a==="sxt"){SX.tab=k;LSs("sae-stab",k);sxSay("");sxLoad(true);renderMain()}
  else if(a==="sxh"){SX.h=e.dataset.v;LSs("sae-harness",SX.h);renderMain()}
  else if(a==="sxv"){var v=e.dataset.v;if(P[1]==="jobs")sxSet(sc,"review",sxJobs(sxVal(sc,"review"),v));else sxSet(sc,P[1],v)}
  else if(a==="sxr")sxReset(sc,P[1],P.slice(2).join("|"));
  else if(a==="sxtic"){var h=P[1].split(".")[1],R=sxRoute(sc,h),on=!R||!R.tiers_in_cells||R.tiers_in_cells.value!==false;
    if(sc==="global")sxEdit(c=>{var b=c.routing[h];b.tiers_in_cells=!on;if(on)SXPH.forEach(p=>LEVELS.forEach(l=>SXPD[p].forEach(d=>{var x=sxGet(b,["tables",p,l,d]),t=x&&x.tier&&(b.tiers||{})[x.tier];if(x&&!x.model&&t){x.model=t.model;x.effort=t.effort}})))});
    else if(!(sc==="task"&&sxRO()))sxSave(sc,on?sxTierOff(sc,h):[P[1]+"=on"])}
  else if(a==="sxm")sxEdit(c=>{var L=c.models[P[1]],i=+P[3],x,sel=$("#sxadd");
    if(P[2]==="up")L.splice(i-1,0,L.splice(i,1)[0]);else if(P[2]==="dn")L.splice(i+1,0,L.splice(i,1)[0]);
    else if(P[2]==="rm"){x=L.splice(i,1)[0];(SX.removed[P[1]]=SX.removed[P[1]]||[]).push(x)}
    else if(P[2]==="add"&&sel&&sel.value){var v=sel.value,n=v.slice(v.indexOf(":")+1),m;
      if(/^rm:/.test(v))x=(SX.removed[P[1]]||[]).find(r=>r.model===n);
      else if(/^cf:/.test(v)){m=sxEff(L);x=m.length&&{model:n,family:true,enabled:true,efforts:m}}
      else if(/^fam:/.test(v)){m=sxNewest(n);x=m&&{model:n,family:true,enabled:true,efforts:m.efforts.slice()}}
      else{m=sxCat().find(r=>r.model===n);x=m&&{model:n,family:false,enabled:true,efforts:m.efforts.slice()}}
      if(x&&!L.some(r=>r.model===x.model))L.push(sxClone(x))}});
  else if(a==="sxg"){if(k==="save")sxGlobalSave();else{SX.draft=null;sxSay("Discarded the unsaved global changes.");renderMain()}}});
D.addEventListener("change",ev=>{var e=ev.target,a=e.dataset&&e.dataset.act;if(!a||!/^(sx|hc)/.test(a))return;var k=e.dataset.k||"",P=k.split("|"),sc=P[0],t=T(),s=t&&settingsOf(t);
  if(a==="sxs"){if(e.value)sxRouteSet(sc,P[1],e.value)}
  else if(a==="sxp")sxSet(sc,"review",sxToggle(sxVal(sc,"review"),P[1],e.checked));
  else if(a==="sxn"){var n=+e.value;if(e.value===""||n!==Math.round(n)||n<1||n>10)return sxSay("The verify limit is an integer from 1 to 10.",true);sxSet(sc,"max-verify-failures",n)}
  else if(a==="sxmon")sxEdit(c=>{c.models[P[1]][+P[2]].enabled=e.checked});
  else if(a==="hc"&&s){if(k==="jobs")sxSet("task","review",sxJobs(s.review.points,e.value));else sxSet("task",k,e.value)}
  else if(a==="hcp"&&s)sxSet("task","review",sxToggle(s.review.points,k,e.checked))});
// the level tabs: arrow keys move between Task, Project and Global (and never reach the task tabs in app.js)
D.addEventListener("keydown",ev=>{var e=ev.target;if(!e.dataset||e.dataset.act!=="sxt"||!/^(ArrowLeft|ArrowRight|Home|End)$/.test(ev.key))return;ev.preventDefault();ev.stopPropagation();
  var i=SXTABS.findIndex(x=>x[0]===e.dataset.k),n=SXTABS.length,k=ev.key;i=k==="Home"?0:k==="End"?n-1:(i+(k==="ArrowRight"?1:-1)+n)%n;
  SX.tab=SXTABS[i][0];LSs("sae-stab",SX.tab);sxSay("");sxLoad(true);renderMain();var b=D.querySelector('[data-act="sxt"][data-k="'+SX.tab+'"]');if(b)b.focus()},true);
// [?] popovers close on Esc (focus goes back to the button) and on an outside click (app.js)
D.addEventListener("keydown",ev=>{var p=$("#pop");if(ev.key==="Escape"&&!p.hidden&&p._b){p._b.setAttribute("aria-expanded","false");try{p._b.focus()}catch(e){}}},true);
D.addEventListener("scroll",ev=>{var p=$("#pop");if(!p.hidden&&!(ev.target.closest&&ev.target.closest("#pop"))){p.hidden=true;if(p._b)p._b.setAttribute("aria-expanded","false")}},true);
function help(btn){var p=$("#pop"),r=btn.getBoundingClientRect();if(!p.hidden&&p._b===btn){p.hidden=true;btn.setAttribute("aria-expanded","false");return}
  if(p._b)p._b.setAttribute("aria-expanded","false");p.innerHTML=HELP[btn.dataset.h||"card"]||"";p.hidden=false;p._b=btn;btn.setAttribute("aria-expanded","true");
  var w=p.offsetWidth,hh=p.offsetHeight,top=r.bottom+6;if(top+hh>W.innerHeight-8&&r.top-hh-6>8)top=r.top-hh-6;p.style.top=top+"px";p.style.left=Math.max(12,Math.min(r.left,W.innerWidth-w-12))+"px"}
