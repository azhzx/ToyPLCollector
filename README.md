# ToyPLCollector

> A community gallery of toy programming languages — collected via PRs, shown on a site.
>
> 玩具编程语言收集站：一个 TOML 提交一门语言，PR + 自动合并 + 自动上站。

# Site ｜ 网站

**[https://coll.i2pl.com/](https://coll.i2pl.com/)**

(也可通过 <https://azhzx.github.io/ToyPLCollector/> 访问。新语言会自动出现在网站里。)

# How it works ｜ 工作方式

```
开发者提交 PR（只新增 collections/<语言名>.toml）
      └─► CI「Validate collections」校验 TOML / URL / 平台枚举
      └─► 维护者点一次 approve
      └─► GitHub 自动合并（auto-merge, squash）
      └─► 站点自动重建并发布（index.html + 每语言 Playground 页）
```

带 `playground`（wasm）的语言可以直接在网页里编辑代码并运行，约定见
[CONTRIBUTING.md](CONTRIBUTING.md#2-online-playground--在线运行约定)。

# Contribute ｜ 如何提交

See **[CONTRIBUTING.md](CONTRIBUTING.md)** — copy
[`collections/riddle.toml`](collections/riddle.toml), fill it in, open a PR.

# Repo setup checklist ｜ 仓库初始化（维护者一次性设置）

1. **Settings → Pages** → Build and deployment → Source: **GitHub Actions**
2. **Settings → General → Pull Requests** → ☑ **Allow auto-merge**
3. **Settings → Rules → Rulesets** → main 分支规则：
   - Require a pull request before merging（1 个 approve）
   - Require status checks：`Validate collections`
   - Block force pushes / deletions
4. 自定义域名 ｜ Custom domain `coll.i2pl.com`：
   - Pages 设置里绑定 `coll.i2pl.com`（构建产物内含 CNAME 文件，由 `make_website.py` 生成）
   - DNS 服务商处添加记录：`coll CNAME → azhzx.github.io`（注意指向本账号，不是其他 github.io 主机）

# Local development ｜ 本地开发

```bash
python3 main.py validate        # lint collections/*.toml
python3 main.py build           # generate the static site into _site/
python3 -m http.server -d _site 8000   # preview at http://localhost:8000
```

# Contributors

<a href="https://github.com/azhzx/ToyPLCollector/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=azhzx/ToyPLCollector" />
</a>
<!-- This image made with [contrib.rocks](https://contrib.rocks).-->
