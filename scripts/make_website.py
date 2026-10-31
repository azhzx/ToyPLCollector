#!/usr/bin/env python3
"""Build the ToyPLCollector website as a zero-dependency static bundle.

Output layout (default ``_site``)::

    _site/
      index.html            card gallery — logo + name tiles, grouped A-Z / 中文 / 其他
      play/<slug>.html      one detail page per language (merged with its playground)
      wasm-runner.js        shared loader implementing the toypl wasm ABI

The index embeds every entry as JSON and does grouping + sorting (A-Z, 中文
pinyin, 其他) client-side via Intl.Collator, so no build-time locale is needed.
Both pages ship an EN/中文 toggle persisted in localStorage (falls back to the
browser language).

Run locally::

    python3 scripts/make_website.py            # writes to _site/
    python3 scripts/make_website.py --out /tmp/site

"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import plc

GITHUB_URL = "https://github.com/azhzx/ToyPLCollector"
CONTRIB_URL = f"{GITHUB_URL}/blob/main/CONTRIBUTING.md"
CONTRIB_URL_ZH = f"{GITHUB_URL}/blob/main/CONTRIBUTING.zh-CN.md"

#: Custom domain for GitHub Pages. With the Actions deploy flow the CNAME
#: file must ship inside the uploaded artifact, so the build writes it out.
SITE_DOMAIN = "coll.i2pl.com"

#: Maintainer-provided playground runtimes. `assets/wasm/*.wasm` is copied
#: into the site (same-origin hosting, so no CORS is involved).
ASSETS_WASM_DIR = plc.REPO_ROOT / "assets" / "wasm"

# --------------------------------------------------------------------------
# tiny helpers
# --------------------------------------------------------------------------


def js_json(data: Any) -> str:
    """JSON that is safe to inline into a ``<script>`` block."""
    s = json.dumps(data, ensure_ascii=False, indent=None).replace("</", "<\\/")
    return s


def collect(coll_dir: Path) -> list[dict]:
    """Load every valid entry; abort loudly on a broken one."""
    langs: list[dict] = []
    seen: dict[str, str] = {}
    for path in sorted(coll_dir.glob("*.toml")):
        lang, err = plc.load_language(path)
        if lang is None:
            raise SystemExit(f"error: {path}: {err}\n(Fix it, or run `python3 scripts/validate.py` for details)")
        name = str(lang["name"])
        if name in seen:
            raise SystemExit(f"error: duplicate language '{name}' in both {seen[name]} and {path}")
        seen[name] = str(path)
        lang["_file"] = path.name
        langs.append(lang)

    # deterministic embed order; the page itself re-sorts into A-Z / 中文 / 其他
    langs.sort(key=lambda l: str(l["name"]))
    if not langs:
        raise SystemExit(f"error: no .toml under {coll_dir}")
    return langs


# --------------------------------------------------------------------------
# styles  (light, warm, orange accent)
# --------------------------------------------------------------------------

CSS = """
:root{
  --bg:#faf8f4;--panel:#ffffff;--panel2:#f4f0e8;--code:#fcfaf5;
  --line:#e9e2d4;--line-strong:#ddd3c2;
  --ink:#2c2921;--muted:#71695b;--faint:#a49b8a;
  --accent:#e8611a;--accent-strong:#c94f0f;--accent-soft:#fdeee1;
  --warn:#b45309;
  --mono:ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;
  --radius:16px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
html,body{margin:0;padding:0}
body{background:
    radial-gradient(900px 460px at 10% -8%,rgba(232,97,26,.05),transparent 60%),
    radial-gradient(760px 420px at 96% -6%,rgba(214,125,27,.04),transparent 55%),
    var(--bg);
  background-attachment:fixed;color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--accent-strong);text-decoration:none}
