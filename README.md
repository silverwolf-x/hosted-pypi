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
- `talib.yml`：TA-Lib 专用构建
- `update-index.yml`：扫描 Release，更新 Pages 索引
- `update-versions.yml`：更新 `.github/.env` 中的 TA-Lib / Python 构建变量
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

## Token 规则

- `update-versions.yml` 使用 `peter-evans/create-pull-request@v8` 发 PR
- 默认走 `GITHUB_TOKEN`
- 仓库如果禁用了 GitHub Actions 创建 PR，要去 Settings → Actions → General 打开 `Allow GitHub Actions to create and approve pull requests`
- `UPDATE_VERSIONS_TOKEN` 现在只是可选 override，可用 fine-grained PAT 或 GitHub App token，权限为 `contents:write`、`pull-requests:write`

## Dependabot 规则

- Dependabot 只负责 workflow 里显式写死的 action 版本
- 它不负责 `TALIB_PY_VER`、`TALIB_C_VER`、`CIBW_BUILD`，因为这些值在 `.github/.env`，由 `update-versions.yml` 维护
- `actions/github-script@v7` 是 Node 20 runtime，所以会出现 Node 20 deprecated 警告
- 现在已经改到 `actions/github-script@v8`，Node 24 runtime
- Dependabot 现在改成每天检查 GitHub Actions；minor/patch 合并，major 单独开 PR，避免大版本升级被埋掉

## 常见问题

- 索引没更新：手动跑 `Update PyPI Index`
- 旧 tag 还在：手动跑 `Cleanup Legacy Releases`
- `Create Pull Request` 被拒：先检查仓库是否开启了 GitHub Actions 创建 PR；需要时再补 `UPDATE_VERSIONS_TOKEN`
- Pages 404：Pages Source 没设成 `GitHub Actions`

## License

MIT

