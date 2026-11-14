import type { Dict } from "./index";

const en: Dict = {
  lang: {
    name: "English",
    switchTo: "Switch to English",
  },
  meta: {
    description: "Self-hosted Python package index backed by GitHub Releases.",
    homeTitle: (repo) => `${repo} · Python Package Index`,
    packageTitle: (name, version) => `${name} ${version} · wheels`,
    packageDescription: (name, version) => `Prebuilt ${name} ${version} wheels.`,
  },
  nav: {
    home: "Home",
    packages: "Packages",
    simpleApi: "Simple API",
    github: "GitHub repository",
    toggleTheme: "Toggle color theme",
  },
  footer: {
    generated: "Generated",
    from: " from",
  },
  copy: {
    label: "Copy",
    copied: "Copied",
  },
  install: {
    tablist: "Install instructions",
    index: "Index",
  },
  home: {
    badge: "PEP 503 index · served by GitHub Pages",
    headline: "Prebuilt wheels, ",
    headlineAccent: "one index away.",
    lead: "Binary packages that are painful to compile — built in CI for Windows and Linux, published as GitHub Releases, installable with pip or uv.",
    stats: { packages: "Packages", versions: "Versions", wheels: "Wheels", hosted: "Hosted" },
    heading: "Packages",
    filterLabel: "Filter by platform",
    filterAll: "All",
    search: "Search packages",
    empty: "No packages match your search.",
  },
  os: {
    windows: "Windows",
    linux: "Linux",
    macos: "macOS",
    any: "Pure Python",
  },
  platform: {
    any: "Any",
    pure: "pure Python",
  },
  card: {
    python: "Python",
    versions: "Versions",
    updated: "Updated",
  },
  pkg: {
    breadcrumb: "Breadcrumb",
    latest: "latest",
    published: "Published",
    files: (n) => `${n} ${n === 1 ? "file" : "files"}`,
    release: "Release",
    simple: "Simple",
    notLatest: "This is not the latest release.",
    viewLatest: (v) => `View v${v}`,
    install: "Install",
    compat: "Compatibility",
    filesHeading: "Files",
    versionsHeading: "Versions",
    links: "Links",
    download: "Download",
    downloadFile: (f) => `Download ${f}`,
    notAvailable: "not available",
    source: "source",
    upstream: "Upstream on PyPI ↗",
    allReleases: "All releases ↗",
    simplePage: "Simple index page",
  },
  notFound: {
    title: "Not found",
    heading: "Nothing here",
    body: "The page or package you're looking for doesn't exist.",
    back: "Browse packages",
  },
  client: {
    count: "{shown} of {total}",
  },
};

export default en;