a:hover{color:var(--accent);text-decoration:underline}
::selection{background:rgba(232,97,26,.22)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
[hidden]{display:none!important}
label.sr{position:absolute;left:-9999px}

/* ---- top bar ---- */
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:13px 26px;border-bottom:1px solid var(--line);
  background:color-mix(in srgb,#ffffff 74%,transparent);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.brand{font-weight:800;font-size:17px;letter-spacing:.01em;color:var(--ink);display:flex;align-items:center;gap:9px}
.brand:hover{text-decoration:none;color:var(--ink)}
.brand .pl{color:var(--accent)}
.search{flex:1 1 300px;max-width:540px;display:flex;gap:8px;align-items:center;min-width:0}
.search select{flex:none;max-width:150px;padding:10px 26px 10px 14px;border-radius:999px;border:1px solid var(--line);
  background-color:#ffffff;color:var(--ink);font-size:13px;font-family:inherit;cursor:pointer;
  appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23a49b8a' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 11px center;
  transition:border-color .15s,box-shadow .15s}
.search select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(232,97,26,.13)}
.search input{flex:1 1 120px;min-width:0;padding:10px 16px;border-radius:999px;border:1px solid var(--line);
  background:#ffffff;color:var(--ink);font-size:14px;transition:border-color .15s,box-shadow .15s}
.search input::placeholder{color:var(--faint)}
.search input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(232,97,26,.13)}
.topbar .count{margin-left:auto;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap}
.topbar nav{display:flex;gap:14px;font-size:14px;align-items:center}
.topbar nav a{color:var(--muted)}
.topbar nav a:hover{color:var(--ink);text-decoration:none}

/* ---- chips ---- */
.chips{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{display:inline-flex;align-items:center;gap:5px;padding:3px 11px;border-radius:999px;font-size:12px;
  border:1px solid var(--line);background:var(--panel2);color:var(--muted);white-space:nowrap}
.chip.k{color:var(--accent-strong);background:var(--accent-soft);border-color:#f3cdb0}
.chip.p{color:#837760;background:#ffffff;border-color:var(--line-strong)}
.chip.x{font-family:var(--mono);color:#5f6f8a;background:#f0f2f6;border-color:#d8dee9}
button.chip{cursor:pointer;font-family:inherit;font-size:12.5px;padding:5px 13px;transition:border-color .15s,color .15s,background .15s}
button.chip:hover{border-color:var(--accent);color:var(--ink)}

/* ---- gallery ---- */
main{padding:26px;max-width:1200px;margin:0 auto}
.group{margin:10px 0 36px}
.group>h2{display:flex;align-items:center;gap:10px;margin:0 0 14px;font-size:13px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.group>h2 .gcount{font-weight:500;letter-spacing:.05em;color:var(--faint);font-size:12px}
.group>h2::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.tile{display:flex;flex-direction:column;align-items:center;gap:12px;padding:24px 12px 18px;text-align:center;
  color:var(--ink);border-radius:var(--radius);border:1px solid var(--line);background:var(--panel);
  box-shadow:0 1px 2px rgba(80,50,10,.04);
  transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease}
.tile:hover{transform:translateY(-4px);border-color:#f0b489;
  box-shadow:0 14px 30px rgba(150,80,20,.13);text-decoration:none;color:var(--ink)}
.tile .tname{font-weight:600;font-size:14.5px;line-height:1.35;max-width:100%;word-break:break-word;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.logo{display:inline-flex;align-items:center;justify-content:center;flex:none;font-weight:800;
  color:#ffffff;user-select:none}
img.logo{object-fit:contain;background:#ffffff}
.tile .logo{width:72px;height:72px;border-radius:18px;font-size:34px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}
.tile img.logo{padding:7px}
.fb{text-shadow:0 1px 2px rgba(0,0,0,.18)}
.g0{background:linear-gradient(135deg,#f5a068,#d95f14)}
.g1{background:linear-gradient(135deg,#7cc9a4,#3d9c72)}
.g2{background:linear-gradient(135deg,#f0a0b8,#c75d84)}
.g3{background:linear-gradient(135deg,#efc069,#c98a2e)}
.g4{background:linear-gradient(135deg,#b7a6ee,#8266d5)}
.g5{background:linear-gradient(135deg,#7fbde8,#4a86c9)}
.muted{color:var(--muted)}
.empty{padding:70px 0;text-align:center;color:var(--muted)}

/* ---- detail / play page ---- */
.play main{max-width:880px;padding-bottom:56px}
.hero{display:flex;gap:20px;align-items:flex-start;margin:30px 0 4px;flex-wrap:wrap}
.hero-logo{width:84px;height:84px;flex:none}
.hero-logo .logo{width:84px;height:84px;border-radius:20px;font-size:40px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}
.hero-logo img.logo{padding:9px}
.hero-main{flex:1 1 320px}
.hero h1{margin:0 0 8px;font-size:clamp(24px,4vw,32px);letter-spacing:-.01em;
  display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hero .slug{font-family:var(--mono);font-size:12.5px;font-weight:500;color:var(--muted);
  border:1px solid var(--line);background:#ffffff;border-radius:8px;padding:2px 9px}
.hero .desc{margin:0;color:var(--muted);max-width:70ch}
.hero .actions{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 15px;border-radius:10px;font-weight:600;
  font-size:13.5px;border:1px solid var(--line);color:var(--muted);background:#ffffff;transition:color .15s,border-color .15s}
.btn:hover{color:var(--accent-strong);border-color:var(--accent);text-decoration:none}
.btn.sm{padding:4px 11px;font-size:12px;border-radius:8px}
.meta{margin:24px 0 0;display:flex;flex-direction:column;gap:10px}
.meta-row{display:grid;grid-template-columns:96px 1fr;column-gap:14px;row-gap:5px;align-items:baseline}
.mlabel{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}

/* ---- shared panels ---- */
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin-top:22px;
  box-shadow:0 2px 10px rgba(120,80,30,.05)}
.panel-head{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.panel-head span{font-size:12px;color:var(--faint);font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.panel-head .sp{flex:1}
pre{margin:0;padding:14px;background:var(--code);border:1px solid var(--line);border-radius:12px;overflow:auto;
  font-family:var(--mono);font-size:12.5px;line-height:1.55;color:#45403a}
textarea#code{width:100%;min-height:270px;resize:vertical;background:var(--code);color:#45403a;
  border:1px solid var(--line);border-radius:12px;padding:14px;font-family:var(--mono);font-size:13px;line-height:1.6;
  tab-size:4;white-space:pre;overflow:auto}
textarea#code:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(232,97,26,.12)}
.runbar{display:flex;align-items:center;gap:14px;margin-top:13px;flex-wrap:wrap}
button.primary{background:var(--accent);color:#ffffff;border:none;border-radius:10px;padding:10px 26px;
  font-weight:700;font-size:14px;cursor:pointer;letter-spacing:.01em;transition:background .15s,transform .08s}
button.primary:hover{background:var(--accent-strong)}
button.primary:active{transform:scale(.98)}
button.primary:disabled{opacity:.45;cursor:not-allowed}
#status{font-size:13px;color:var(--muted)}
#status.err{color:var(--warn)}
#out{max-height:420px;min-height:64px}
.srcinfo{margin-top:16px;font-size:12px;color:var(--faint);word-break:break-all}

footer{padding:28px 26px 46px;color:var(--muted);font-size:13px;text-align:center;border-top:1px solid var(--line);margin-top:34px}
footer code{font-family:var(--mono);background:var(--panel2);padding:1px 6px;border-radius:6px}

@media (max-width:620px){
  main{padding:16px}
  .topbar{padding-left:16px;padding-right:16px}
  .grid{grid-template-columns:repeat(auto-fill,minmax(118px,1fr))}
  .meta-row{grid-template-columns:1fr}
  .hero{margin-top:20px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}}
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
__METATAGS__
<style>__CSS__</style>
</head>
"""

INDEX_TEMPLATE = HEAD + """<body>
<header class="topbar">
  <a class="brand" href="index.html"><span class="name">Toy<span class="pl">PL</span>Collector</span></a>
  <span class="search">
    <label class="sr" for="field">Search field</label>
    <select id="field"></select>
    <label class="sr" for="q">Search</label>
    <input id="q" type="search" autocomplete="off">
  </span>
  <span id="count" class="count"></span>
  <nav>
    <button id="lang" class="chip" type="button" aria-label="Switch language / 切换语言"></button>
    <a href="__GITHUB_URL__" target="_blank" rel="noopener">GitHub</a>
    <a id="nav-add" href="__CONTRIB_URL__" target="_blank" rel="noopener">Add your language →</a>
  </nav>
</header>
<main id="cards"><noscript><p class="empty">Please enable JavaScript to browse the gallery ｜ 请启用 JavaScript 浏览。</p></noscript></main>
<footer>
  <span id="f-gen"></span> <code>collections/*.toml</code> <span id="f-mid"></span>
  <a id="f-link" href="__CONTRIB_URL__" target="_blank" rel="noopener"></a>.
  <span id="f-built"></span> <span id="builtat">__BUILT_AT__</span>
</footer>
<script>const LANGS=__LANGS__;</script>
<script>
(function(){
"use strict";
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const enColl=new Intl.Collator("en",{sensitivity:"base",numeric:true});
let zhColl=null;
try{zhColl=new Intl.Collator("zh-u-co-pinyin",{numeric:true});}catch(e){}
const GROUP_ORDER=["en","zh","other"];
 const UI={
 en:{
  htmlLang:"en",
  title:"ToyPLCollector — a gallery of toy programming languages",
  fields:{all:"All fields",kw:"Keywords",name:"Name",ext:"Extension",platform:"Platform"},
  ph:{all:"Search all fields…",kw:"Search keywords…",name:"Search by name…",ext:"Search by extension…",platform:"Search platforms…"},
  count:(n,m)=>`${n} / ${m} languages`,
  groups:{en:"A–Z",zh:"Chinese",other:"Other"},
  noMatch:q=>`No language matches “${q}”.`,
  navAdd:"Add your language →",
  contrib:"__CONTRIB_URL__",
  fGen:"Generated from",fMid:"— have a toy language of your own?",fLink:"Submit it with a PR",fBuilt:"Built at"
 },
 zh:{
  htmlLang:"zh-CN",
  title:"ToyPLCollector — 玩具编程语言图鉴",
  fields:{all:"全部字段",kw:"关键词",name:"名称",ext:"后缀",platform:"平台"},
  ph:{all:"搜索全部字段…",kw:"搜索关键词…",name:"按名称搜索…",ext:"按后缀搜索…",platform:"搜索平台…"},
  count:(n,m)=>`${n} / ${m} 门语言`,
  groups:{en:"A–Z",zh:"中文",other:"其他"},
  noMatch:q=>`没有匹配“${q}”的语言。`,
  navAdd:"提交你的语言 →",
  contrib:"__CONTRIB_URL_ZH__",
  fGen:"由",fMid:"生成 —— 有自己写的玩具语言？",fLink:"用 PR 提交它",fBuilt:"构建于"
 }
};
let lang=null;
try{lang=localStorage.getItem("tplc-lang");}catch(e){}
if(lang!=="en"&&lang!=="zh"){
  lang=(navigator.language&&navigator.language.indexOf("zh")===0)?"zh":"en";
}

function initial(l){
  const s=String(l.display_name||l.name||"?").trim();
  return [...s][0]||"?";
}
function groupOf(l){
  const c=initial(l);
  if(/[\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff]/.test(c))return "zh";
  if(/[a-z]/i.test(c))return "en";
  return "other";
}
function gclass(l){
  let h=7;
  for(const ch of String(l.name))h=(h*31+ch.codePointAt(0))>>>0;
  return "g"+(h%6);
}
function textOf(l){
  return [l.name,l.display_name,l.description,String(l.year||""),
    ...(l.keywords||[]),...(l.platforms||[]),...(l.file_extensions||[])]
    .join(" ").toLowerCase();
}
function logoHTML(l){
  return l.logo
    ?`<img class="logo" src="${esc(l.logo)}" alt="" loading="lazy">`
    :`<span class="logo fb ${gclass(l)}">${esc(initial(l))}</span>`;
}
function tileHTML(l){
  return `<a class="tile" href="play/${esc(l.name)}.html" title="${esc(l.display_name)}">`+
    logoHTML(l)+`<span class="tname">${esc(l.display_name)}</span></a>`;
}

const FIELD_ORDER=["all","kw","name","ext","platform"];

let query="",field="all";

function matches(l){
  if(!query)return true;
  if(field==="kw")return (l.keywords||[]).some(k=>k.toLowerCase().includes(query));
  if(field==="name")return ((l.name||"")+" "+(l.display_name||"")).toLowerCase().includes(query);
  if(field==="ext")return (l.file_extensions||[]).some(e=>("."+e).toLowerCase().includes(query)||e.toLowerCase().includes(query));
  if(field==="platform")return (l.platforms||[]).some(p=>p.toLowerCase().includes(query));
  return textOf(l).includes(query);
}

function filtered(){
  return LANGS.filter(matches);
}

function render(){
  const t=UI[lang];
  const list=filtered();
  const by={en:[],zh:[],other:[]};
  for(const l of list)by[groupOf(l)].push(l);
  const cmp=(a,b)=>{
    const ka=a.display_name||a.name,kb=b.display_name||b.name;
    const c=(groupOf(a)==="zh"&&zhColl)?zhColl.compare(ka,kb):enColl.compare(ka,kb);
    return c||enColl.compare(a.name,b.name);
  };
  by.en.sort(cmp);by.zh.sort(cmp);by.other.sort(cmp);
  let html="";
  for(const key of GROUP_ORDER){
    if(!by[key].length)continue;
    html+=`<section class="group"><h2>${t.groups[key]}<span class="gcount">${by[key].length}</span></h2>`+
      `<div class="grid">${by[key].map(tileHTML).join("")}</div></section>`;
  }
  $("#cards").innerHTML=html||`<p class="empty">${t.noMatch(query)}</p>`;
  $("#count").textContent=t.count(list.length,LANGS.length);
}

function initFieldSelect(){
  const t=UI[lang];
  const sel=$("#field");
  const prev=sel.value||field;
  sel.innerHTML=FIELD_ORDER.map(k=>`<option value="${k}">${esc(t.fields[k])}</option>`).join("");
  sel.value=FIELD_ORDER.includes(prev)?prev:"all";
  field=sel.value;
  $("#q").placeholder=t.ph[field];
}

function applyLang(){
  const t=UI[lang];
  document.documentElement.lang=t.htmlLang;
  document.title=t.title;
  $("#q").placeholder=t.ph[field];
  $("#nav-add").textContent=t.navAdd;
  $("#nav-add").href=t.contrib;
  $("#f-gen").textContent=t.fGen;
  $("#f-mid").textContent=t.fMid;
  $("#f-link").textContent=t.fLink;
  $("#f-link").href=t.contrib;
  $("#f-built").textContent=t.fBuilt;
  $("#lang").textContent=lang==="en"?"中文":"EN";
  initFieldSelect();render();
}

$("#lang").addEventListener("click",()=>{
  lang=lang==="en"?"zh":"en";
  try{localStorage.setItem("tplc-lang",lang);}catch(e){}
  applyLang();
});
$("#field").addEventListener("change",e=>{
  field=e.target.value;
  $("#q").placeholder=UI[lang].ph[field];
  render();
});
$("#q").addEventListener("input",e=>{query=e.target.value.trim().toLowerCase();render();});
applyLang();
})();
</script>
</body>
</html>
"""

PLAY_TEMPLATE = HEAD + """<body class="play">
<header class="topbar">
  <a class="brand" href="../index.html">← <span class="name">Toy<span class="pl">PL</span>Collector</span></a>
  <nav>
    <button id="lang" class="chip" type="button" aria-label="Switch language / 切换语言"></button>
    <a href="__GITHUB_URL__" target="_blank" rel="noopener">GitHub</a>
  </nav>
</header>
<main>
  <div class="hero">
    <span class="hero-logo" id="llogo"></span>
    <div class="hero-main">
      <h1><span id="ltitle"></span><span class="slug" id="lslug" hidden></span><span class="chip" id="lyear" hidden></span></h1>
      <p class="desc" id="ldesc"></p>
      <div class="actions">
        <a class="btn" id="btn-repo" href="#" target="_blank" rel="noopener">Code ↗</a>
        <a class="btn" id="btn-doc" href="#" target="_blank" rel="noopener">Docs ↗</a>
      </div>
    </div>
  </div>
  <div class="meta">
    <div class="meta-row" id="row-kw" hidden><span class="mlabel" id="mlabel-kw"></span><div class="chips" id="lkw"></div></div>
    <div class="meta-row" id="row-pl" hidden><span class="mlabel" id="mlabel-pl"></span><div class="chips" id="lpl"></div></div>
    <div class="meta-row" id="row-ex" hidden><span class="mlabel" id="mlabel-ex"></span><div class="chips" id="lex"></div></div>
  </div>
  <section class="panel">
    <div class="panel-head"><span id="lbl-play"></span><div class="sp"></div>
      <button class="btn sm" id="reset"></button>
      <button class="btn sm" id="copysrc"></button>
    </div>
    <textarea id="code" spellcheck="false" aria-label="source code"></textarea>
    <div class="runbar" id="runbar">
      <button id="run" class="primary"></button>
      <span id="status"></span>
    </div>
  </section>
  <section class="panel" id="panel-out">
    <div class="panel-head"><span id="lbl-out"></span></div>
    <pre id="out" aria-live="polite"></pre>
  </section>
  <p class="srcinfo" id="srcinfo"></p>
</main>
<footer>
  <span id="f-gen"></span> <code>collections/*.toml</code> <span id="f-mid"></span>
  <a id="f-link" href="__CONTRIB_URL__" target="_blank" rel="noopener"></a>.
</footer>
<script>window.LANG=__LANG__;</script>
<script src="../wasm-runner.js"></script>
</body>
</html>
"""

RUNNER_JS = r"""/* ToyPLCollector — universal wasm playground runner.
 *
 * Implements the "toypl" wasm ABI that languages opt into
 * (see CONTRIBUTING.md):
 *
 *   exports: memory, alloc(size:i32) -> ptr:i32, run(ptr:i32, len:i32) -> i32
 *   imports: toypl.output(ptr:i32, len:i32), toypl.exit(code:i32)
 *
 * Flow: page writes the UTF-8 source into the module's memory via alloc(),
 * calls run(), and streams whatever the module sends back through output().
 * The compiled module is cached per page session — later runs instantiate a
 * fresh Instance (clean memory) without re-downloading or recompiling.
 *
 * This script also fills the detail page (logo, name, chips, links) from the
 * LANG JSON embedded by the page, and drives its EN/中文 toggle.
 */
(function () {
  "use strict";

  var LANG = window.LANG || {};
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var UI = {
    en: {
      title: function (dn) { return dn + " Playground — ToyPLCollector"; },
      contrib: "__CONTRIB_URL__",
      playground: "Playground", sample: "Sample code", output: "Output",
      reset: "↺ reset", copy: "copy", copied: "copied!", run: "▶ Run",
      kw: "Keywords", pl: "Platforms", ex: "Extensions",
      downloading: "Downloading wasm…", running: "Running…",
      done: function (ms, code) { return "done in " + ms + " ms · exit code " + code; },
      failed: "Run failed: ",
      srcinfo: "Playground wasm: ",
      fLink: "Submit it with a PR",
      notAbi: "this wasm does not follow the ToyPLCollector ABI — required exports: memory, alloc(size)->ptr, run(ptr,len)->i32 (see CONTRIBUTING.md)",
      wasi: "wasm needs imports this page does not provide — it is probably a WASI module; languages must use the toypl ABI (see CONTRIBUTING.md)",
      cors: "wasm blocked by CORS — the host must send Access-Control-Allow-Origin (try raw.githubusercontent.com or cdn.jsdelivr.net)"
    },
    zh: {
      title: function (dn) { return dn + " 在线运行 — ToyPLCollector"; },
      contrib: "__CONTRIB_URL_ZH__",
      playground: "在线运行", sample: "示例代码", output: "输出",
      reset: "↺ 重置", copy: "复制", copied: "已复制！", run: "▶ 运行",
      kw: "关键字", pl: "平台", ex: "扩展名",
      downloading: "正在下载 wasm…", running: "运行中…",
      done: function (ms, code) { return "完成，耗时 " + ms + " ms · 退出码 " + code; },
      failed: "运行失败：",
      srcinfo: "Playground wasm：",
      fLink: "用 PR 提交它",
      notAbi: "该 wasm 不符合 ToyPLCollector ABI——需要导出 memory、alloc(size)->ptr、run(ptr,len)->i32（见 CONTRIBUTING.md）",
      wasi: "该 wasm 需要本页未提供的导入——它可能是 WASI 模块；请改用 toypl ABI（见 CONTRIBUTING.md）",
      cors: "wasm 被 CORS 拦截——托管地址必须返回 Access-Control-Allow-Origin 头（推荐 raw.githubusercontent.com 或 cdn.jsdelivr.net）"
    }
  };
  var lang = null;
  try { lang = localStorage.getItem("tplc-lang"); } catch (e) {}
  if (lang !== "en" && lang !== "zh") {
    lang = (navigator.language && navigator.language.indexOf("zh") === 0) ? "zh" : "en";
  }
  function T() { return UI[lang]; }

  var elCode = $("#code");
  var elOut = $("#out");
  var elStatus = $("#status");
  var elRun = $("#run");
  var elReset = $("#reset");
  var elCopy = $("#copysrc");
  var hello = LANG.hello_world || "";
  var decoder = new TextDecoder("utf-8", { fatal: false });
  var running = false;

  // ---- header / meta ----------------------------------------------------
  function initial() {
    var s = String(LANG.display_name || LANG.name || "?").trim();
    return Array.from(s)[0] || "?";
  }
  function gclass() {
    var h = 7, s = String(LANG.name || "");
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return "g" + (h % 6);
  }
  function logoHTML() {
    if (LANG.logo) return '<img class="logo" src="' + esc(LANG.logo) + '" alt="">';
    return '<span class="logo fb ' + gclass() + '">' + esc(initial()) + "</span>";
  }
  function chipRow(rowSel, boxSel, items, cls) {
    var row = $(rowSel);
    if (!items || !items.length) { row.hidden = true; return; }
    $(boxSel).innerHTML = items.map(function (m) {
      return '<span class="chip ' + cls + '">' + esc(m) + "</span>";
    }).join("");
    row.hidden = false;
  }

  $("#llogo").innerHTML = logoHTML();
  $("#ltitle").textContent = LANG.display_name || LANG.name || "";
  var slug = $("#lslug");
  if (LANG.name) { slug.textContent = LANG.name; slug.hidden = false; }
  var year = $("#lyear");
  if (LANG.year != null) { year.textContent = LANG.year; year.hidden = false; }
  $("#ldesc").textContent = LANG.description || "";

  var repo = $("#btn-repo"), doc = $("#btn-doc");
  if (LANG.repo) repo.href = LANG.repo; else repo.hidden = true;
  if (LANG.doc) doc.href = LANG.doc; else doc.hidden = true;

  chipRow("#row-kw", "#lkw", LANG.keywords, "k");
  chipRow("#row-pl", "#lpl", LANG.platforms, "p");
  chipRow("#row-ex", "#lex", (LANG.file_extensions || []).map(function (x) { return "." + x; }), "x");

  elOut.textContent = "";
  elReset.onclick = function () { elCode.value = hello + "\n"; };
  elCopy.onclick = function () {
    var b = elCopy;
    navigator.clipboard.writeText(elCode.value).then(function () {
      b.textContent = T().copied;
      setTimeout(function () { b.textContent = T().copy; }, 1200);
    });
  };

  elCode.value = hello + (hello ? "\n" : "");

  function applyLang() {
    var t = T();
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.title = t.title(LANG.display_name || LANG.name || "Play");
    $("#lbl-play").textContent = LANG.playground ? t.playground : t.sample;
    $("#lbl-out").textContent = t.output;
    elReset.textContent = t.reset;
    elCopy.textContent = t.copy;
    elRun.textContent = t.run;
    $("#mlabel-kw").textContent = t.kw;
    $("#mlabel-pl").textContent = t.pl;
    $("#mlabel-ex").textContent = t.ex;
    $("#lang").textContent = lang === "en" ? "中文" : "EN";
    var flink = $("#f-link");
    if (flink) { flink.textContent = t.fLink; flink.href = t.contrib; }
    if (LANG.playground) {
      $("#srcinfo").textContent = t.srcinfo + LANG.playground;
    }
  }

  $("#lang").onclick = function () {
    lang = lang === "en" ? "zh" : "en";
    try { localStorage.setItem("tplc-lang", lang); } catch (e) {}
    applyLang();
  };

  // ---- no wasm? plain sample-code page -----------------------------------
  // Without a playground wasm there is nothing to run: relabel the panel to
  // "Sample code" and hide the run controls and output entirely.
  if (!LANG.playground) {
    elRun.hidden = true;
    var runbar = $("#runbar"); if (runbar) runbar.hidden = true;
    var outPanel = $("#panel-out"); if (outPanel) outPanel.hidden = true;
    applyLang();
    return; // nothing else to wire up
  }

  elRun.addEventListener("click", function () {
    if (running) return;
    doRun();
  });

  function setStatus(msg, cls) {
    elStatus.textContent = msg;
    elStatus.className = cls || "";
  }

  function appendOut(bytes) {
    var text = decoder.decode(bytes, { stream: false });
    elOut.textContent += text;
    elOut.scrollTop = elOut.scrollHeight;
  }

  // ---- module cache -----------------------------------------------------
  // The wasm downloads and compiles once per page session; every Run then
  // gets a fresh Instance from the cached Module (clean memory each time).
  // The first fetch still uses "no-cache", so a fresh deploy is picked up
  // on the next page load via the server's ETag.
  var wasmModule = null; // Promise<WebAssembly.Module> | null

  async function doRun() {
    running = true;
    elRun.disabled = true;
    elOut.textContent = "";
    var firstRun = !wasmModule;
    setStatus(firstRun ? T().downloading : T().running);
    var t0 = performance.now();

    var sourceBytes;
    try {
      sourceBytes = new TextEncoder().encode(elCode.value);
    } catch (e) {
      setStatus(T().failed + e.message, "err");
      finish();
      return;
    }

    var exitCode = null;
    var holder = { exports: null }; // filled right after instantiation

    var imports = {
      toypl: {
        // Import callbacks fire at run() time, so holder.exports is set by
        // then. (Calls made *during* instantiation are dropped — see docs.)
        output: function (ptr, len) {
          if (!holder.exports || !holder.exports.memory || len === 0) return;
          // Read a fresh view each call: the buffer detaches on memory.grow.
          var view = new Uint8Array(holder.exports.memory.buffer, ptr, len);
          appendOut(view);
        },
        exit: function (code) { exitCode = code; }
      }
    };

    try {
      if (!wasmModule) {
        var resp = await fetch(LANG.playground, { cache: "no-cache" });
        if (!resp.ok) throw new Error("wasm download failed: HTTP " + resp.status);
        var buf = await resp.arrayBuffer();
        if (buf.byteLength === 0) throw new Error("wasm file is empty");
        if (!WebAssembly.validate(buf)) {
          throw new Error("response is not valid wasm (check the playground URL)");
        }
        wasmModule = WebAssembly.compile(buf);
        // A failed download/compile must not poison the cache: allow a retry.
        wasmModule.catch(function () { wasmModule = null; });
      }
      var instance = await WebAssembly.instantiate(await wasmModule, imports);
      var ex = instance.exports;
      holder.exports = ex;

      if (!ex.memory || typeof ex.alloc !== "function" || typeof ex.run !== "function") {
        throw new Error(T().notAbi);
      }

      if (firstRun) setStatus(T().running);
      // alloc may memory.grow(), so grab the view afterwards.
      var ptr = ex.alloc(sourceBytes.length);
      if (typeof ptr !== "number" || ptr < 0) throw new Error("alloc() returned an invalid pointer");
      var mem = new Uint8Array(ex.memory.buffer);
      mem.set(sourceBytes, ptr);

      var rc = ex.run(ptr, sourceBytes.length);
      var ms = Math.round(performance.now() - t0);
      var code = exitCode != null ? exitCode : rc;
      setStatus(T().done(ms, code));
    } catch (err) {
      var msg = (err && err.message) ? err.message : String(err);
      if (/imports? provided/i.test(msg) && /toypl/.test(msg) === false) {
        msg = T().wasi;
      }
      if (/Blocked|CORS/i.test(msg)) {
        msg = T().cors;
      }
      setStatus(T().failed + msg, "err");
    }

    finish();
  }

  function finish() {
    running = false;
    elRun.disabled = false;
  }

  applyLang();
})();
"""


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------


def guard_placeholder(template: str, replacements: dict) -> str:
    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)
    left = [k for k in replacements if k in out]
    if left:
        raise SystemExit(f"internal error: placeholders not replaced: {left}")
    return out


def head_block(title: str, description: str) -> str:
    """Meta tags for <head>, attribute-escaped."""
    t = html.escape(title)
    d = html.escape(description, quote=True)
    return "\n".join([
        f"<title>{t}</title>",
        f'<meta name="description" content="{d}">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        '<meta property="og:type" content="website">',
    ])


def lang_public(lang: dict) -> dict:
    """The JSON shape the pages embed (drop private keys)."""
    out = {
        "name": lang["name"],
        "display_name": lang.get("display_name") or lang["name"],
        "logo": lang.get("logo"),
        "description": lang.get("description", ""),
        "year": lang.get("year"),
        "keywords": lang.get("keywords") or [],
        "platforms": lang.get("platforms") or [],
        "file_extensions": lang.get("file_extensions") or [],
        "repo": lang.get("repo", ""),
        "doc": lang.get("doc"),
        "playground": lang.get("playground"),
        "hello_world": lang.get("hello_world", ""),
    }
    # normalize file extensions (strip leading dots)
    out["file_extensions"] = [str(e).lstrip(".").lower() for e in out["file_extensions"]]
    return out


def build(coll_dir: Path, out_dir: Path) -> None:
    langs = collect(coll_dir)
    public = [lang_public(l) for l in langs]
    platforms = sorted({p for l in public for p in l["platforms"]})
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    index_html = guard_placeholder(INDEX_TEMPLATE, {
        "__METATAGS__": head_block(
            "ToyPLCollector — a gallery of toy programming languages",
            "Community-collected toy programming languages: hello worlds, links and browser playgrounds.",
        ),
        "__CSS__": CSS,
        "__GITHUB_URL__": GITHUB_URL,
        "__CONTRIB_URL__": CONTRIB_URL,
        "__CONTRIB_URL_ZH__": CONTRIB_URL_ZH,
        "__BUILT_AT__": built_at,
        "__LANGS__": js_json(public),
    })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")
    (out_dir / "CNAME").write_text(SITE_DOMAIN + "\n", encoding="utf-8")

    (out_dir / "wasm-runner.js").write_text(RUNNER_JS, encoding="utf-8")

    if ASSETS_WASM_DIR.is_dir():
        dst = out_dir / "wasm"
        dst.mkdir(exist_ok=True)
        for f in sorted(ASSETS_WASM_DIR.glob("*.wasm")):
            shutil.copy2(f, dst / f.name)

    play_dir = out_dir / "play"
    play_dir.mkdir(exist_ok=True)
    for lang in public:
        page = guard_placeholder(PLAY_TEMPLATE, {
            "__METATAGS__": head_block(
                f"{lang['display_name']} — ToyPLCollector",
                f"{lang.get('description', '')} "
                + ("Run it in your browser playground." if lang.get("playground") else "Sample code and project links."),
            ),
            "__CSS__": CSS,
            "__GITHUB_URL__": GITHUB_URL,
            "__CONTRIB_URL__": CONTRIB_URL,
            "__CONTRIB_URL_ZH__": CONTRIB_URL_ZH,
            "__LANG__": js_json(lang),
        })
        (play_dir / f"{lang['name']}.html").write_text(page, encoding="utf-8")

    print(f"site → {out_dir}")
    print(f"  {len(langs)} language(s): {', '.join(str(l['name']) for l in langs)}")
    print(f"  platforms: {', '.join(platforms) or '—'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", default=str(plc.COLLECTIONS_DIR), help="collections directory")
    parser.add_argument("--out", default="_site", help="output directory (default _site)")
    args = parser.parse_args(argv)
    build(Path(args.dir), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
