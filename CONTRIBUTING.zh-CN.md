[English](CONTRIBUTING.md) | 简体中文

# 贡献指南

> 简单说：**一个 TOML 文件 = 一个玩具语言**。复制示例填好，发一个 PR —— CI 自动校验，
> 维护者点一次 approve 之后 GitHub 自动合并。

---

## 1. 新增一门语言

1. fork 本仓库
2. 新建 `collections/<语言名>.toml` —— 文件名**必须**和 `name` 字段一致
3. 填好字段（参考下表）
4. 发起 PR
5. CI 会跑校验，红了就修
6. 维护者 approve 后自动合并

**从真实条目起步**：[`collections/riddle.toml`](collections/riddle.toml)

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 名称标识：字母（含中文）、数字、空格、`-`、`_`、`.`，≤64 字符，必须与文件名一致 |
| `display_name` | string | ✅ | 展示名称，≤60 字符 |
| `logo` | string | – | 卡片 LOGO：`data:image/...` data URL 或 https 图片链接 |
| `description` | string | ✅ | 一句话介绍，≤500 字符（任意语言） |
| `year` | int | – | 诞生年份，1940 至今 |
| `keywords` | string[] | – | ≤12 个，用于站内搜索 |
| `platforms` | string[] | – | 枚举：`Windows, Linux, macOS, Web, Other` |
| `file_extensions` | string[] | – | 文件扩展名，如 `["bas"]` |
| `repo` | https URL | ✅ | 源码仓库 |
| `doc` | https URL | – | 文档 |
| `official_playground` | https URL | – | **官方**在线 Playground（任意技术实现），详情页展示链接 |
| `release` | https URL | – | 发布 / 下载页，详情页展示链接 |
| `playground` | https URL | – | 符合下文 `toypl` ABI 的 wasm，填写后详情页可内联运行 |
| `hello_world` | string | ✅ | 示例代码，≤5000 字符 |

CI 硬性规则：

* PR 只能改 `collections/*.toml`，脚本、workflow 和网站由维护者维护
* `name` 不可重复
* 所有 URL 字段必须是 `https://`；链接暂时不可达只会给出警告，不会因此阻止合并
* 未知字段只是警告——方便以后扩展字段而不破坏旧条目
* 删除别人的条目请先开 issue 并经维护者确认

### 许可

本仓库采用 [MIT 许可证](LICENSE)。提交 PR 即表示同意你的贡献（TOML 条目、
playground wasm、代码片段）以相同许可发布。

---

## 2. 在线运行约定：`toypl` wasm ABI

网站不是什么 wasm 都能跑：`playground` 指向的 wasm 必须是**你的语言的解释器**（或执行器）
编译成的 wasm，并遵守页面 runner（`wasm-runner.js`）调用的最小协议：

```
exports 必须有:
  memory                 线性内存
  alloc(size:i32) -> i32 分配 size 字节，返回内存偏移
  run(ptr:i32, len:i32) -> i32
                         页面会把源代码 UTF-8 写进 [ptr, ptr+len) 再调 run；
                         解释执行，返回进程式退出码

imports 请向以下模块调用输出/退出:
  toypl.output(ptr:i32, len:i32)   把 [ptr, ptr+len) 字节追加到 stdout
  toypl.exit(code:i32)             停止并上报退出码

注意:
  * allocate 后立刻写内存：alloc 可能触发 memory.grow
  * 实例化期间（start 函数）的 output 调用会被丢弃，请在 run 内输出
  * 如果你的 wasm 是 WASI 模块（imports wasi_snapshot_preview1）将无法实例化
```

### Rust 起步模板

仓库里有一份可直接复制的模板：

* [`scripts/wasm-runner/TEMPLATE-rust/Cargo.toml`](scripts/wasm-runner/TEMPLATE-rust/Cargo.toml)
* [`scripts/wasm-runner/TEMPLATE-rust/src/lib.rs`](scripts/wasm-runner/TEMPLATE-rust/src/lib.rs)

构建：

```bash
rustup target add wasm32-unknown-unknown
cargo build --release --target wasm32-unknown-unknown
# → target/wasm32-unknown-unknown/release/yourlang_wasm.wasm
```

必须保留的导入/导出签名：

```rust
// 页面提供的导入:
#[link(wasm_import_module = "toypl")]
extern "C" {
    fn output(ptr: i32, len: i32);
    fn exit(code: i32) -> !;
}

// 页面要求的导出:
#[no_mangle] pub extern "C" fn alloc(size: i32) -> i32;
#[no_mangle] pub extern "C" fn run(ptr: i32, len: i32) -> i32;
// wasm32-unknown-unknown 目标下 memory 由 wasm-ld 自动导出
```

### 托管 wasm（必须有 CORS）

浏览器要能跨域取到文件，托管地址必须带 CORS 头：

| ✅ 推荐 | `https://cdn.jsdelivr.net/gh/<user>/<repo>@<tag>/<path>.wasm` |
| ✅ 推荐 | `https://raw.githubusercontent.com/<user>/<repo>/<branch>/<path>.wasm` |
| ❌ 别用 | GitHub Releases 下载链接（无 CORS 头） |

---

## 3. 合并流程

```
PR ──► 校验通过 ──► 维护者 approve ──> 自动合并（squash）──► 网站 ~1 分钟内更新（bot 合并的 PR 由 5 分钟兜底任务补发）
```

## 4. 本地自测

```bash
python3 main.py validate      # 校验你的条目
python3 main.py build         # 生成站点到 _site/
python3 -m http.server -d _site 8000   # 预览 http://localhost:8000
```
