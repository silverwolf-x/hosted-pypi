// Source-of-truth dictionary. Other locales are type-checked against this shape
// (see ./index.ts), so a missing or misspelled key fails `npm run check`.
const zh = {
  lang: {
    /** Name of this language, shown in the switcher on the other locale's pages. */
    name: "中文",
    switchTo: "切换到中文",
  },
  meta: {
    description: "基于 GitHub Releases 的自托管 Python 包索引。",
    homeTitle: (repo: string) => `${repo} · Python 包索引`,
    packageTitle: (name: string, version: string) => `${name} ${version} · 预编译 wheel`,
    packageDescription: (name: string, version: string) => `${name} ${version} 的预编译 wheel。`,
  },
  nav: {
    home: "首页",
    packages: "包列表",
    simpleApi: "Simple API",
    github: "GitHub 仓库",
    toggleTheme: "切换深色 / 浅色主题",
  },
  footer: {
    generated: "索引生成于",
    from: "，数据来自",
  },
  copy: {
    label: "复制",
    copied: "已复制",
  },
  install: {
    tablist: "安装方式",
    index: "索引",
  },
  home: {
    badge: "PEP 503 索引 · 由 GitHub Pages 托管",
    headline: "免编译的 wheel，",
    headlineAccent: "一行命令装好。",
    lead: "那些编译起来很折腾的二进制包——在 CI 中为 Windows 和 Linux 构建，以 GitHub Releases 发布，用 pip 或 uv 直接安装。",
    stats: { packages: "包", versions: "版本", wheels: "Wheel", hosted: "总大小" },
    heading: "全部包",
    filterLabel: "按平台筛选",
    filterAll: "全部",
    search: "搜索包",
    empty: "没有匹配的包。",
  },
  os: {
    windows: "Windows",
    linux: "Linux",
    macos: "macOS",
    any: "纯 Python",
  },
  platform: {
    any: "通用",
    pure: "纯 Python",
  },
  card: {
    python: "Python",
    versions: "版本数",
    updated: "更新于",
  },
  pkg: {
    breadcrumb: "面包屑导航",
    latest: "最新",
    published: "发布于",
    files: (n: number) => `${n} 个文件`,
    release: "Release",
    simple: "Simple",
    notLatest: "这不是最新版本。",
    viewLatest: (v: string) => `查看 v${v}`,
    install: "安装",
    compat: "兼容性",
    filesHeading: "文件",
    versionsHeading: "版本",
    links: "链接",
    download: "下载",
    downloadFile: (f: string) => `下载 ${f}`,
    notAvailable: "不可用",
    source: "源码包",
    upstream: "PyPI 上游 ↗",
    allReleases: "全部 Release ↗",
    simplePage: "Simple 索引页",
  },
  notFound: {
    title: "页面不存在",
    heading: "这里什么都没有",
    body: "你要找的页面或包不存在。",
    back: "浏览全部包",
  },
  /** Strings used by client-side scripts; serialized into the page as JSON. */
  client: {
    /** Search result counter; {shown} and {total} are substituted at runtime. */
    count: "{shown} / {total}",
  },
};

export default zh;
