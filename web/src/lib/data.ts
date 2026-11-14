import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Shape of packages.json written by .github/scripts/generate_index.py
export interface PackageFile {
  filename: string;
  url: string;
  kind: "wheel" | "sdist";
  size: number;
  sha256: string | null;
  uploaded_at: string | null;
  downloads: number;
  python?: string;
  abi?: string;
  platform?: string;
}

export interface PackageVersion {
  version: string;
  release_tag: string;
  release_url: string | null;
  published_at: string | null;
  files: PackageFile[];
}

export interface Package {
  name: string;
  display_name: string;
  latest: string;
  versions: PackageVersion[];
}

export interface IndexData {
  repo: string;
  index_url: string;
  generated_at: string;
  packages: Package[];
}

const DATA_PATH = resolve(process.env.PACKAGES_JSON ?? "../site/packages.json");

let cached: IndexData | undefined;

export function loadIndex(): IndexData {
  if (cached) return cached;
  try {
    cached = JSON.parse(readFileSync(DATA_PATH, "utf-8")) as IndexData;
  } catch (err) {
    throw new Error(
      `Cannot read ${DATA_PATH}. Run .github/scripts/generate_index.py first ` +
        `(or set PACKAGES_JSON). Cause: ${(err as Error).message}`,
    );
  }
  return cached;
}

/** Join a path onto the configured base (BASE_URL may lack a trailing slash). */
export function url(path = ""): string {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  return base + path.replace(/^\//, "");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let n = bytes / 1024;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n < 10 ? 1 : 0)} ${units[i]}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-CA", { timeZone: "UTC" });
}

export type OsKey = "windows" | "linux" | "macos" | "any";

export interface PlatformInfo {
  os: OsKey;
  label: string;
  detail: string;
}

/** Human label for a wheel platform tag, e.g. manylinux_2_34_x86_64. */
export function platformInfo(tag: string | undefined): PlatformInfo {
  if (!tag || tag === "any") return { os: "any", label: "Any", detail: "pure Python" };
  const first = tag.split(".")[0] ?? tag;
  const arch = (s: string) =>
    s.endsWith("amd64") || s.endsWith("x86_64")
      ? "x64"
      : s.endsWith("arm64") || s.endsWith("aarch64")
        ? "ARM64"
        : s.endsWith("universal2")
          ? "Universal"
          : s === "win32" || s.endsWith("i686")
            ? "x86"
            : s.split("_").at(-1) ?? s;
  if (first.startsWith("win")) return { os: "windows", label: `Windows ${arch(first)}`, detail: first };
  if (first.startsWith("macosx")) {
    const m = first.match(/^macosx_(\d+)_(\d+)/);
    return { os: "macos", label: `macOS ${arch(first)}`, detail: m ? `macOS ${m[1]}.${m[2]}+` : first };
  }
  const glibc = first.match(/^manylinux_(\d+)_(\d+)/);
  const legacy: Record<string, string> = { manylinux1: "2.5", manylinux2010: "2.12", manylinux2014: "2.17" };
  const legacyKey = Object.keys(legacy).find((k) => first.startsWith(k));
  if (first.startsWith("musllinux")) return { os: "linux", label: `Linux ${arch(first)} (musl)`, detail: first };
  if (glibc || legacyKey) {
    const ver = glibc ? `${glibc[1]}.${glibc[2]}` : legacy[legacyKey!];
    return { os: "linux", label: `Linux ${arch(first)}`, detail: `glibc ${ver}+` };
  }
  if (first.startsWith("linux")) return { os: "linux", label: `Linux ${arch(first)}`, detail: first };
  return { os: "any", label: first, detail: first };
}

/** Human label for a python tag: cp313 → "3.13", cp313t → "3.13t", py3 → "py3". */
export function pythonLabel(tag: string | undefined): string {
  if (!tag) return "—";
  const m = tag.match(/^cp(\d)(\d+)(t?)$/);
  return m ? `${m[1]}.${m[2]}${m[3]}` : tag;
}

export function pythonSortKey(tag: string): number {
  const m = tag.match(/^cp(\d)(\d+)/);
  return m ? Number(m[1]) * 1000 + Number(m[2]) : 0;
}

export interface PackageSummary {
  platforms: PlatformInfo[];
  pythons: string[];
  updated: string | null;
  fileCount: number;
}

export function summarize(version: PackageVersion): PackageSummary {
  const wheels = version.files.filter((f) => f.kind === "wheel");
  const platforms = new Map<string, PlatformInfo>();
  for (const w of wheels) {
    const p = platformInfo(w.platform);
    platforms.set(p.label, p);
  }
  const pythons = [...new Set(wheels.map((w) => w.python ?? ""))]
    .filter(Boolean)
    .sort((a, b) => pythonSortKey(a) - pythonSortKey(b));
  return {
    platforms: [...platforms.values()].sort((a, b) => a.label.localeCompare(b.label)),
    pythons,
    updated: version.published_at,
    fileCount: version.files.length,
  };
}
