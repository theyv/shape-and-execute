/* sae viewer: data loading, palette, tabs, sidebar, Markdown, project switcher. Classic script:
   the three scripts share their top-level names; app.js loads first and boots on DOMContentLoaded. */
"use strict";
var D=document,W=window,$=s=>D.querySelector(s);
var TABS=[["overview","Overview"],["plan","Plan"],["jobs","Jobs"],["timeline","Timeline"],["reviews","Reviews"],["decisions","Decisions"],["spec","Intent & Spec"],["findings","Findings"]],
 PHASES=[["executing","Executing"],["planning","Planning"],["shaping","Shaping"],["done","Done"],["abandoned","Abandoned"]],
 WR={implementation:1,integration:1},RTP={shaping:"spec",planning:"plan"},
 KBP={shaping:["research","review"],planning:["planning","research","review"],executing:["research","implementation","integration","validation","review","decision"]},
 MODES=["full-auto","auto","critical-only","collaborative","interactive"],LEVELS=["economy","balanced","max"],POINTS=["spec","plan","selected-jobs","all-jobs","integration"],
 SK={interaction:["interaction"],research:["levels","research"],planning:["levels","planning"],execution:["levels","execution"],"review-level":["levels","review"],review:["review","points"],reviewer:["review","provider"],"max-verify-failures":["max_verify_failures"]},
 GL={pending:"○",ready:"▷",running:"◐",done:"●",parked:"‖",failed:"✕",removed:"–"},VC={pass:"done","pass-with-notes":"done","changes-required":"failed"},
 FILTERS=[["all","All"],["graph","Graph changes"],["decisions","Decisions"],["reviews","Reviews"],["settings","Settings"]],
 FT={graph:/^(job\.(added|changed|removed)|merge\.conflict)$/,decisions:/^(decision|amendment)$/,reviews:/^review\.completed$/,settings:/^settings\.changed$/},
 FAM=[["f-fail",/^(job\.verify_failed|merge\.conflict)$/],["f-job",/^(job|merge)\./],["f-review",/^review\./],["f-decision",/^(decision|amendment)$/],["f-gate",/^(spec|plan|execution|task)\./]],
 STALE=60, // minutes; mirrors STALE_RUNNING_MINUTES in sae_lib/common.py
 S={repo:null,task:null,tab:"overview",job:null,doc:null,f:"all",bl:null},IDX=null,PROJ=null,psig="",isig="",TASKS={},tsig={},timer=0,PSEQ=0,ED=null,MISS={},ERR="",OPEN={},FOLD={},OPENER="",
 TOKEN=(D.querySelector('meta[name="sae-token"]')||{}).content||"", // embedded by the server; sent with every change
 own=(o,k)=>o&&k!=null&&Object.prototype.hasOwnProperty.call(o,k)?o[k]:undefined,
 LSg=k=>{try{return localStorage.getItem(k)}catch(e){return null}},LSs=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
try{OPEN=JSON.parse(LSg("sae-open")||"{}")||{}}catch(e){}
try{FOLD=JSON.parse(LSg("sae-fold")||"{}")||{}}catch(e){}

