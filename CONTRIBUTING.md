English | [简体中文](CONTRIBUTING.zh-CN.md)

# Contributing

> In short: **one TOML file = one toy language**. Copy an example, fill it in, open a PR —
> validation runs automatically, and after one maintainer approval GitHub merges by itself.

---

## 1. Add your language

1. Fork this repo
2. Create `collections/<your-language>.toml` — the file name **must equal** the `name` field
3. Fill the fields (reference below)
4. Open a PR
5. CI runs `validate.py`; fix anything it marks red
6. A maintainer approves → auto-merge does the rest

**Start from a real example**: [`collections/riddle.toml`](collections/riddle.toml)

### Field reference

| field | type | required | what it is |
|---|---|---|---|
| `name` | string | ✅ | URL slug, `^[a-z0-9][a-z0-9-]{0,63}$`, must equal the file name |
| `display_name` | string | ✅ | Shown name, ≤60 chars |
| `logo` | string | – | Logo for the gallery card: a `data:image/...` URL or an https image URL |
| `description` | string | ✅ | ≤500 chars, any language |
| `year` | int | – | Birth year, 1940–now |
| `keywords` | string[] | – | ≤12, used by site search |
| `platforms` | string[] | – | From: `Windows, Linux, macOS, Web, Other` |
| `file_extensions` | string[] | – | e.g. `["bas"]` |
| `repo` | https URL | ✅ | Source code |
| `doc` | https URL | – | Documentation |
| `playground` | https URL | – | Your `*.wasm` following the `toypl` ABI below — enables Run |
| `hello_world` | string | ✅ | Sample code, ≤5000 chars |

Rules that CI enforces:

* PRs may only add/edit `collections/*.toml` — scripts, workflows and the site are maintainer-only
* no duplicate `name`
* unknown extra fields are only a warning — new fields can be added later without breaking old entries
* deleting other languages' files needs an issue + a maintainer

### License

This repo is [MIT-licensed](LICENSE). By opening a PR you agree that your
contribution (TOML entry, playground wasm, code snippets) is published under
the same license.

---

## 2. Online playground — the `toypl` wasm ABI

The site cannot run *every* wasm: your `playground` wasm must itself be your language's
interpreter (compiled to wasm) and follow this minimal protocol, which the shared page runner
(`wasm-runner.js`) drives.

```
exports must include:
  memory                 linear memory
  alloc(size:i32) -> i32 reserve size bytes, return the wasm offset
  run(ptr:i32, len:i32) -> i32
                         the page writes the source code to [ptr, ptr+len) as UTF-8 —
                         interpret it; return a process-like exit code

imports — emit output / exit by calling:
  toypl.output(ptr:i32, len:i32)   append [ptr, ptr+len) bytes to stdout
  toypl.exit(code:i32)             stop, report exit code

Notes:
  * write memory right after allocating: alloc may trigger memory.grow
  * output calls made during instantiation (start function) are dropped — output from within run
  * a WASI module (imports wasi_snapshot_preview1) cannot be instantiated
```

### Rust starter template

A ready-to-copy crate ships in this repo:

* [`scripts/wasm-runner/TEMPLATE-rust/Cargo.toml`](scripts/wasm-runner/TEMPLATE-rust/Cargo.toml)
* [`scripts/wasm-runner/TEMPLATE-rust/src/lib.rs`](scripts/wasm-runner/TEMPLATE-rust/src/lib.rs)

Build it:

```bash
rustup target add wasm32-unknown-unknown
cargo build --release --target wasm32-unknown-unknown
# → target/wasm32-unknown-unknown/release/yourlang_wasm.wasm
```

The imports/exports you must keep exactly:

```rust
// imports the page provides:
#[link(wasm_import_module = "toypl")]
extern "C" {
    fn output(ptr: i32, len: i32);
    fn exit(code: i32) -> !;
}

// exports the page expects:
#[no_mangle] pub extern "C" fn alloc(size: i32) -> i32;
#[no_mangle] pub extern "C" fn run(ptr: i32, len: i32) -> i32;
// memory is exported automatically by wasm-ld on this target
```

### Hosting the wasm (CORS required)

The browser fetches the file, so the host must send `Access-Control-Allow-Origin`:

| ✅ good | `https://cdn.jsdelivr.net/gh/<user>/<repo>@<tag>/<path>.wasm` |
| ✅ good | `https://raw.githubusercontent.com/<user>/<repo>/<branch>/<path>.wasm` |
| ❌ NOT allowed | GitHub Releases download links (no CORS headers) |

---

## 3. How merging works

```
PR opened ──► CI "Validate collections" passes ──► maintainer approves
        ──► GitHub auto-merge merges (squash) ──► site rebuilds within ~1 min
```

## 4. Test locally

```bash
python3 main.py validate      # lint your entry
python3 main.py build         # build the site into _site/
python3 -m http.server -d _site 8000   # preview http://localhost:8000
```
