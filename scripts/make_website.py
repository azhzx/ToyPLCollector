#!/usr/bin/env python3
"""Build the ToyPLCollector website as a zero-dependency static bundle.

Output layout (default ``_site``)::

    _site/
      index.html            card gallery — logo + name tiles, grouped A-Z / 中文 / 其他
      play/<slug>.html      one detail page per language (merged with its playground)
      wasm-runner.js        shared loader implementing the toypl wasm ABI

The index embeds every entry as JSON and does grouping + sorting (A-Z, 中文
pinyin, 其他) client-side via Intl.Collator, so no build-time locale is needed.

Run locally::

    python3 scripts/make_website.py            # writes to _site/
    python3 scripts/make_website.py --out /tmp/site

"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import plc

GITHUB_URL = "https://github.com/azhzx/ToyPLCollector"
CONTRIB_URL = f"{GITHUB_URL}/blob/main/CONTRIBUTING.md"

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
# styles
# --------------------------------------------------------------------------

CSS = """
:root{
  --bg:#070a12;--panel:#0f1523;--panel2:#0b101c;--code:#080c16;
  --line:#1f2a44;--ink:#e8edf8;--muted:#8d99b8;--faint:#5d688a;
  --accent:#7c9cff;--accent2:#5fe3c0;--warn:#ffc86b;
  --grad:linear-gradient(135deg,#7c9cff 0%,#5ad1ff 55%,#5fe3c0 100%);
  --mono:ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;
  --radius:16px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
html,body{margin:0;padding:0}
body{background:
    radial-gradient(900px 480px at 12% -10%,rgba(124,156,255,.13),transparent 60%),
    radial-gradient(820px 460px at 96% -6%,rgba(95,227,192,.09),transparent 55%),
    var(--bg);
  background-attachment:fixed;color:var(--ink);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
::selection{background:rgba(124,156,255,.35)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
[hidden]{display:none!important}
label.sr{position:absolute;left:-9999px}

/* ---- top bar ---- */
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:13px 26px;border-bottom:1px solid var(--line);
  background:color-mix(in srgb,var(--bg) 76%,transparent);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.brand{font-weight:800;font-size:17px;display:flex;align-items:center;gap:9px;color:var(--ink)}
.brand:hover{text-decoration:none}
.brand .name{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand .logo{font-size:19px}
.search{flex:1 1 240px;max-width:430px;position:relative}
.search svg{position:absolute;left:13px;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--faint);pointer-events:none}
.search input{width:100%;padding:10px 16px 10px 37px;border-radius:999px;border:1px solid var(--line);
  background:var(--panel2);color:var(--ink);font-size:14px;transition:border-color .15s,box-shadow .15s}
.search input::placeholder{color:var(--faint)}
.search input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(124,156,255,.16)}
.topbar nav{display:flex;gap:18px;margin-left:auto;font-size:14px}
.topbar nav a{color:var(--muted)}
.topbar nav a:hover{color:var(--ink);text-decoration:none}

/* ---- filter bar ---- */
.subbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 26px;border-bottom:1px solid var(--line)}
.chips{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{display:inline-flex;align-items:center;gap:5px;padding:3px 11px;border-radius:999px;font-size:12px;
  border:1px solid var(--line);background:var(--panel2);color:var(--muted);white-space:nowrap}
.chip.k{color:var(--accent2);border-color:color-mix(in srgb,var(--accent2) 35%,transparent)}
.chip.p{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 35%,transparent)}
.chip.x{font-family:var(--mono);color:#c8b3ff;border-color:color-mix(in srgb,#c8b3ff 35%,transparent)}
button.chip{cursor:pointer;font-family:inherit;font-size:12.5px;padding:5px 13px;transition:border-color .15s,color .15s,background .15s}
button.chip:hover{border-color:var(--accent);color:var(--ink)}
button.chip.on{background:var(--grad);color:#071022;border-color:transparent;font-weight:700}
.count{color:var(--muted);font-size:13px;margin-left:auto;font-variant-numeric:tabular-nums}

/* ---- gallery ---- */
main{padding:26px;max-width:1200px;margin:0 auto}
.group{margin:10px 0 36px}
.group>h2{display:flex;align-items:center;gap:10px;margin:0 0 14px;font-size:13px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.group>h2 .gcount{font-weight:500;letter-spacing:.05em;color:var(--faint);font-size:12px}
.group>h2::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,var(--line),transparent)}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.tile{display:flex;flex-direction:column;align-items:center;gap:12px;padding:24px 12px 18px;text-align:center;
  color:var(--ink);border-radius:var(--radius);border:1px solid var(--line);
  background:linear-gradient(180deg,rgba(255,255,255,.028),rgba(255,255,255,0) 55%),var(--panel);
  transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease}
.tile:hover{transform:translateY(-4px);border-color:color-mix(in srgb,var(--accent) 60%,transparent);
  box-shadow:0 14px 34px rgba(0,0,0,.38);text-decoration:none}
.tile .tname{font-weight:600;font-size:14.5px;line-height:1.35;max-width:100%;word-break:break-word;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.logo{display:inline-flex;align-items:center;justify-content:center;flex:none;font-weight:800;
  color:#f2f5ff;user-select:none}
img.logo{object-fit:contain;background:var(--panel)}
.tile .logo{width:72px;height:72px;border-radius:18px;font-size:34px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.1)}
.tile img.logo{padding:7px}
.fb{color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.25)}
.g0{background:linear-gradient(135deg,#7c9cff,#4a5fd0)}
.g1{background:linear-gradient(135deg,#5fe3c0,#2e9e83)}
.g2{background:linear-gradient(135deg,#f2a4c0,#c05a8e)}
.g3{background:linear-gradient(135deg,#ffc86b,#d08a2e)}
.g4{background:linear-gradient(135deg,#c8b3ff,#7d5ad0)}
.g5{background:linear-gradient(135deg,#5ad1ff,#2e7ec0)}
.muted{color:var(--muted)}
.empty{padding:70px 0;text-align:center;color:var(--muted)}

/* ---- detail / play page ---- */
.play main{max-width:880px;padding-bottom:56px}
.hero{display:flex;gap:20px;align-items:flex-start;margin:30px 0 4px;flex-wrap:wrap}
.hero-logo{width:84px;height:84px;flex:none}
.hero-logo .logo{width:84px;height:84px;border-radius:20px;font-size:40px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.1)}
.hero-logo img.logo{padding:9px}
.hero-main{flex:1 1 320px}
.hero h1{margin:0 0 8px;font-size:clamp(24px,4vw,32px);letter-spacing:-.01em;
  display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hero .slug{font-family:var(--mono);font-size:12.5px;font-weight:500;color:var(--muted);
  border:1px solid var(--line);border-radius:8px;padding:2px 9px}
.hero .desc{margin:0;color:var(--muted);max-width:70ch}
.hero .actions{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 15px;border-radius:10px;font-weight:600;
  font-size:13.5px;border:1px solid var(--line);color:var(--muted);background:var(--panel);transition:color .15s,border-color .15s}
.btn:hover{color:var(--ink);border-color:var(--accent);text-decoration:none}
.btn.grad{background:var(--grad);color:#071022;border-color:transparent}
.btn.grad:hover{filter:brightness(1.08);color:#071022}
.btn.sm{padding:4px 11px;font-size:12px;border-radius:8px}
.meta{margin:24px 0 0;display:flex;flex-direction:column;gap:9px}
.meta-row{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
.mlabel{flex:none;width:96px;font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}

/* ---- shared panels ---- */
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin-top:22px;
  box-shadow:0 8px 28px rgba(0,0,0,.18)}
.panel-head{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.panel-head span{font-size:12px;color:var(--muted);font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.panel-head .sp{flex:1}
pre{margin:0;padding:14px;background:var(--code);border:1px solid var(--line);border-radius:12px;overflow:auto;
  font-family:var(--mono);font-size:12.5px;line-height:1.55;color:#c9d6f7}
textarea#code{width:100%;min-height:270px;resize:vertical;background:var(--code);color:#c9d6f7;
  border:1px solid var(--line);border-radius:12px;padding:14px;font-family:var(--mono);font-size:13px;line-height:1.6;
  tab-size:4;white-space:pre;overflow:auto}
textarea#code:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(124,156,255,.16)}
.runbar{display:flex;align-items:center;gap:14px;margin-top:13px;flex-wrap:wrap}
button.primary{background:var(--grad);color:#071022;border:none;border-radius:10px;padding:10px 26px;
  font-weight:800;font-size:14px;cursor:pointer;letter-spacing:.01em;transition:filter .15s,transform .08s}
button.primary:hover{filter:brightness(1.07)}
button.primary:active{transform:scale(.98)}
button.primary:disabled{opacity:.45;cursor:not-allowed;filter:none}
#status{font-size:13px;color:var(--muted)}
#status.err{color:var(--warn)}
#out{max-height:420px;min-height:64px}
.srcinfo{margin-top:16px;font-size:12px;color:var(--faint);word-break:break-all}

footer{padding:28px 26px 46px;color:var(--muted);font-size:13px;text-align:center;border-top:1px solid var(--line);margin-top:34px}
footer code{font-family:var(--mono);background:var(--panel2);padding:1px 6px;border-radius:6px}

@media (max-width:620px){
  main{padding:16px}
  .topbar,.subbar{padding-left:16px;padding-right:16px}
  .grid{grid-template-columns:repeat(auto-fill,minmax(118px,1fr))}
  .mlabel{width:100%}
  .hero{margin-top:20px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}}
"""

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%A7%A9%3C/text%3E%3C/svg%3E"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="__FAVICON__">
__METATAGS__
<style>__CSS__</style>
</head>
"""

INDEX_TEMPLATE = HEAD + """<body>
<header class="topbar">
  <a class="brand" href="index.html"><span class="logo">🧩</span><span class="name">ToyPLCollector</span></a>
  <span class="search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <label class="sr" for="q">Search</label>
    <input id="q" type="search" placeholder="Search by name, keyword, platform, extension…" autocomplete="off">
  </span>
  <nav>
    <a href="__GITHUB_URL__" target="_blank" rel="noopener">GitHub</a>
    <a href="__CONTRIB_URL__" target="_blank" rel="noopener">Add your language →</a>
  </nav>
</header>
<section class="subbar">
  <div id="chips" class="chips"></div>
  <span id="count" class="count"></span>
</section>
<main id="cards"><noscript><p class="empty">Please enable JavaScript to browse the gallery ｜ 请启用 JavaScript 浏览。</p></noscript></main>
<footer>
  Generated from <code>collections/*.toml</code> — have a toy language of your own?
  <a href="__CONTRIB_URL__" target="_blank" rel="noopener">Submit it with a PR</a>.
  Built at <span id="builtat">__BUILT_AT__</span>.
</footer>
<script>const LANGS=__LANGS__;const PLATFORMS=__PLATFORMS__;</script>
<script>
(function(){
"use strict";
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const enColl=new Intl.Collator("en",{sensitivity:"base",numeric:true});
let zhColl=null;
try{zhColl=new Intl.Collator("zh-u-co-pinyin",{numeric:true});}catch(e){}
const GROUPS=[["en","A–Z"],["zh","中文"],["other","其他"]];

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

let activePlatform=null,query="";

function filtered(){
  return LANGS.filter(l=>{
    if(activePlatform&&!(l.platforms||[]).includes(activePlatform))return false;
    if(query&&!textOf(l).includes(query))return false;
    return true;
  });
}

function render(){
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
  for(const[key,label]of GROUPS){
    if(!by[key].length)continue;
    html+=`<section class="group"><h2>${label}<span class="gcount">${by[key].length}</span></h2>`+
      `<div class="grid">${by[key].map(tileHTML).join("")}</div></section>`;
  }
  $("#cards").innerHTML=html||`<p class="empty">No language matches “${esc(query)}”.</p>`;
  $("#count").textContent=`${list.length} / ${LANGS.length} languages`;
}

function initChips(){
  const box=$("#chips");
  const mk=(label,val)=>`<button class="chip ${val===activePlatform?"on":""}" data-p="${esc(val==null?"":val)}">${esc(label)}</button>`;
  box.innerHTML=mk("All platforms",null)+PLATFORMS.map(p=>mk(p,p)).join("");
  box.querySelectorAll("button").forEach(b=>b.onclick=()=>{
    activePlatform=b.dataset.p===""?null:b.dataset.p;
    initChips();render();
  });
}

$("#q").addEventListener("input",e=>{query=e.target.value.trim().toLowerCase();render();});
initChips();render();
})();
</script>
</body>
</html>
"""

PLAY_TEMPLATE = HEAD + """<body class="play">
<header class="topbar">
  <a class="brand" href="../index.html">← <span class="name">🧩 ToyPLCollector</span></a>
  <nav><a href="__GITHUB_URL__" target="_blank" rel="noopener">GitHub</a></nav>
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
    <div class="meta-row" id="row-kw" hidden><span class="mlabel">Keywords</span><div class="chips" id="lkw"></div></div>
    <div class="meta-row" id="row-pl" hidden><span class="mlabel">Platforms</span><div class="chips" id="lpl"></div></div>
    <div class="meta-row" id="row-ex" hidden><span class="mlabel">Extensions</span><div class="chips" id="lex"></div></div>
  </div>
  <section class="panel">
    <div class="panel-head"><span>Playground</span><div class="sp"></div>
      <button class="btn sm" id="reset">↺ reset</button>
      <button class="btn sm" id="copysrc">copy</button>
    </div>
    <textarea id="code" spellcheck="false" aria-label="source code"></textarea>
    <div class="runbar">
      <button id="run" class="primary">▶ Run</button>
      <span id="status"></span>
    </div>
  </section>
  <section class="panel">
    <div class="panel-head"><span>Output</span></div>
    <pre id="out" aria-live="polite"></pre>
  </section>
  <p class="srcinfo" id="srcinfo"></p>
</main>
<footer>
  Generated from <code>collections/*.toml</code> — have a toy language of your own?
  <a href="__CONTRIB_URL__" target="_blank" rel="noopener">Submit it with a PR</a>.
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
 *
 * This script also fills the detail-page hero (logo, name, chips, links)
 * from the LANG JSON embedded by the page.
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

  document.title = (LANG.display_name || LANG.name || "Play") + " — ToyPLCollector";
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
      b.textContent = "copied!";
      setTimeout(function () { b.textContent = "copy"; }, 1200);
    });
  };

  elCode.value = hello + (hello ? "\n" : "");

  // ---- no wasm? degrade gracefully --------------------------------------
  if (!LANG.playground) {
    elRun.disabled = true;
    setStatus("This language does not provide an online wasm runtime yet — " +
      "edit and copy the code, or open its repo.", "err");
    return; // nothing else to wire up
  }
  $("#srcinfo").textContent = "Playground wasm: " + LANG.playground;

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

  async function doRun() {
    running = true;
    elRun.disabled = true;
    elOut.textContent = "";
    setStatus("Downloading wasm…");
    var t0 = performance.now();

    var sourceBytes;
    try {
      sourceBytes = new TextEncoder().encode(elCode.value);
    } catch (e) {
      setStatus("Failed to encode source: " + e.message, "err");
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
      var resp = await fetch(LANG.playground, { cache: "no-cache" });
      if (!resp.ok) throw new Error("wasm download failed: HTTP " + resp.status);
      var buf = await resp.arrayBuffer();
      if (buf.byteLength === 0) throw new Error("wasm file is empty");
      if (!WebAssembly.validate(buf)) {
        throw new Error("response is not valid wasm (check the playground URL)");
      }

      var result = await WebAssembly.instantiate(buf, imports);
      var ex = result.instance.exports;
      holder.exports = ex;

      if (!ex.memory || typeof ex.alloc !== "function" || typeof ex.run !== "function") {
        throw new Error(
          "this wasm does not follow the ToyPLCollector ABI — " +
          "required exports: memory, alloc(size)->ptr, run(ptr,len)->i32 " +
          "(see CONTRIBUTING.md)"
        );
      }

      setStatus("Running…");
      // alloc may memory.grow(), so grab the view afterwards.
      var ptr = ex.alloc(sourceBytes.length);
      if (typeof ptr !== "number" || ptr < 0) throw new Error("alloc() returned an invalid pointer");
      var mem = new Uint8Array(ex.memory.buffer);
      mem.set(sourceBytes, ptr);

      var rc = ex.run(ptr, sourceBytes.length);
      var ms = Math.round(performance.now() - t0);
      var code = exitCode != null ? exitCode : rc;
      setStatus("done in " + ms + " ms · exit code " + code);
    } catch (err) {
      var msg = (err && err.message) ? err.message : String(err);
      if (/imports? provided/i.test(msg) && /toypl/.test(msg) === false) {
        msg = "wasm needs imports this page does not provide — it is probably a WASI " +
          "module; languages must use the toypl ABI (see CONTRIBUTING.md)";
      }
      if (/Blocked|CORS/i.test(msg)) {
        msg = "wasm blocked by CORS — the host must send Access-Control-Allow-Origin " +
          "(try raw.githubusercontent.com or cdn.jsdelivr.net)";
      }
      setStatus("Run failed: " + msg, "err");
    }

    finish();
  }

  function finish() {
    running = false;
    elRun.disabled = false;
  }
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
        "__FAVICON__": FAVICON,
        "__METATAGS__": head_block(
            "ToyPLCollector — a gallery of toy programming languages",
            "Community-collected toy programming languages: hello worlds, links and browser playgrounds.",
        ),
        "__CSS__": CSS,
        "__GITHUB_URL__": GITHUB_URL,
        "__CONTRIB_URL__": CONTRIB_URL,
        "__BUILT_AT__": built_at,
        "__LANGS__": js_json(public),
        "__PLATFORMS__": js_json(platforms),
    })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    (out_dir / "wasm-runner.js").write_text(RUNNER_JS, encoding="utf-8")

    play_dir = out_dir / "play"
    play_dir.mkdir(exist_ok=True)
    for lang in public:
        page = guard_placeholder(PLAY_TEMPLATE, {
            "__FAVICON__": FAVICON,
            "__METATAGS__": head_block(
                f"{lang['display_name']} — ToyPLCollector",
                f"{lang.get('description', '')} Run it in your browser playground.",
            ),
            "__CSS__": CSS,
            "__GITHUB_URL__": GITHUB_URL,
            "__CONTRIB_URL__": CONTRIB_URL,
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