/* ---------- text ---------- */
var esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>"&#"+c.charCodeAt(0)+";"),
 pad=n=>(n<10?"0":"")+n,
 fmt=iso=>{var d=new Date(iso);return iso&&!isNaN(d)?d.toLocaleDateString("en",{month:"short",day:"numeric"})+" "+pad(d.getHours())+":"+pad(d.getMinutes()):""},
 ago=iso=>{if(!iso)return"never";var m=Math.floor((Date.now()-Date.parse(iso))/6e4);return isNaN(m)?iso:m<1?"just now":m<120?m+" min ago":m<2880?Math.floor(m/60)+" h ago":Math.floor(m/1440)+" d ago"},
 agoH=iso=>'<span data-ago="'+esc(iso||"")+'" title="'+esc(fmt(iso))+'">'+esc(ago(iso))+"</span>",
 mins=iso=>(Date.now()-Date.parse(iso))/6e4,
 span=m=>m<120?Math.max(1,Math.round(m))+" min":m<2880?Math.floor(m/60)+" h":Math.floor(m/1440)+" d",
 active=iso=>!iso?"no activity yet":(mins(iso)<STALE?"active ":"last active ")+'<span data-ago="'+esc(iso)+'" title="'+esc(fmt(iso))+'">'+esc(ago(iso))+"</span>",
 clock=iso=>{var d=new Date(iso);return isNaN(d)?"":d.toDateString()===new Date().toDateString()?pad(d.getHours())+":"+pad(d.getMinutes()):fmt(iso)},
 num=n=>(n=+n||0)<1e4?n.toLocaleString("en"):n<1e6?(n/1e3).toFixed(1).replace(/\.0$/,"")+"K":(n/1e6).toFixed(1).replace(/\.0$/,"")+"M",
 dur=s=>{if(s==null)return"";var m=Math.round(s/60);return s<60?s+" s":m<60?m+" min":Math.floor(m/60)+" h "+m%60+" min"},
 code=s=>s==null||s===""?"":'<span class="mono">'+esc(s)+"</span>",
 shq=s=>(s=String(s),/^[\w@%+=:,.\/-]+$/.test(s)?s:"'"+s.replace(/'/g,"'\\''")+"'"),
 trunc=(s,n)=>(s=String(s),s.length>n?s.slice(0,n-1)+"…":s),
 plural=(n,w)=>n+" "+w+(n===1?"":"s"),
 slug=s=>String(s).replace(/^\d{4}-\d{2}-\d{2}-\d{4}--/,"");

/* ---------- data: mirrors sae's readiness rules (waits_for) ---------- */
var T=()=>own(TASKS,S.task)||null,
 IT=id=>IDX&&IDX.tasks.find(t=>t.id===id),
 JS=t=>t&&t.state&&t.state.jobs||{},
 JO=(t,id)=>own(JS(t),id),
 jf=(t,f)=>{var js=JS(t);return Object.keys(js).filter(k=>f(js[k],k))},
 evs=(t,re)=>(t.events||[]).filter(e=>re.test(e.type)),
 kindOk=(t,j)=>{var p=t.state.task.phase;return(KBP[p]||[]).includes(j.kind)&&(j.kind!=="review"||!RTP[p]||j.target===RTP[p])},
 waits=(t,id)=>{var js=JS(t),j=js[id],r=[],i=t.state.task,wt=i.git&&i.layout==="worktrees";
  j.needs.forEach(n=>{var o=js[n];if(!o)r.push(n+" (unknown job)");else if(o.status!=="done")r.push(n);else if(WR[o.kind]&&wt&&!o.merged&&j.target!==n)r.push(n+" (merge)")});
  if(j.final){var op=jf(t,(o,k)=>k!==id&&o.status!=="done");if(op.length)r.push("all other jobs: "+op.join(", "))}
  if(!kindOk(t,j))r.push("phase "+i.phase);return r},
 stOf=(t,id)=>{var j=JS(t)[id];return j.status==="pending"&&!waits(t,id).length?"ready":j.status},
 model=a=>a?a.model+(a.effort?" ("+a.effort+")":""):"",
 tierOf=a=>a.tier||a.rung||"", // attempts of old tasks name a rung
 lastA=j=>j.attempts&&j.attempts[j.attempts.length-1],
 byM=a=>a?esc(a.harness)+" "+code(model(a)):"",
 tokens=j=>(j.attempts||[]).reduce((s,a)=>s+(a.tokens||0),0),
 resultPath=(id,j)=>({research:"research/",review:"reviews/",decision:"decisions/"}[j.kind]||"jobs/")+id+(/^(research|review|decision)$/.test(j.kind)?".md":".result.md"),
 reviewsOf=(t,id)=>jf(t,j=>j.kind==="review"&&j.target===id),
 revInfo=(t,id)=>{var j=JS(t)[id],rs=reviewsOf(t,id),l=rs.length&&JS(t)[rs[rs.length-1]];return j.kind==="review"?{v:j.verdict}:l?l.verdict?{v:l.verdict}:{x:"in review"}:j.review?{x:"review due"}:{}},
 settingsOf=t=>{var s=t.settings;return s&&s.levels&&s.review&&Array.isArray(s.review.points)?s:null},
 vlimit=(t,s)=>s.max_verify_failures==null?t.settings_default_max_verify_failures:s.max_verify_failures,
 cdTo=it=>"cd "+shq(it&&it.checkout||IDX.root)+" && ",
 cmd=rest=>cdTo(IT(S.task))+IDX.sae+" "+rest,
 staleM=(t,id)=>{var j=JO(t,id),m=j&&j.status==="running"?mins(j.last_change):0;return m>=STALE?m:0},
 staleTip=(t,id)=>{var k=t.state.task.id;return"sae still marks this job running; the agent may have stopped. Run sae status "+k+", or restart it with sae dispatch "+k+" "+id+' --resume --reason "<why>".'},
 stale=(t,id)=>{var m=staleM(t,id);return m?'<span class="stl" title="'+esc(staleTip(t,id))+'">no activity for '+span(m)+"</span>":""};

/* ---------- markdown: escape first, no raw HTML ---------- */
var stripC=s=>String(s||"").replace(/<!--[\s\S]*?-->/g,""),
 unq=v=>String(v).trim().replace(/^(["'])(.*)\1$/,"$2"),
 front=s=>{s=String(s||"");var m=/^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(s),o={},key;if(!m)return[o,s];
  m[1].split(/\r?\n/).forEach(l=>{l=l.replace(/(^|\s)#.*$/,"").trimEnd();var it=/^\s*-\s+(.*)$/.exec(l),p=/^([A-Za-z_][\w-]*):\s*(.*)$/.exec(l);
   if(it&&key)(Array.isArray(o[key])?o[key]:o[key]=[]).push(unq(it[1]));
   else if(p){key=p[1];var v=p[2].trim();o[key]=/^\[.*\]$/.test(v)?v.slice(1,-1).split(",").map(unq).filter(Boolean):unq(v)}});
  return[o,s.slice(m[0].length)]},
 section=(text,title)=>{var out=[],inside=false,fence=false;String(text||"").split(/\r?\n/).some(l=>{if(/^\s*```/.test(l))fence=!fence;var m=!fence&&/^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(l);
  if(m){if(inside&&m[1].length<=2)return true;if(m[1].length===2&&m[2].trim().toLowerCase()===title.toLowerCase())return!(inside=true)}if(inside)out.push(l)});return inside?out.join("\n"):null},
 filled=s=>stripC(s).split(/\r?\n/).some(l=>(l=l.trim())&&!/^([-*]|- \[ \])$/.test(l)),
 dropEmpty=L=>{var keep=L.map(()=>true),fence=false,hd=[];
  L.forEach((l,i)=>{if(/^\s*```/.test(l))fence=!fence;else if(!fence){var m=/^(#{1,6})\s/.exec(l);if(m)hd.push([i,m[1].length]);if(/^\s*(?:[-*]|- \[ \])\s*$/.test(l))keep[i]=false}});
  hd.forEach((h,k)=>{if(h[1]===1)return;var end=L.length,j,x;for(j=k+1;j<hd.length;j++)if(hd[j][1]<=h[1]){end=hd[j][0];break}
   for(x=h[0]+1;x<end;x++)if(keep[x]&&L[x].trim()&&!/^#{1,6}\s/.test(L[x]))return;keep[h[0]]=false});
  return L.filter((_,i)=>keep[i])},
 // code spans and links become placeholders first, so emphasis never runs inside them
 inl=s=>{var cs=[],ls=[];s=esc(s).replace(/`([^`]+)`/g,(_,c)=>"\u0000"+(cs.push(c)-1)+"\u0000")
  .replace(/\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)/g,(_,t,u)=>"\u0001"+(ls.push(/^(https?:\/\/|mailto:|#)/i.test(u)?'<a href="'+u+'" target="_blank" rel="noopener">'+t+"</a>":t)-1)+"\u0001")
  .replace(/\[([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\]/g,'<span class="rid">$1</span>')
  .replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/(^|[^\w*])\*([^*\s][^*]*?)\*(?!\w)/g,"$1<em>$2</em>").replace(/(^|[^\w])_([^_\s][^_]*?)_(?!\w)/g,"$1<em>$2</em>");
  return s.replace(/\u0001(\d+)\u0001/g,(_,n)=>ls[n]).replace(/\u0000(\d+)\u0000/g,(_,n)=>"<code>"+cs[n]+"</code>")},
 cells=l=>l.trim().replace(/^\||\|$/g,"").split("|").map(c=>"<td>"+inl(c.trim())+"</td>").join(""),
 LI=/^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
function md(src,opt){opt=opt||{};var fm=front(src),L=dropEmpty(stripC(fm[1]).split(/\r?\n/)),h=[],P=[],i=0,amend=false,m,l;
  var flush=()=>{if(P.length)h.push("<p>"+P.map((l,k)=>(k?/^\*\*/.test(l)?"<br>":" ":"")+inl(l)).join("")+"</p>");P=[]};
  if(opt.meta!==false&&Object.keys(fm[0]).length)h.push('<dl class="fm">'+Object.keys(fm[0]).map(k=>{var v=fm[0][k];return"<dt>"+esc(k)+"</dt><dd>"+esc(Array.isArray(v)?v.join(", ")||"–":v)+"</dd>"}).join("")+"</dl>");
  while(i<L.length){l=L[i];
    if(/^\s*```/.test(l)){flush();var c=[];while(++i<L.length&&!/^\s*```/.test(L[i]))c.push(L[i]);i++;h.push("<pre><code>"+esc(c.join("\n"))+"</code></pre>")}
    else if(m=/^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(l)){flush();var lv=m[1].length;if(amend&&lv<=2){h.push("</div>");amend=false}
      h.push("<h"+lv+">"+inl(m[2])+"</h"+lv+">");if(opt.amend&&lv===2&&/^amendments$/i.test(m[2])){h.push('<div class="amend">');amend=true}i++}
    else if(/^\s*\|/.test(l)&&/^\s*\|?\s*:?-{3,}/.test(L[i+1]||"")){flush();var rows=[];i+=2;while(i<L.length&&/^\s*\|/.test(L[i]))rows.push("<tr>"+cells(L[i++])+"</tr>");
      h.push('<div class="tw"><table><thead><tr>'+cells(l).replace(/td>/g,"th>")+"</tr></thead><tbody>"+rows.join("")+"</tbody></table></div>")}
    else if(LI.test(l)){flush();var stk=[],o="";
      while(i<L.length){var it=LI.exec(L[i]);
        if(!it){if(/^\s+\S/.test(L[i])){o+=" "+inl(L[i++].trim());continue}if(!L[i].trim()&&LI.test(L[i+1]||"")){i++;continue}break}
        var d=Math.floor(it[1].replace(/\t/g,"  ").length/2),tg=/\d/.test(it[2])?"ol":"ul";
        while(stk.length>d+1)o+="</li></"+stk.pop()+">";if(stk.length===d+1)o+="</li>";else while(stk.length<d+1){o+="<"+tg+">";stk.push(tg)}
        var cb=/^\[([ xX])\]\s+(.*)$/.exec(it[3]);o+=cb?'<li class="cb"><span class="ck'+(cb[1]===" "?'" role="img" aria-label="open">':' on" role="img" aria-label="done">✓')+"</span><span>"+inl(cb[2])+"</span>":"<li>"+inl(it[3]);i++}
      while(stk.length)o+="</li></"+stk.pop()+">";h.push(o)}
    else if(/^\s*>/.test(l)){flush();var q=[];while(i<L.length&&/^\s*>/.test(L[i]))q.push(L[i++].replace(/^\s*>\s?/,""));h.push("<blockquote>"+md(q.join("\n"),{meta:false})+"</blockquote>")}
    else if(/^\s*(-{3,}|\*{3,})\s*$/.test(l)){flush();h.push("<hr>");i++}
    else{if(l.trim())P.push(l.trim());else flush();i++}}
  flush();if(amend)h.push("</div>");return'<div class="md">'+h.join("")+"</div>"}
// a file that still holds only the template: headings, comments and empty bullets
var DOCN={"intent.md":"Intent","specs.md":"Spec","brief.md":"Brief","plan.md":"Plan"},
 blankDoc=src=>!stripC(front(src)[1]).split(/\r?\n/).some(l=>(l=l.trim())&&!/^#{1,6}\s/.test(l)&&!/^([-*+]|\d+[.)]|- \[ \])$/.test(l)),
 notYet=f=>'<p class="mut nyw">'+(DOCN[f.split("/").pop()]||"This file")+" not written yet: the file still holds only the template.</p>",
 doc=(src,f,opt)=>{if(!blankDoc(src))return md(src,opt);var h=/^#\s+(.*)$/m.exec(stripC(front(src)[1]));return(h?'<div class="md"><h1>'+inl(h[1])+"</h1></div>":"")+notYet(f)};

/* ---------- small renderers ---------- */
var pill=s=>'<span class="pill k-'+s+'"><i aria-hidden="true">'+(GL[s]||"")+"</i>"+esc(s)+"</span>",
 vpill=v=>v?'<span class="pill k-'+(VC[v]||"pending")+'"><i aria-hidden="true">'+(v[0]==="c"?"✕":"✓")+"</i>"+esc(v)+"</span>":"",
 sp=h=>h?" "+h:"",
 stp=(t,id)=>{var j=JS(t)[id];return j.verdict?vpill(j.verdict):pill(stOf(t,id))+sp(stale(t,id))},
 jpill=(t,id)=>pill(stOf(t,id))+sp(stale(t,id))+(JS(t)[id].merged?' <span class="mut" title="merged">✓ merged</span>':""),
 php=p=>'<span class="php p-'+esc(p)+'"><i class="pd" aria-hidden="true">'+(p==="done"?"✓":p==="abandoned"?"–":"")+"</i>"+esc(p)+"</span>",
 fam=type=>(FAM.find(f=>f[1].test(type))||[""])[0],
 dataJ=(a,id)=>' data-act="'+a+'" data-id="'+esc(id)+'"',
 J=id=>id?'<button class="lnk mono"'+dataJ("job",id)+">"+esc(id)+"</button>":"",
 tgt=(t,x)=>JS(t)[x]?J(x):esc(x||""),
 empty=s=>'<div class="empty">'+s+"</div>",
 sec=(label,body,extra)=>'<section class="sec"><h2 class="lbl">'+label+(extra?' <span class="mut">'+extra+"</span>":"")+"</h2>"+body+"</section>",
 box=(rows,none)=>'<div class="box">'+(rows.length?rows.join(""):empty(none))+"</div>",
 line=(h,r)=>'<div class="row two"><span>'+h+"</span>"+(r?'<span class="r">'+r+"</span>":"")+"</div>",
 row=(c,left,main,right,sub,id)=>{var tg=id?"button":"div";return"<"+tg+' class="row '+c+'"'+(id?dataJ("job",id):"")+">"+left+'<span class="x">'+main+'</span><span class="r">'+(right||"")+"</span>"+(sub?'<span class="sub">'+sub+"</span>":"")+"</"+tg+">"},
 jrow=(t,id,sub,right)=>{var j=JS(t)[id];return row("fx",pill(stOf(t,id)),code(id)+' <span class="ink2">'+esc(j.summary?"— "+j.summary:"")+"</span>",right,sub,id)},
 tbl=(c,heads,rows)=>'<div class="box tw"><table class="'+c+'"><thead><tr>'+heads.split(",").map(h=>'<th class="'+({"~":"n","-":"hm"}[h[0]]||"")+'">'+h.replace(/^[~-]/,"")+"</th>").join("")+"</tr></thead><tbody>"+rows.join("")+"</tbody></table></div>",
 tr=(cells,attrs)=>"<tr"+(attrs||"")+">"+cells.map(c=>Array.isArray(c)?'<td class="'+c[0]+'">'+c[1]+"</td>":"<td>"+c+"</td>").join("")+"</tr>",
 dl=pairs=>'<dl class="kv">'+pairs.filter(p=>p[1]!==""&&p[1]!=null).map(p=>"<dt>"+p[0]+"</dt><dd>"+p[1]+"</dd>").join("")+"</dl>",
 cpi=(text,short)=>'<button class="cpi" data-act="copy" data-copy="'+esc(text)+'" aria-label="Copy command: '+esc(short)+'" title="Copy command: '+esc(short)+'"><svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5v-2a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2"/></svg></button>',
 cpy=(text,label)=>'<button class="btn sm" data-act="copy" data-copy="'+esc(text)+'">'+(label||"Copy command")+"</button>",
 dt=(k,label,body)=>'<details data-k="'+esc(k)+'"'+(OPEN[k]?" open":"")+"><summary><b>"+esc(label)+"</b></summary>"+body+"</details>",
 docs=(k,list,f)=>'<div class="box docs">'+list.map(d=>dt(k+d,d,/\.log$/.test(d)?'<pre class="log">'+esc(f[d])+"</pre>":doc(f[d],d))).join("")+"</div>",
 ask=(t,id)=>{var j=JS(t)[id],txt=t.files[resultPath(id,j)],s=txt&&section(front(txt)[1],"Decision request");if(!filled(s))return"";
  var ls=stripC(s).split(/\r?\n/).map(l=>l.trim()).filter(Boolean),q=ls.find(l=>/decision required/i.test(l));return q?inl(q):ls.slice(0,2).map(inl).join(" ")};
/* ---------- fixed palette ([DECISION-FIXED-COLORS]): discrete, never a gradient ----------
   A model takes the color of its place in its harness's model list (disabled entries counted, so
   unticking one never recolors the others); a tier the color of its number; an effort its word.
   `models` is the config's model lists ({claude: [{model, enabled, …}], codex: […]}), as the server
   sends them with each task (t.models) and with the settings. */
var EFFORTS=["low","medium","high","xhigh","max","ultra"],
 modelIndex=(models,h,m)=>((models&&models[h])||[]).findIndex(x=>x.model===m),
 modelColor=(models,h,m)=>{var i=modelIndex(models,h,m);return i<0?"var(--cx)":"var(--c"+Math.min(i,5)+")"},
 tierColor=name=>{var n=/^L(\d+)$/.exec(name||"");return n&&+n[1]>0?"var(--c"+Math.min(+n[1]-1,5)+")":"var(--cx)"},
 effortColor=e=>EFFORTS.includes(e)?"var(--e-"+(e==="ultra"?"max":e)+")":"var(--ink3)",
 // `ultra` is `max` with an underline
 effortWord=e=>'<span class="we'+(e==="ultra"?" u":"")+'" style="--ec:'+effortColor(e)+'">'+esc(e)+"</span>",
 modelWord=(models,h,m)=>'<span class="wm" style="--mc:'+modelColor(models,h,m)+'">'+esc(m)+"</span>",
 tierWord=name=>'<span class="wm" style="--mc:'+tierColor(name)+'">'+esc(name)+"</span>",
 routeWords=(models,h,m,e)=>'<span class="w">'+modelWord(models,h,m)+"<i> · </i>"+effortWord(e)+"</span>";

/* ---------- frame ---------- */
// the project switcher: every repository where sae has run ([VIEWER-SERVER])
function projectSwitch(){var P=PROJ||[],cur=P.find(x=>x.key===S.repo);if(P.length<2)return"<b>"+esc(cur?cur.name:IDX?IDX.repo:"sae")+"</b>";
  return'<select class="proj" data-act="proj" aria-label="Project">'+P.map(x=>'<option value="'+esc(x.key)+'"'+(x.key===S.repo?" selected":"")+' title="'+esc(x.path)+'">'+esc(x.name)+"</option>").join("")+"</select>"}
function renderTop(){var it=IT(S.task),th=D.documentElement.dataset.theme||"dark";
  $("#top").innerHTML='<button class="menu" data-act="side" aria-label="Tasks"><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" stroke-width="1.5"/></svg></button>'+
   '<div class="crumb">'+projectSwitch()+(it?'<span>/</span><span class="t">'+esc(it.title)+"</span>":"")+"</div>"+
   '<div class="live" title="Read live from the repository; this page asks again every few seconds.">'+(IDX?'<span class="hm">Last updated '+esc(clock(IDX.generated))+' · </span><span class="sm">Updated </span><span data-ago="'+esc(IDX.generated)+'">'+esc(ago(IDX.generated))+"</span>":"No data")+"</div>"+
   '<div class="seg" role="radiogroup" aria-label="Theme">'+["dark","light"].map(m=>'<button role="radio" data-act="theme" data-m="'+m+'" aria-checked="'+(th===m)+'">'+(m==="dark"?"Dark":"Light")+"</button>").join("")+"</div>"}
/* ---------- sidebar: collapsible sections, phase groups, a status bar per task ---------- */
var BAR=["done","running","parked","failed","pending"],
 shut=(k,n)=>own(FOLD,k)!=null?!!FOLD[k]:/^ph:(done|abandoned)$/.test(k)&&n>3,
 fold=(k,n,cls,label,cnt)=>'<button class="sx '+cls+'" data-act="fold" data-k="'+k+'" data-n="'+n+'" data-nav aria-expanded="'+!shut(k,n)+'"><svg class="cv" viewBox="0 0 10 10" aria-hidden="true"><path d="M3.5 2l3 3-3 3"/></svg>'+label+'<span class="n">'+cnt+"</span></button>",
 pmark=p=>'<i class="pd" aria-hidden="true">'+(p==="done"?"✓":p==="abandoned"?"–":"")+"</i>",
 since=(p,iso)=>p==="done"?"finished "+agoH(iso):p==="abandoned"?"abandoned "+agoH(iso):active(iso);
function renderSide(){if(!IDX){$("#side").innerHTML="";return}var ts=IDX.tasks,bl=IDX.backlog||[],
  item=(on,a,v,title,meta,more,cls)=>'<button class="ti'+(on?" on":"")+(cls||"")+'" data-act="'+a+'" data-'+(a==="bl"?"f":"id")+'="'+esc(v)+'" data-nav'+(on?' aria-current="true"':"")+'><span class="tt">'+esc(title)+'</span><span class="tm">'+meta+"</span>"+(more||"")+"</button>",
  h='<div class="ssec">'+fold("tasks",0,"top","Tasks",ts.length);
  if(!shut("tasks",0)){if(!ts.length)h+=empty("No tasks yet.");
    PHASES.forEach(p=>{var L=ts.filter(t=>t.phase===p[0]),k="ph:"+p[0],sh=shut(k,L.length);if(!L.length)return;
      h+='<div class="sgrp">'+fold(k,L.length,"p-"+p[0],pmark(p[0])+p[1],L.length);
      L.forEach(t=>{if(sh&&t.id!==S.task)return;var c=t.counts||{},tot=BAR.reduce((v,x)=>v+(c[x]||0),0),
        right=t.parked?pill("parked").replace("parked</span>",t.parked+" parked</span>"):p[0]==="planning"&&t.plan_approved?"<span>plan approved</span>":"",
        bar=tot?'<span class="sbw" title="'+esc(BAR.filter(x=>c[x]).map(x=>c[x]+" "+x).join(", "))+'"><span class="sbar">'+BAR.filter(x=>c[x]).map(x=>'<i class="k-'+x+'" style="flex:'+c[x]+'"></i>').join("")+"</span><b>"+(c.done||0)+"/"+tot+"</b></span>":"";
        h+=item(t.id===S.task,"task",t.id,t.title||t.id,"<span>"+since(p[0],t.last_change)+"</span>"+right,bar+(t.checkout?'<span class="tm mono" title="'+esc(t.checkout)+'">in …/'+esc(t.checkout.split(/[\\\/]/).pop())+"</span>":""),/^(done|abandoned)$/.test(p[0])?" mu":"")});
      h+="</div>"})}
  h+='</div><div class="ssec">'+fold("backlog",0,"top","Backlog",bl.length)+(shut("backlog",0)?"":bl.map(b=>item(S.bl===b.file,"bl",b.file,b.title,"<span>"+esc(ago(b.created)+(b.source?" · from "+slug(b.source):""))+"</span>")).join("")||empty("Empty."))+"</div>";
  $("#side").innerHTML=h}
function renderMain(){var m=$("#main"),it=IT(S.task),t=T(),cnt={},js=JS(t),h;
  if(!IDX||!it){m.innerHTML='<div class="wrap">'+empty(!IDX?(ERR?esc(ERR):PROJ&&!PROJ.length?"No repository yet. Run <code>sae view</code> in a repository.":"Loading…"):IDX.tasks.length?"Select a task.":"No tasks yet. Start one with <code>sae new</code>.")+"</div>";return}
  var s=t&&settingsOf(t);
  if(t){cnt.jobs=Object.keys(js).length;cnt.timeline=(t.events||[]).length;cnt.reviews=jf(t,j=>j.kind==="review").length;cnt.decisions=evs(t,FT.decisions).length+jf(t,j=>j.kind==="decision").length}
  cnt.findings=(IDX.findings||[]).length;
  h='<div class="wrap"><div class="th"><div><h1 title="'+esc(it.id)+'">'+esc(it.title)+'</h1><div class="meta">'+php(it.phase)+"<span>"+since(it.phase,it.last_change)+"</span><span>"+(it.branch?'<span class="mut">branch</span> '+code(it.branch):'<span class="mut">task</span> '+code(it.id))+"</span>"+(it.checkout?'<span title="'+esc(it.checkout)+'">in '+code("…/"+it.checkout.split(/[\\\/]/).slice(-2).join("/"))+"</span>":"")+"</div></div>"+
   '<div class="acts">'+(/done|abandoned/.test(it.phase)?"":'<button class="btn" data-act="settings"'+(s?"":" disabled")+">Edit settings</button>")+'<button class="btn ic" data-act="help" aria-label="About settings" aria-expanded="false">?</button></div></div>';
  if(t)h+='<div class="card" aria-label="Settings">'+(s?setPairs(t,s).map(p=>"<div><span>"+p[0]+"</span> <b>"+esc(p[1])+"</b></div>").join(""):"<span>settings.json is missing or invalid</span>")+"</div>";
  h+='<div class="tabs" role="tablist" aria-label="Task views">'+TABS.map(x=>{var on=S.tab===x[0];return'<button role="tab" id="tab-'+x[0]+'" aria-selected="'+on+'" tabindex="'+(on?0:-1)+'" data-act="tab" data-tab="'+x[0]+'">'+x[1]+(cnt[x[0]]?"<i>"+cnt[x[0]]+"</i>":"")+"</button>"}).join("")+"</div>";
  var gs=$(".gts"),gl=gs&&gs.scrollLeft;
  m.innerHTML=h+'<div class="tc" role="tabpanel" aria-labelledby="tab-'+S.tab+'">'+(S.tab==="findings"?TAB.findings():t?TAB[S.tab](t):empty(MISS[S.task]?"This task could not be read: "+esc(MISS[S.task]):"Loading…"))+"</div></div>";D.title=it.title+" · "+IDX.repo;
  // the timeline overview keeps its horizontal scroll; the first time it opens at the newest activity
  if((gs=$(".gts")))gs.scrollLeft=gl!=null?gl:gs.scrollWidth}
function renderPanel(){var p=$("#panel"),t=T(),h="",x='<button class="btn ic" data-act="close" aria-label="Close">✕</button>';
  if(S.bl&&IDX){var b=(IDX.backlog||[]).find(x=>x.file===S.bl),c=b&&cdTo(null)+IDX.sae+" new "+shq(b.title)+" --from "+b.file;if(b)h='<div class="ph"><h2 class="sans">'+esc(b.title)+"</h2>"+x+'</div><div class="meta">'+code(b.file)+"<span>"+agoH(b.created)+"</span>"+(b.source?"<span>from "+code(b.source)+"</span>":"")+"</div>"+
    sec("Start it as a task",'<div class="cmdrow"><pre class="cmd">'+esc(c)+"</pre>"+cpy(c,"Copy")+"</div>")+sec("Intent",blankDoc(b.text)?notYet("intent.md"):md(front(b.text)[1].replace(/^#\s.*$/m,""),{meta:false}))}
  else if(S.job&&t&&!/^(jobs|findings)$/.test(S.tab)){var j=JO(t,S.job),g=!j&&own(changes(t).r.removed,S.job);if(j||g)h='<div class="ph"><div><h2>'+esc(S.job)+'</h2><div class="meta">'+esc(j?j.kind+" · "+j.difficulty+(j.final?" · final":""):g.kind+" · removed")+"</div></div>"+x+'</div><div class="sec">'+jobBody(t,S.job)+"</div>"}
  p.hidden=!h;p.innerHTML=h}
var fkey=x=>x&&x.dataset?(x.dataset.act||"")+"|"+(x.dataset.id||x.dataset.tab||x.dataset.f||x.dataset.d||x.dataset.m||x.dataset.k||"")+"|"+(x.dataset.v||""):"",
 refocus=(root,k)=>{if(k&&k!=="||"){var e=[...root.querySelectorAll("[data-act]")].find(x=>fkey(x)===k);if(e)try{e.focus({preventScroll:true})}catch(_){}}};
function render(){var k=fkey(D.activeElement),ps=$("#panel").scrollTop;
  try{renderTop();renderSide();renderMain();renderPanel()}catch(e){$("#main").innerHTML='<div class="wrap"><p class="mut">This view could not be drawn: '+esc(e&&e.message||e)+". The page keeps reading new data.</p></div>"}
  $("#panel").scrollTop=ps;refocus(D,k)}

/* ---------- state, hash, polling ---------- */
function readHash(){var q={},dec=v=>{try{return decodeURIComponent(v)}catch(e){return""}};
  location.hash.slice(1).split("&").forEach(p=>{var k=p.split("=");if(k[0])q[dec(k[0])]=dec(k.slice(1).join("="))});
  S.repo=q.repo||null;S.task=q.task||null;S.tab=q.tab==="graph"?"plan":TABS.some(x=>x[0]===q.tab)?q.tab:"overview";S.job=q.job||null;S.doc=q.doc||null;S.f=own(FT,q.filter)?q.filter:"all";S.bl=q.backlog||null}
function writeHash(){var q=[["repo",S.repo],["task",S.task],["tab",S.tab!=="overview"&&S.tab],["job",S.job],["doc",S.tab==="spec"&&S.doc],["filter",S.tab==="timeline"&&S.f!=="all"&&S.f],["backlog",S.bl]].filter(p=>p[1]).map(p=>p[0]+"="+encodeURIComponent(p[1])).join("&");
  try{history.replaceState(null,"","#"+q)}catch(e){location.hash=q}}
function pickTask(){if(!IDX||IT(S.task))return;var ts=IDX.tasks;S.task=(ts.find(t=>t.phase==="executing")||ts.find(t=>!/done|abandoned/.test(t.phase))||ts[0]||{}).id||null}
// reads go to the server: GET /api/projects, /api/repo, /api/task (scripts/sae_lib/server.py)
var enc=encodeURIComponent,
 api=(path,cb)=>fetch(path,{cache:"no-store",credentials:"same-origin"}).then(r=>r.json().then(d=>r.ok?cb(d,""):cb(null,d&&d.error||"HTTP "+r.status),()=>cb(null,"HTTP "+r.status)),e=>cb(null,"The viewer server does not answer. Run sae view again. ("+(e&&e.message||e)+")")),
 // every change: POST /api/<route> with the token; the server runs the same sae command
 post=(route,body)=>fetch("/api/"+route,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-SAE-Token":TOKEN},body:JSON.stringify(Object.assign({repo:S.repo},body))})
  .then(r=>r.json().catch(()=>({ok:false,error:"HTTP "+r.status})),e=>({ok:false,error:"The viewer server does not answer: "+(e&&e.message||e)}));
// every callback ends in cb (the poll loop), even when drawing fails
function loadTask(cb){var id=S.task,rk=S.repo;if(!id||!rk)return cb&&cb();
  api("/api/task?repo="+enc(rk)+"&task="+enc(id),(t,err)=>{try{if(S.task!==id||S.repo!==rk)return;
    var ch=(t?t.version:"")!==(tsig[id]||"")||err!==(MISS[id]||"");if(t){TASKS[id]=t;tsig[id]=t.version}MISS[id]=err;if(ch)render()}finally{cb&&cb()}})}
var fastPoll=()=>!!(IDX&&IDX.tasks.some(t=>t.phase==="executing"));
// a newer poll (a project switch starts one) supersedes the older: its answers are dropped, never drawn
function poll(){clearTimeout(timer);if(D.hidden)return;var seq=++PSEQ;
  api("/api/projects",(p,err)=>{if(seq!==PSEQ)return;var rk=S.repo;if(p){if(p.version!==psig){psig=p.version;PROJ=p.projects}if(!PROJ.some(x=>x.key===S.repo))S.repo=(PROJ[0]||{}).key||null}
    if(!S.repo){IDX=null;ERR=err;render();return sched()}if(S.repo!==rk){IDX=null;isig=""}var asked=S.repo;
    api("/api/repo?repo="+enc(asked),(d,err2)=>{if(seq!==PSEQ||S.repo!==asked)return;try{ERR=err2;if(d&&d.version!==isig){isig=d.version;IDX=d;pickTask();writeHash()}if(d||err2)render()}finally{loadTask(sched)}})})}
function sched(){clearTimeout(timer);if(!D.hidden)timer=setTimeout(poll,fastPoll()?3000:30000)}
function go(patch){var tk=S.task,rk=S.repo;Object.assign(S,patch);writeHash();if(S.repo!==rk){IDX=null;isig="";render();return poll()}render();if(S.task!==tk)loadTask()}
function copy(text,btn){var o=btn.innerHTML,done=()=>{btn.innerHTML=btn.className==="cpi"?"✓":"Copied";setTimeout(()=>{btn.innerHTML=o},1200)},
  fb=()=>{var a=D.createElement("textarea"),ok=false;a.value=text;a.style.cssText="position:fixed;opacity:0";(btn.closest("dialog")||D.body).appendChild(a);a.select();try{ok=D.execCommand("copy")}catch(e){}a.remove();ok?done():W.prompt("Copy this command:",text)};
  if(navigator.clipboard&&W.isSecureContext)navigator.clipboard.writeText(text).then(done,fb);else fb()}
/* ---------- events ---------- */
var side=o=>$("#app").classList.toggle("so",o),
 panelOn=()=>!$("#panel").hidden,
 // the panel closes on ✕, Escape or a click outside it; focus goes back to what opened it
 closePanel=()=>{var k=OPENER;OPENER="";go({job:null,bl:null});refocus(D,k)},
 openPanel=(patch,e,ev)=>{if(!panelOn()||!e.closest("#panel"))OPENER=fkey(e);go(patch);if(ev.detail===0&&panelOn()){var c=$("#panel [data-act=close]");if(c)c.focus()}};
D.addEventListener("click",ev=>{var e=ev.target.closest("[data-act]"),p=$("#pop");if(!p.hidden&&!ev.target.closest("#pop")&&!(e&&e.dataset.act==="help"))p.hidden=true;
  var a=e&&e.dataset.act,id=e&&e.dataset.id,d=e&&e.dataset;
  if(panelOn()&&!ev.target.closest("#panel,#dlg,#pop")&&!/^(job|bl|row|theme|fold|side|copy|help)$/.test(a)){closePanel();if(!e)return}
  if(!e)return;
  if(a==="task"){side(false);go({task:id,job:null,bl:null})}
  else if(a==="tab"){side(false);go({tab:d.tab,job:S.tab===d.tab?S.job:null,bl:null})}
  else if(a==="job")openPanel({job:id,bl:null,tab:S.tab==="findings"?"plan":S.tab},e,ev);
  else if(a==="row")go({job:S.job===id?null:id});
  else if(a==="bl"){side(false);openPanel({bl:d.f,job:null},e,ev)}
  else if(a==="close")closePanel();
  else if(a==="fold"){FOLD[d.k]=!shut(d.k,+d.n||0);LSs("sae-fold",JSON.stringify(FOLD));renderSide();refocus($("#side"),fkey(e))}
  else if(a==="filter")go({f:d.f});
  else if(a==="doc")go({doc:d.d});
  else if(a==="side")side();
  else if(a==="theme"){D.documentElement.dataset.theme=d.m;LSs("sae-theme",d.m);renderTop()}
  else if(a==="copy")copy(d.copy,e);
  else if(a==="settings")openSettings();
  else if(a==="help")help(e);
  else if(a==="dclose")$("#dlg").close();
  else if(a==="sv")setv(d.k,d.v);
  else if(a==="save")save()});
D.addEventListener("change",ev=>{var e=ev.target,a=e.dataset&&e.dataset.act,F=ED&&ED.cur;if(a==="proj")return go({repo:e.value,task:null,job:null,bl:null});if(!F)return;
  if(a==="sel")setv(e.dataset.k,e.value);
  else if(a==="pt"){F.review=F.review.filter(x=>x!==e.dataset.k);if(e.checked)F.review.push(e.dataset.k);setv()}});
D.addEventListener("input",ev=>{var e=ev.target;if(!ED||!e.dataset||e.dataset.act!=="num")return;var v=+e.value;
  ED.bad=!(e.value!==""&&v===Math.round(v)&&v>=1&&v<=10);if(!ED.bad)ED.cur[e.dataset.k]=String(v);ED.msg=ED.bad?"The verify limit is an integer from 1 to 10.":"";ED.err=ED.bad;ED.path="";syncDlg()});
D.addEventListener("toggle",ev=>{var k=ev.target.dataset&&ev.target.dataset.k;if(k&&ev.target.tagName==="DETAILS"){if(ev.target.open)OPEN[k]=1;else delete OPEN[k];LSs("sae-open",JSON.stringify(OPEN))}},true);
D.addEventListener("keydown",ev=>{var e=ev.target,k=ev.key,i,n=TABS.length;
  if(k==="Escape"){$("#tip").hidden=true;if(!$("#pop").hidden)$("#pop").hidden=true;else if($("#app").classList.contains("so"))side(false);else if(!$("#dlg").open&&panelOn())closePanel();return}
  if((k==="Enter"||k===" ")&&e.matches("g.nd,tr[data-act]")){ev.preventDefault();e.dispatchEvent(new MouseEvent("click",{bubbles:true}))}
  else if(e.getAttribute("role")==="tab"&&/^(ArrowLeft|ArrowRight|Home|End)$/.test(k)){i=TABS.findIndex(x=>x[0]===S.tab);i=k==="Home"?0:k==="End"?n-1:(i+(k==="ArrowRight"?1:-1)+n)%n;ev.preventDefault();go({tab:TABS[i][0],job:null});$("#tab-"+TABS[i][0]).focus()}
  else if(e.closest("#side")&&/^Arrow(Down|Up)$/.test(k)){var L=[...D.querySelectorAll("#side [data-nav]")],j=L.indexOf(e);if(j>=0){ev.preventDefault();L[Math.max(0,Math.min(L.length-1,j+(k==="ArrowDown"?1:-1)))].focus()}}});
// timeline overview: one hover state per job row across the label column and the chart, and a tooltip for marks
var hov=null,rz=0;
D.addEventListener("mouseover",ev=>{var r=ev.target.closest&&ev.target.closest(".gt [data-row]"),k=r&&r.dataset.row||null;if(k===hov)return;hov=k;
  D.querySelectorAll(".gt .hov").forEach(x=>x.classList.remove("hov"));if(k)D.querySelectorAll(".gt [data-row]").forEach(x=>{if(x.dataset.row===k)x.classList.add("hov")})});
D.addEventListener("mousemove",ev=>{var el=ev.target.closest&&ev.target.closest("[data-tip]"),tp=$("#tip");if(!el){tp.hidden=true;tp._el=null;return}
  if(tp._el!==el){var L=el.dataset.tip.split("\n");tp.innerHTML="<b>"+esc(L[0])+"</b>"+(L.length>1?"\n"+esc(L.slice(1).join("\n")):"");tp._el=el;tp.hidden=false}
  var w=tp.offsetWidth,h=tp.offsetHeight,x=ev.clientX+14,y=ev.clientY+18;if(x+w>W.innerWidth-8)x=Math.max(8,ev.clientX-w-14);if(y+h>W.innerHeight-8)y=Math.max(8,ev.clientY-h-12);tp.style.left=x+"px";tp.style.top=y+"px"});
D.addEventListener("mouseleave",()=>{$("#tip").hidden=true});
W.addEventListener("resize",()=>{clearTimeout(rz);rz=setTimeout(()=>{if(S.tab==="timeline")renderMain()},150)});
W.addEventListener("hashchange",()=>{var tk=S.task,rk=S.repo;readHash();if(S.repo!==rk){IDX=null;isig="";render();return poll()}pickTask();render();if(S.task!==tk)loadTask()});
D.addEventListener("visibilitychange",()=>{if(D.hidden)clearTimeout(timer);else poll()});
setInterval(()=>D.querySelectorAll("[data-ago]").forEach(e=>{e.textContent=ago(e.dataset.ago)}),30000);
$("#dlg").addEventListener("close",()=>{ED=null;var p=$("#pop");p.hidden=true;D.body.appendChild(p)});

// classic scripts: task-views.js and settings.js are loaded when the document is parsed
D.addEventListener("DOMContentLoaded",()=>{readHash();render();poll()});
