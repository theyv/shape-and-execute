/* sae viewer: the settings card, the settings dialog and its saving through the server. */
"use strict";
var setPairs=(t,s)=>[["interaction",s.interaction],["research",s.levels.research],["planning",s.levels.planning],["execution",s.levels.execution],["review",s.review.points.length?s.review.points.join(", ")+" · "+s.levels.review+" · "+s.review.provider:"off"],["verify limit",vlimit(t,s)]];
/* ---------- settings dialog: saved through the server (POST /api/set runs sae set), or copied as a command ---------- */
var flat=(t,s)=>({interaction:s.interaction,research:s.levels.research,planning:s.levels.planning,execution:s.levels.execution,"review-level":s.levels.review,review:s.review.points.slice(),reviewer:s.review.provider,"max-verify-failures":String(vlimit(t,s))}),
 pts=F=>POINTS.filter(x=>F.review.includes(x)),
 sval=(F,k)=>k==="review"?pts(F).join(",")||"off":String(F[k]),
 edited=()=>Object.keys(SK).filter(k=>sval(ED.base,k)!==sval(ED.cur,k)),
 segH=(k,opts,v)=>'<div class="seg" role="radiogroup" aria-label="'+k+'">'+opts.map(o=>'<button role="radio" aria-checked="'+(v===o[0])+'" data-act="sv" data-k="'+k+'" data-v="'+o[0]+'">'+o[1]+"</button>").join("")+"</div>";
function openSettings(){var t=T(),s=t&&settingsOf(t);if(!s)return;ED={base:flat(t,s),cur:flat(t,s),msg:"",err:false};renderDlg();var d=$("#dlg");if(d.showModal&&!d.open)d.showModal()}
function renderDlg(){var t=T(),F=ED.cur,id=S.task,lv=LEVELS.map(x=>[x,x]),jr=F.review.includes("all-jobs")?"all-jobs":F.review.includes("selected-jobs")?"selected-jobs":"off";
  var rw=(k,label,ctl)=>'<div class="srow" data-k="'+k+'"><div class="k">'+label+"<span>"+k+'<span class="ed"></span></span></div><div class="c">'+ctl+"</div>"+cpi("","")+"</div>";
  $("#dlg").innerHTML='<div class="dh"><h2>Edit settings</h2><div class="acts"><button class="btn ic" data-act="help" aria-label="About settings" aria-expanded="false">?</button><button class="btn ic" data-act="dclose" aria-label="Close">✕</button></div></div><div>'+
    rw("interaction","Interaction",'<select data-act="sel" data-k="interaction" aria-label="Interaction">'+MODES.map(m=>"<option"+(m===F.interaction?" selected":"")+">"+m+"</option>").join("")+"</select>")+
    [["research","Research level"],["planning","Planning level"],["execution","Execution level"],["review-level","Review level"]].map(x=>rw(x[0],x[1],segH(x[0],lv,F[x[0]]))).join("")+
    rw("review","Review points",'<div class="cbs">'+["spec","plan","integration"].map(p=>'<label><input type="checkbox" data-act="pt" data-k="'+p+'"'+(F.review.includes(p)?" checked":"")+">"+p+"</label>").join("")+"</div>"+segH("jobs",[["off","No job reviews"],["selected-jobs","Selected jobs"],["all-jobs","All jobs"]],jr))+
    rw("reviewer","Reviewer",segH("reviewer",[["claude","claude"],["codex","codex"],["cross-harness","cross-harness"]],F.reviewer))+
    rw("max-verify-failures","Verify limit",'<input type="number" min="1" max="10" step="1" data-act="num" data-k="max-verify-failures" value="'+esc(F["max-verify-failures"])+'" aria-label="Failed verify runs before a job fails">')+
    '</div><div class="dmsg" role="status"><div class="dm"></div><div class="dp mono"></div></div><div class="df">'+
    cpy("","Copy all changes").replace('class="btn sm"','class="btn sm all"')+'<button class="btn pri" data-act="save">Save</button></div>';
  syncDlg()}
// updates the parts that follow the edits in place, so a control being typed in (and the Save button) keep their nodes
function syncDlg(){var d=$("#dlg"),F=ED.cur,ch=edited(),id=S.task,q=x=>d.querySelector(x),setc=(b,c,short)=>{b.dataset.copy=c;if(short){b.title="Copy command: "+short;b.setAttribute("aria-label",b.title)}};
  d.querySelectorAll(".srow[data-k]").forEach(r=>{var k=r.dataset.k,rest="set "+id+" "+k+"="+sval(F,k);r.querySelector(".ed").textContent=ch.includes(k)?" · edited":"";setc(r.querySelector(".cpi"),cmd(rest),"sae "+rest)});
  var all=q(".all");all.hidden=!ch.length;setc(all,cmd("set "+id+" "+ch.map(k=>k+"="+sval(F,k)).join(" ")));
  q("[data-act=save]").disabled=!ch.length||!!ED.bad||!!ED.busy;
  var m=ED.msg;
  q(".dmsg").hidden=!m&&!ED.path;q(".dm").textContent=m;q(".dm").className="dm"+(ED.err?" err":"");q(".dp").textContent=ED.path||"";q(".dp").hidden=!ED.path}
function setv(k,v,msg){var F=ED.cur;if(k==="jobs"){F.review=F.review.filter(x=>!/-jobs$/.test(x));if(v!=="off")F.review.push(v)}else if(k)F[k]=v;ED.msg=msg||"";ED.err=!!msg;ED.path="";ED.bad=false;var f=fkey(D.activeElement);renderDlg();refocus($("#dlg"),f)}
// the server runs `sae set <task> key=value …`: the same validation, lock and event (by: viewer)
function save(){var t=T(),id=S.task,ch=edited(),F=ED&&ED.cur,
  msg=(m,err,path)=>{if(!ED)return;ED.msg=m;ED.err=!!err;ED.path=path||"";syncDlg()};
  if(!F||!ch.length||ED.busy)return;ED.busy=true;msg("Saving…");
  post("set",{task:id,pairs:ch.map(k=>k+"="+sval(F,k))}).then(r=>{if(!ED)return;ED.busy=false;
    if(!r.ok)return msg(r.error||"Not saved.",true,r.command);
    var s=r.result&&r.result.settings;if(s&&TASKS[id])TASKS[id].settings=s;
    if(s){ED.base=flat(t,s);ED.cur=flat(t,s)}render();renderDlg();msg("Saved. It applies from the next dispatch.",false,r.command);loadTask()})}
var HELP="<p>Settings live on three levels.</p><p><b>Global</b> — your user config: the model lists, tiers and routing tables of Claude and Codex, and the defaults for new tasks. Change it with the skill's setup mode.</p><p><b>Project</b> — your own defaults for new tasks in this repository, kept in the user config (sae project set).</p><p><b>This task</b> — <code>settings.json</code>: interaction mode, the level of each phase, review points, review provider, and how many failed checks a job may have before it is marked failed. You can change them here. The next dispatch uses the new values.</p>";
function help(btn){var p=$("#pop"),r=btn.getBoundingClientRect(),d=btn.closest("dialog")||D.body;if(!p.hidden&&p._b===btn){p.hidden=true;btn.setAttribute("aria-expanded","false");return}
  if(p.parentNode!==d)d.appendChild(p);p.innerHTML=HELP;p.hidden=false;p._b=btn;btn.setAttribute("aria-expanded","true");var w=p.offsetWidth;p.style.top=r.bottom+6+"px";p.style.left=Math.max(12,Math.min(r.right-w,W.innerWidth-w-12))+"px"}
