[English](README.md) | 简体中文

# ToyPLCollector

> 玩具编程语言收集站：一个 TOML 提交一门语言，PR + 自动合并 + 自动上站。

# 网站

**[https://coll.i2pl.com/](https://coll.i2pl.com/)**

（也可通过 <https://azhzx.github.io/ToyPLCollector/> 访问。新语言会自动出现在网站里。）

# 工作方式

```
开发者提交 PR（只新增 collections/<语言名>.toml）
      └─► CI「Validate collections」校验 TOML / URL / 平台枚举
      └─► 维护者点一次 approve
      └─► GitHub 自动合并（auto-merge, squash）
      └─► 站点自动重建并发布（index.html + 每语言 Playground 页）
```

带 `playground`（wasm）的语言可以直接在网页里编辑代码并运行，约定见
[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md#2-在线运行约定toypl-wasm-abi)。

`assets/wasm/` 存放维护者提供的 playground 运行时（如 `riddle.wasm`），构建时
直接随站点发布，同源加载、无需 CORS 配置。

# 如何提交

见 **[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)** —— 复制
[`collections/riddle.toml`](collections/riddle.toml) 填好，发一个 PR 即可。

# 仓库初始化（维护者一次性设置）

1. **Settings → Pages** → Build and deployment → Source: **GitHub Actions**
2. **Settings → General → Pull Requests** → ☑ **Allow auto-merge**
3. **Settings → Rules → Rulesets** → main 分支规则：
   - Require a pull request before merging（1 个 approve）
   - Require status checks：`Validate collections`
   - Block force pushes / deletions
4. 自定义域名 `coll.i2pl.com`：
   - Pages 设置里绑定 `coll.i2pl.com`（构建产物内含 CNAME 文件，由 `make_website.py` 生成）
   - DNS 服务商处添加记录：`coll CNAME → azhzx.github.io`（注意指向本账号的 github.io 主机，不是别的账号）

# 本地开发

```bash
python3 main.py validate        # 校验 collections/*.toml
python3 main.py build           # 生成静态站点到 _site/
python3 -m http.server -d _site 8000   # 预览 http://localhost:8000
```

# 贡献者

<a href="https://github.com/azhzx/ToyPLCollector/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=azhzx/ToyPLCollector" />
</a>
<!-- This image made with [contrib.rocks](https://contrib.rocks).-->
