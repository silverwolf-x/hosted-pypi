# GitHub Pages PyPI

用 GitHub Releases 存包，用 GitHub Pages 提供 PEP 503 simple index。

## 你真正需要知道的

- 索引地址：`https://<user>.github.io/<repo>/simple/`
- 默认构建平台：Windows x64、Linux x86_64
- tag / Release 命名：`a-v1.0.0`、`b-v1.0.1`、`talib-v0.6.8`
- 如果重复构建同一版本，会先删掉同版本旧 tag / Release，再在新 commit 上重建同名 tag / Release
- Release 名称和 tag 保持一致
- 不再生成 `SHA256SUMS.txt`

## 关键工作流

- `build-a.yml`：纯 Python 包示例
- `build-b.yml`：编译包示例
- `build-external-template.yml`：外部构建模板
- `talib.yml`：TA-Lib 专用构建（可被 `update-versions.yml` 调用）
- `update-index.yml`：扫描 Release，生成 PEP 503 索引 + `packages.json`，构建 `web/` 前端并部署 Pages
- `update-versions.yml`：每周检查上游版本，有变化就直接提交 `.github/.env` 并立即构建发布 TA-Lib
- `dependabot-automerge.yml`：自动合并 Dependabot PR（npm 需先构建通过）
- `cleanup-legacy-releases.yml`：一次性清掉历史遗留的非版本化 tag / Release（如 `a`、`b`、`talib`、`*-latest`）

## 快速使用

安装：

```bash
pip install <package> --extra-index-url https://<user>.github.io/<repo>/simple/
```

持久配置：

Linux: `~/.config/pip/pip.conf`
Windows: `%APPDATA%\pip\pip.ini`

```ini
[global]
extra-index-url = https://<user>.github.io/<repo>/simple/
```

## 发布规则

- 包版本来自 wheel / sdist 文件名，不来自 Git tag 名称
- Git tag 和 Release 名称统一为 `<package>-v<version>`
- 例如：`a-v1.0.0`、`b-v1.0.1`、`talib-v0.6.8`
- 如果同一版本重新构建，workflow 只删除同名旧 tag / Release，然后把同名 tag 重新打到新的 commit
- 历史错误命名（`a`、`b`、`talib`、`*-latest`）可用 `Cleanup Legacy Releases` 一次性清理

## 新包怎么加

- 纯 Python 包：复制 `build-a.yml`
- 编译包：复制 `build-b.yml`
- 外部构建：复制 `build-external-template.yml`
- 改这几个字段：`PACKAGE_NAME`、版本写入路径、产物路径

## Pages 前置条件

- 仓库 Settings → Pages → Source 选 `GitHub Actions`
- 如果 `github-pages` environment 要审批，去掉 Required reviewers

## TA-Lib 自动更新

- 每周一 `update-versions.yml` 拉取 PyPI / ta-lib C 库 / Python / manylinux 最新版本
- 有变化：直接 commit `.github/.env` 到 `main`，同一次运行内调用 `talib.yml` 构建 → Release → 更新 Pages
- 不再走 PR：之前 PR 需要人工合并，且 `talib.yml` 的 push 触发器监听的是不存在的 `dev` 分支，所以新版本一直没构建
- 手动强制重建：运行 `Update Versions` 时勾选 `force_build`，或直接运行 `Build TA-Lib Wheels`
- 只用默认 `GITHUB_TOKEN`，不需要额外 secret；`main` 如果加了分支保护，需要允许 GitHub Actions 推送

## 前端

- `web/`：Astro + TypeScript + Tailwind CSS v4，纯静态输出；数据来自 `generate_index.py` 生成的 `packages.json`
- 首页：搜索（`/` 或 `Ctrl+K`）、平台筛选、pip / uv / pyproject / pip.conf 安装命令
- 包详情页：Python × 平台兼容矩阵、文件 sha256、历史版本页 `packages/<name>/<version>/`
- 多语言：默认中文（根路径），英文在 `en/` 下；页头可切换，不按浏览器语言自动跳转。文案在 `web/src/i18n/{zh,en}.ts`，`en` 按 `zh` 的键做类型检查
- 本地预览：

```bash
GITHUB_REPOSITORY=<user>/<repo> GITHUB_TOKEN=$(gh auth token) python .github/scripts/generate_index.py
cd web && npm ci && npm run dev
```

## Dependabot 规则

- Dependabot 只负责 workflow 里显式写死的 action 版本
- 它不负责 `TALIB_PY_VER`、`TALIB_C_VER`、`CIBW_BUILD`，因为这些值在 `.github/.env`，由 `update-versions.yml` 维护
- `web/` 的 npm 依赖每周一次合并为一个 PR；忽略 major（如 TypeScript 7 与 `@astrojs/check` 的 peer 冲突），需人工升级
- 自动合并：`dependabot-automerge.yml` 对所有 Dependabot PR 直接 squash 合并并删除分支，仓库只保留 `main`
  - npm（`web/`）PR 先跑 `npm ci` + `npm run check` + `npm run build`（数据用 `web/fixtures/packages.json`），通过才合并，合并后自动 dispatch `Update PyPI Index` 重新部署
  - 默认用 `GITHUB_TOKEN`；它没有 `workflows` 权限，合并修改 `.github/workflows/*` 的 Action 升级 PR 可能被拒。需要时在 Settings → Secrets and variables → **Dependabot** 添加 `DEPENDABOT_AUTOMERGE_TOKEN`（fine-grained PAT：Contents / Pull requests / Workflows 读写），有它会优先使用
- `actions/github-script@v7` 是 Node 20 runtime，所以会出现 Node 20 deprecated 警告
- 现在已经改到 `actions/github-script@v8`，Node 24 runtime
- Dependabot 现在改成每天检查 GitHub Actions；minor/patch 合并，major 单独开 PR，避免大版本升级被埋掉

## 常见问题

- 索引没更新：手动跑 `Update PyPI Index`
- 旧 tag 还在：手动跑 `Cleanup Legacy Releases`
- `Update Versions` 推送失败：检查 `main` 分支保护是否允许 GitHub Actions 推送
- Pages 404：Pages Source 没设成 `GitHub Actions`

## License

MIT

