# GitHub Pages PyPI

用 GitHub Releases 存包，用 GitHub Pages 提供 PEP 503 simple index。

## 你真正需要知道的

- 索引地址：`https://<user>.github.io/<repo>/simple/`
- 默认构建平台：Windows x64、Linux x86_64
- 默认稳定 tag：`a`、`b`、`talib`
- 每次新构建都会先删旧 Release / tag，再用同名稳定 tag 重新发布
- Release 名称只保留包名和版本号，不带 commit SHA
- 不再生成 `SHA256SUMS.txt`

## 关键工作流

- `build-a.yml`：纯 Python 包示例
- `build-b.yml`：编译包示例
- `build-external-template.yml`：外部构建模板
- `talib.yml`：TA-Lib 专用构建
- `update-index.yml`：扫描 Release，更新 Pages 索引
- `update-versions.yml`：更新 `.github/.env` 中的 TA-Lib / Python 构建变量
- `cleanup-legacy-releases.yml`：一次性清掉历史遗留的 `*-v*` / `*-latest` tag 和 Release

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
- Git tag 固定为包名本身，例如 `a`、`b`、`talib`
- 旧的 `a-v*`、`b-v*`、`talib-v*`、`*-latest` 都属于历史遗留
- 现在的 workflow 会在发布前顺手清理同包历史命名
- 已经留在远端的历史垃圾，手动跑一次 `Cleanup Legacy Releases` 即可清干净

## 新包怎么加

- 纯 Python 包：复制 `build-a.yml`
- 编译包：复制 `build-b.yml`
- 外部构建：复制 `build-external-template.yml`
- 改这几个字段：`PACKAGE_NAME`、`RELEASE_TAG`、版本写入路径、产物路径

## Pages 前置条件

- 仓库 Settings → Pages → Source 选 `GitHub Actions`
- 如果 `github-pages` environment 要审批，去掉 Required reviewers

## Token 规则

- `update-versions.yml` 不能再用 `GITHUB_TOKEN` 开 PR
- 必须配置 `UPDATE_VERSIONS_TOKEN`
- 需要的权限：`contents:write`、`pull-requests:write`

## Dependabot 规则

- Dependabot 只负责 workflow 里显式写死的 action 版本
- 它不负责 `TALIB_PY_VER`、`TALIB_C_VER`、`CIBW_BUILD`，因为这些值在 `.github/.env`，由 `update-versions.yml` 维护
- `actions/github-script@v7` 是 Node 20 runtime，所以会出现 Node 20 deprecated 警告
- 现在已经改到 `actions/github-script@v8`，Node 24 runtime
- Dependabot 现在改成每天检查 GitHub Actions；minor/patch 合并，major 单独开 PR，避免大版本升级被埋掉

## 常见问题

- 索引没更新：手动跑 `Update PyPI Index`
- 旧 tag 还在：手动跑 `Cleanup Legacy Releases`
- `Create Pull Request` 被拒：没配 `UPDATE_VERSIONS_TOKEN`
- Pages 404：Pages Source 没设成 `GitHub Actions`

## License

MIT

