# Contributing ｜ 贡献指南

> In short: **one TOML file = one toy language**. Copy an example, fill it in, open a PR —
> validation runs automatically, and after one maintainer approval GitHub merges by itself.
>
> 简单说：**一个 TOML 文件 = 一个玩具语言**。复制示例填好，发一个 PR —— CI 自动校验，
> 维护者点一次 approve 之后 GitHub 自动合并。

---

## 1. Add your language ｜ 新增一门语言

1. Fork this repo / fork 本仓库
2. Create `collections/<your-language>.toml` — the file name **must equal** the `name` field
   / 新建 `collections/<语言名>.toml`，文件名必须和 `name` 字段一致
3. Fill the fields (reference below) ｜ 填好字段（参考下表）
4. Open a PR ｜ 发起 PR
5. CI runs `validate.py`; fix anything it marks red ｜ CI 会跑校验，红了就修
6. A maintainer approves → auto-merge does the rest ｜ 维护者 approve 后自动合并

**Start from the sample** ｜ 复制示例起步: [`collections/demo.toml`](collections/demo.toml)

### Field reference ｜ 字段说明

| field | type | required | what it is ｜ 说明 |
|---|---|---|---|
| `name` | string | ✅ | URL slug, `^[a-z0-9][a-z0-9-]{0,63}$`, must equal the file name ｜ 网址和文件名 |
| `display_name` | string | ✅ | Shown name, ≤60 chars ｜ 显示名称 |
| `logo` | string | – | Logo for the gallery card: a `data:image/...` URL or an https image URL ｜ 卡片 LOGO：data URL 或 https 图片链接 |
| `description` | string | ✅ | ≤500 chars, any language ｜ 一句话介绍（任意语言） |
| `year` | int | – | Birth year, 1940–now ｜ 诞生年份 |
| `keywords` | string[] | – | ≤12, used by site search ｜ 关键字，用于站内搜索 |
| `platforms` | string[] | – | From: `Windows, Linux, macOS, Web, Other` ｜ 支持平台（枚举） |
| `file_extensions` | string[] | – | e.g. `["bas"]` ｜ 文件扩展名 |
| `repo` | https URL | ✅ | Source code ｜ 源码仓库 |
| `doc` | https URL | – | Documentation ｜ 文档 |
| `playground` | https URL | – | Your `*.wasm` following the `toypl` ABI below — enables Run ｜ 符合下文 ABI 的 wasm，可在线运行 |
| `hello_world` | string | ✅ | Sample code, ≤5000 chars ｜ 示例代码 |

Rules that CI enforces ｜ CI 硬性规则:

* PR must only add/edit `collections/*.toml` — scripts, workflows and the site are maintainer-only
  （PR 只能改 `collections/*.toml`，脚本与网站由维护者维护）
* no duplicate `name` ｜ `name` 不可重复
* unknown extra fields are only a warning — new fields can be added later without breaking old
  entries ｜ 未知字段只是警告，方便以后扩展而不破坏旧条目
* deleting other languages' files needs an issue + maintainer ｜ 删除别人的条目请先开 issue

---

## 2. Online playground — the `toypl` wasm ABI ｜ 在线运行约定

The site cannot run *every* wasm: your `playground` wasm must itself be your language's
interpreter (compiled to wasm) and follow this minimal protocol, which the shared page runner
(`wasm-runner.js`) drives.

网站不是什么 wasm 都能跑：`playground` 指向的 wasm 必须是**你的语言的解释器**（或执行器）
编译成的 wasm，并遵守页面 runner 调用的最小协议：

```
exports 必须有:
  memory                 linear memory                线性内存
  alloc(size:i32) -> i32 reserve size bytes, return the wasm offset
                         （分配 size 字节，返回内存偏移）
  run(ptr:i32, len:i32) -> i32
                         source code was written to [ptr, ptr+len) as UTF-8 —
                         interpret it; return process-like exit code
                         （页面会把源代码 UTF-8 写进内存再调 run；返回退出码）

imports 请向以下模块调用输出/退出:
  toypl.output(ptr:i32, len:i32)   append [ptr, ptr+len) bytes to stdout
  toypl.exit(code:i32)             stop, report exit code

注意:
  * allocate 后立刻写内存：alloc 可能触发 memory.grow
  * 实例化期间（start 函数）的 output 调用会被丢弃，请在 run 内输出
  * 如果你的 wasm 是 WASI 模块（imports wasi_snapshot_preview1）将无法实例化
```

### Rust starter template ｜ Rust 起步模板

A ready-to-copy crate ships in this repo ｜ 仓库里有一份可直接复制的模板:

* [`scripts/wasm-runner/TEMPLATE-rust/Cargo.toml`](scripts/wasm-runner/TEMPLATE-rust/Cargo.toml)
* [`scripts/wasm-runner/TEMPLATE-rust/src/lib.rs`](scripts/wasm-runner/TEMPLATE-rust/src/lib.rs)

Build it ｜ 构建:

```bash
rustup target add wasm32-unknown-unknown
cargo build --release --target wasm32-unknown-unknown
# → target/wasm32-unknown-unknown/release/yourlang_wasm.wasm
```

The imports/exports you must keep exactly ｜ 必须保留的导入/导出签名:

```rust
// imports the page provides ｜ 页面提供的导入:
#[link(wasm_import_module = "toypl")]
extern "C" {
    fn output(ptr: i32, len: i32);
    fn exit(code: i32) -> !;
}

// exports the page expects ｜ 页面要求的导出:
#[no_mangle] pub extern "C" fn alloc(size: i32) -> i32;
#[no_mangle] pub extern "C" fn run(ptr: i32, len: i32) -> i32;
// memory is exported automatically by wasm-ld on this target
// （wasm32-unknown-unknown 目标下 memory 由 wasm-ld 自动导出）
```

### Hosting the wasm ｜ 托管 wasm（必须有 CORS）

The browser fetches the file, so the host must send `Access-Control-Allow-Origin`:

浏览器要能跨域取到文件，托管地址必须带 CORS 头：

| ✅ good ｜ 推荐 | `https://cdn.jsdelivr.net/gh/<user>/<repo>@<tag>/<path>.wasm` |
| ✅ good ｜ 推荐 | `https://raw.githubusercontent.com/<user>/<repo>/<branch>/<path>.wasm` |
| ❌ NOT allowed ｜ 别用 | GitHub Releases 下载链接（无 CORS 头） |

---

## 3. How merging works ｜ 合并流程

```
PR opened ──► CI "Validate collections" passes ──► maintainer approves
        ──► GitHub auto-merge merges (squash) ──► site rebuilds within ~1 min
       （PR ──> 校验通过 ──> 维护者 approve ──> 自动合并 ──> 网站 ~1 分钟内更新）
```

## 4. Test locally ｜ 本地自测

```bash
python3 main.py validate      # lint your entry ｜ 校验
python3 main.py build         # build the site into _site/
python3 -m http.server -d _site 8000   # preview ｜ 预览 http://localhost:8000
```
