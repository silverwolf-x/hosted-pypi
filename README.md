# 📦 基于 GitHub Pages 的私有 PyPI 服务

用 **GitHub Pages** 托管你自己的 PyPI 仓库，包的构建由 **GitHub Actions** 完成，通过 GitHub Releases 发布。

完全遵循 [PEP 503（Simple Repository API）](https://peps.python.org/pep-0503/)，可直接配合 `pip` 使用，无需任何额外工具。

## ✨ 特性

- **PEP 503 标准兼容** — 用标准 `pip install --extra-index-url` 安装
- **自动更新索引** — 每次发布后自动重新生成索引
- **默认平台收敛** — 默认只构建 Windows x64 和 Linux x64
- **稳定 Tag 发布** — 每个包使用稳定 tag，并在新构建时重新指向最新 commit
- **零基础设施** — 不需要服务器、不需要 Docker，只用 GitHub

---

## 关键约定

- `update-versions.yml` 固定使用 `UPDATE_VERSIONS_TOKEN` 创建 PR；不要再用 `GITHUB_TOKEN` 碰仓库策略。
- 所有包的默认构建平台与 TA-Lib 看齐：只保留 Windows x64 和 Linux x64。
- 每个包使用稳定 tag（如 `a`、`b`、`talib`），新构建时先删除旧 tag / Release，再把同名 tag 重新打到当前构建 commit。
- Release 名称保持干净，只显示包名和版本号，不拼接 commit SHA。

---

## 🚀 快速开始

### 安装包

```bash
pip install <包名> --extra-index-url https://<你的用户名>.github.io/<仓库名>/simple/
```

### 或者写入 `pip.conf`（永久生效）

**Linux**：`~/.config/pip/pip.conf`
**Windows**：`%APPDATA%\pip\pip.ini`

```ini
[global]
extra-index-url = https://<你的用户名>.github.io/<仓库名>/simple/
```

---

## 📐 架构原理

```
┌──────────────────────────────────────────────────────────────────┐
│  GitHub Actions                                                  │
│                                                                  │
│  build-a.yml ──► 构建 wheel ──► 创建 Release（tag: a）          │
│  build-b.yml ──► 构建 wheels ─► 创建 Release（tag: b）          │
│       │                              │                           │
│       └──────── workflow_call ───────┘                           │
│                      │                                           │
│              update-index.yml                                    │
│                      │                                           │
│          generate_index.py                                       │
│          ├─ 通过 GitHub API 扫描所有 Release                      │
│          ├─ 解析 .whl 文件名（包名、版本、平台标签）               │
│          └─ 生成静态 HTML                                         │
│                      │                                           │
│              部署到 GitHub Pages                                  │
└──────────────────────────────────────────────────────────────────┘

GitHub Pages 提供以下页面：
  /                      → 可视化首页（人类可读）
  /simple/               → PEP 503 根索引
  /simple/<包名>/        → 每个包的文件列表页

下载链接指向：
  https://github.com/<用户名>/<仓库名>/releases/download/<tag>/<文件>.whl
```

---

## 🌐 GitHub Pages 在哪里？

当你完成初次配置并触发第一次构建后，索引会自动部署到：

```
https://<你的用户名>.github.io/<仓库名>/
```

具体页面：

| URL | 内容 |
|-----|------|
| `https://user.github.io/repo/` | 可视化首页，展示所有包 |
| `https://user.github.io/repo/simple/` | PEP 503 根索引（pip 使用这个） |
| `https://user.github.io/repo/simple/mypackage/` | 某个包的所有版本下载链接 |

> ⚠️ **本地看不到 GitHub Pages**。Pages 需要推送到 GitHub 并运行工作流之后才存在。  
> 本地只有代码文件，没有部署好的网页——这是正常的。

---

## 🛠 初次配置

### 第一步：创建你的仓库

将本项目作为模板或 Fork 到你自己的 GitHub 账号。

### 第二步：开启 GitHub Pages

1. 进入仓库 **Settings → Pages**
2. 在 **Build and deployment → Source** 下选择 **GitHub Actions**

> **注意**：首次部署时 GitHub 会自动创建 `github-pages` environment。  
> 如果你的组织开启了 **Environment protection rules**，首次部署可能需要手动审批——  
> 去 **Settings → Environments → github-pages** 移除 Required reviewers 即可。

### 第三步：构建第一个包

1. 进入 **Actions → Build Package A**（或 B）
2. 点击 **Run workflow**
3. 输入版本号（例如 `1.0.0`）
4. 等待工作流完成

工作流会自动：
- 构建 wheel 包
- 删除该包旧的 tag / Release，并把稳定 tag（如 `a`）重新打到本次构建 commit
- 创建 GitHub Release，并上传本次构建的 `.whl`、`.tar.gz`
- 重新生成 PyPI 索引
- 部署到 GitHub Pages

### 第四步：验证

访问 `https://<你的用户名>.github.io/<仓库名>/` 查看首页，或直接安装：

```bash
pip install a --extra-index-url https://<你的用户名>.github.io/<仓库名>/simple/
```

---

## 📁 目录结构

```
.github/
  scripts/
    generate_index.py                    # 核心：从 Release 生成 PEP 503 索引
  workflows/
    update-index.yml                      # 重新生成索引并部署到 Pages
    build-a.yml                           # 示例：构建纯 Python 包（有源码目录）
    build-b.yml                           # 示例：构建编译包（有源码目录）
    build-external-template.yml           # 模板：外部构建（无 packages/ 目录）
packages/
  a/                                      # 示例：纯 Python 包源码
  b/                                      # 示例：C 扩展包源码
```

> **packages/ 目录不是必须的。** 它只是示例。你完全可以在另一个仓库里构建包，只要最终把 wheel 上传到这个仓库的 Release 资产即可。

---

## ➕ 两种方式添加新包

### 方式一：包源码在本仓库（packages/ 模式）

适合：自己编写的 Python 包，源码在本仓库管理。

**第一步：创建包源码**

```
packages/mypackage/
  pyproject.toml
  mypackage/__init__.py
```

`pyproject.toml` 示例：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mypackage"
version = "0.1.0"
description = "我的自定义包"
requires-python = ">=3.9"
```

**第二步：复制并修改构建工作流**

复制 `build-a.yml`（纯 Python）或 `build-b.yml`（编译包），改名为 `build-mypackage.yml`，修改：

| 字段 | 改为 |
|---|---|
| `working-directory: packages/a` | `packages/mypackage` |
| `RELEASE_TAG: a` | `mypackage` |
| artifact 名称 | 改成对应的包名 |
| workflow `name:` | `Build Package MyPackage` |

---

### 方式二：外部构建（无 packages/ 目录）

适合：直接调用编译脚本构建第三方 C 库的 Python 绑定，或任何不需要 Python 源码目录的场景（类似 [cgohlke/talib-build](https://github.com/cgohlke/talib-build) 的模式）。

**核心思路**：构建流程完全自定义，只需要最终产物满足：
1. wheels 存在于 `./wheelhouse/` 或 `./dist/`
2. 创建 GitHub Release 并上传 wheels 资产
3. 调用 `update-index.yml`

**使用 `build-external-template.yml`：**

1. 复制 `.github/workflows/build-external-template.yml`，改名为 `build-mylib.yml`
2. 修改 `env.PACKAGE_NAME: "mylib"`
3. 在各平台 job 的 "=== 你的构建步骤 ===" 区域填入自己的构建逻辑：

```yaml
# 示例：构建依赖第三方 C 库的包（类 talib-build 风格）
steps:
  - uses: actions/checkout@v4

  # 下载并编译 C 库
  - name: 编译 mylib C 库
    run: |
      wget https://example.com/mylib-1.0.tar.gz
      tar xf mylib-1.0.tar.gz
      cd mylib-1.0 && ./configure --prefix=/usr/local && make install

  # 设置版本并用 cibuildwheel 构建 Python wheel
  - name: 用 cibuildwheel 构建
    uses: pypa/cibuildwheel@v2.21.3
    env:
      CIBW_ENVIRONMENT: MY_LIB_PATH="/usr/local/lib"

  - uses: actions/upload-artifact@v4
    with:
      name: wheels-mylib-linux
      path: ./wheelhouse/*.whl
```

4. 默认模板已经只保留 Linux x64 和 Windows x64；如果你只需要单平台，再删掉对应 job 即可
5. 保留模板中的 `release` 和 `update-index` job，其中 `release` 会先删除旧 tag / Release，再用稳定 tag 重新发布

**触发构建：** Actions → Build MyLib → Run workflow → 输入版本号

---

## ⚙️ 索引生成器工作原理

`generate_index.py` 在 GitHub Actions 中运行，流程如下：

1. **获取所有 Release**（分页处理，支持超过 100 个）
2. **跳过草稿**——只有已发布的 Release 才会被索引
3. **解析 wheel 文件名**——按 [PEP 427](https://peps.python.org/pep-0427/) 提取包名、版本、平台标签
4. **生成下载链接**——直接使用 Release 资产地址生成索引
5. **生成静态 HTML**：
   - `/simple/index.html` — 所有包的根索引
   - `/simple/<包名>/index.html` — 每个包的下载链接列表
   - `/index.html` — 人类可读的首页
6. **通过 `actions/deploy-pages` 部署**

### Wheel 文件名格式（PEP 427）

```
{包名}-{版本}(-{build})?-{python}-{abi}-{平台}.whl
```

示例：

| 文件名 | 含义 |
|--------|------|
| `a-1.0.0-py3-none-any.whl` | 纯 Python，所有平台 |
| `b-2.1.1-cp312-cp312-manylinux_2_17_x86_64.whl` | Linux x86_64 |
| `b-2.1.1-cp312-cp312-win_amd64.whl` | Windows x64 |

pip 会自动选择与当前系统和 Python 版本匹配的 wheel。

---

## 📝 Tag 命名规范

Release tag 直接使用包名本身，并在每次新构建时重新指向最新构建 commit。

| 包名 | Tag |
|------|-----|
| a | `a` |
| b | `b` |
| talib | `talib` |

每次新构建都会先删除该包此前的 tag 和同名 Release，再把同一个稳定 tag 重新打到当前构建 commit。实际的包版本信息仍然来自 wheel / sdist 文件名本身。

---

## ❓ 常见问题

**pip 怎么知道下载哪个 wheel？**  
pip 根据当前系统平台、Python 版本、ABI 匹配 wheel 文件名，自动选择兼容的版本下载。

**可以用 `--index-url` 代替 `--extra-index-url` 吗？**  
可以，但这样 pip 只会查询你的私有索引，不再回退到 PyPI。如果包依赖 PyPI 上的其他包，请用 `--extra-index-url`。

**为什么 `release: published` 触发器对自动构建无效？**  
GitHub 安全策略：`GITHUB_TOKEN` 创建的事件不会触发其他 workflow。因此构建工作流通过 `workflow_call` 显式调用 `update-index.yml`。如果你手动在 GitHub 页面创建 Release，`release: published` 触发器仍然有效。

**为什么 `update-versions.yml` 不能直接用 `GITHUB_TOKEN` 开 PR？**  
部分仓库会禁用 GitHub Actions 直接创建或审批 Pull Request，这时 `GITHUB_TOKEN` 即使有 `pull-requests: write` 也会被平台拒绝。根因方案是配置 `UPDATE_VERSIONS_TOKEN` secret，并让工作流固定用这个 token 创建 PR。

**支持私有仓库吗？**  
本项目**面向公开仓库设计**。GitHub Pages 公开提供索引，Release 下载链接对公开仓库也无需认证。  
私有仓库场景下，release asset 下载需要 API 认证（`Authorization` header），而 pip 不原生支持。如有需要，可改造 `generate_index.py` 将 `.whl` 文件直接嵌入 Pages 目录（替代链接跳转），或使用 [AWS CodeArtifact](https://aws.amazon.com/codeartifact/) / [自建 pypiserver](https://github.com/pypiserver/pypiserver) 等方案。

**如何手动刷新索引？**  
进入 **Actions → Update PyPI Index → Run workflow**，会重新扫描所有 Release 并重新部署。

---

## 🔧 常见问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| Pages 返回 404 | Pages Source 未设为 GitHub Actions | Settings → Pages → Source → **GitHub Actions** |
| Workflow 卡在 "Waiting for approval" | `github-pages` environment 有审批规则 | Settings → Environments → github-pages → 移除 Required reviewers |
| `Create Pull Request` 被拒绝 | 未配置 `UPDATE_VERSIONS_TOKEN`，或仍在用 `GITHUB_TOKEN` 开 PR | 配置具备 `contents:write` 和 `pull-requests:write` 权限的 `UPDATE_VERSIONS_TOKEN` secret |
| `pip install` 报 404 | URL 末尾缺少斜杠 | 使用 `.../simple/`（末尾带 `/`） |
| 构建后索引为空 | `update-index` 工作流未运行或失败 | Actions → **Update PyPI Index** → Run workflow |
| 旧版本在索引中消失 | 稳定 tag 发布会删除旧 Release，或 Release 仍为草稿 | 这是当前策略的预期行为；如需保留历史版本，请改回版本化 tag |
| `pkg.__version__` 显示旧值 | `__init__.py` 未同步版本 | 使用工作流构建，不要手动 build |

---

## 📄 License

MIT

