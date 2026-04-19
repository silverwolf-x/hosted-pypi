#!/usr/bin/env python3
"""
Generate PEP 503 compliant PyPI Simple Repository Index from GitHub Releases.

Scans all releases in a GitHub repository, finds .whl and .tar.gz assets,
and generates static HTML pages for use as a pip-compatible package index
served via GitHub Pages.

Usage:
    GITHUB_REPOSITORY=owner/repo GITHUB_TOKEN=xxx python generate_index.py

Environment Variables:
    GITHUB_REPOSITORY  - Required. Owner/repo (e.g., 'myuser/pypi-index')
    GITHUB_TOKEN       - Optional. GitHub token for API access
    OUTPUT_DIR         - Optional. Output directory (default: 'site')
"""

import html
import os
import re
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

GITHUB_API = "https://api.github.com"


def normalize(name: str) -> str:
    """Normalize package name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_wheel_filename(filename: str):
    """
    Parse a wheel filename into (name, version).

    Wheel format (PEP 427):
        {name}-{version}(-{build})?-{python}-{abi}-{platform}.whl
    """
    if not filename.endswith(".whl"):
        return None, None
    stem = filename[:-4]
    parts = stem.split("-")
    if len(parts) >= 5:
        return parts[0], parts[1]
    return None, None


def parse_sdist_filename(filename: str):
    """
    Parse a source distribution filename into (name, version).
    Supports .tar.gz and .zip formats.
    """
    for ext in (".tar.gz", ".zip"):
        if filename.endswith(ext):
            stem = filename[: -len(ext)]
            parts = stem.split("-")
            for i in range(1, len(parts)):
                if parts[i] and parts[i][0].isdigit():
                    name = "-".join(parts[:i])
                    version = "-".join(parts[i:])
                    return name, version
            break
    return None, None


def github_api_request(url: str, token: str = None):
    """Make a GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "pypi-index-generator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason} for {url}", file=sys.stderr)
        raise


def get_all_releases(repo: str, token: str = None) -> list:
    """Fetch all releases with pagination."""
    releases = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{repo}/releases?page={page}&per_page=100"
        try:
            data = github_api_request(url, token)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if page == 1:
                # First page failure is fatal — we have no data at all
                print(f"Fatal: cannot fetch releases: {e}", file=sys.stderr)
                sys.exit(1)
            # Later pages: warn but use what we have
            print(
                f"Warning: pagination stopped at page {page}: {e}",
                file=sys.stderr,
            )
            break
        if not data:
            break
        releases.extend(data)
        if len(data) < 100:
            break
        page += 1
    return releases


def download_asset_text(url: str, token: str = None) -> str:
    """Download text content from a GitHub API asset URL."""
    headers = {
        "Accept": "application/octet-stream",
        "User-Agent": "pypi-index-generator",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_checksums_file(content: str) -> dict:
    """Parse SHA256SUMS file into {filename: hash} dict."""
    checksums = {}
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            hash_val, fname = parts
            checksums[fname.lstrip("*").strip()] = hash_val
    return checksums


def collect_packages(releases: list, token: str = None) -> tuple:
    """
    Scan releases and collect all package files.

    Returns:
        (packages_dict, latest_versions_dict)
        packages_dict:  {normalized_name: [file_info_dict, ...]}
        latest_versions_dict: {normalized_name: version_str}
    """
    packages = defaultdict(list)
    latest_versions = {}
    seen_files = set()

    for release in releases:
        if release.get("draft"):
            continue

        tag = release.get("tag_name", "")
        assets = release.get("assets", [])

        # Look for checksums file in release assets
        checksums = {}
        for asset in assets:
            if asset["name"].lower() in (
                "sha256sums",
                "checksums.txt",
                "sha256sums.txt",
            ):
                try:
                    content = download_asset_text(asset["url"], token)
                    checksums = parse_checksums_file(content)
                    print(f"  [{tag}] Loaded {len(checksums)} checksums")
                except Exception as e:
                    print(
                        f"  [{tag}] Warning: checksums read failed: {e}",
                        file=sys.stderr,
                    )
                break

        # Process each asset
        for asset in assets:
            filename = asset["name"]

            if filename.endswith(".whl"):
                pkg_name, version = parse_wheel_filename(filename)
            elif filename.endswith(".tar.gz") or filename.endswith(".zip"):
                pkg_name, version = parse_sdist_filename(filename)
            else:
                continue

            if not pkg_name or not version:
                print(
                    f"  [{tag}] Warning: cannot parse: {filename}",
                    file=sys.stderr,
                )
                continue

            norm_name = normalize(pkg_name)
            file_key = (norm_name, filename)
            if file_key in seen_files:
                continue
            seen_files.add(file_key)

            packages[norm_name].append(
                {
                    "filename": filename,
                    "url": asset["browser_download_url"],
                    "sha256": checksums.get(filename, ""),
                    "version": version,
                }
            )

            # Track latest version (releases come newest-first from API)
            if norm_name not in latest_versions:
                latest_versions[norm_name] = version

    return packages, latest_versions


def generate_simple_index(packages: dict, output_dir: Path):
    """Generate PEP 503 Simple Repository API pages."""
    simple_dir = output_dir / "simple"
    simple_dir.mkdir(parents=True, exist_ok=True)

    # /simple/index.html  ──  root index listing all projects
    with open(simple_dir / "index.html", "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n")
        f.write('<html lang="en">\n<head>\n')
        f.write('  <meta charset="utf-8">\n')
        f.write('  <meta name="pypi:repository-version" content="1.0">\n')
        f.write("  <title>Simple Index</title>\n")
        f.write("</head>\n<body>\n")
        f.write("  <h1>Simple Index</h1>\n")
        for name in sorted(packages.keys()):
            safe_name = html.escape(name)
            f.write(f'  <a href="{safe_name}/">{safe_name}</a><br>\n')
        f.write("</body>\n</html>\n")

    # /simple/<package>/index.html  ──  per-project file listing
    for name, files in packages.items():
        pkg_dir = simple_dir / name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        with open(pkg_dir / "index.html", "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html>\n")
            f.write('<html lang="en">\n<head>\n')
            f.write('  <meta charset="utf-8">\n')
            f.write('  <meta name="pypi:repository-version" content="1.0">\n')
            f.write(f"  <title>Links for {name}</title>\n")
            f.write("</head>\n<body>\n")
            f.write(f"  <h1>Links for {html.escape(name)}</h1>\n")
            for fi in sorted(files, key=lambda x: x["filename"]):
                href = fi["url"]
                if fi.get("sha256"):
                    href += f"#sha256={fi['sha256']}"
                safe_fn = html.escape(fi["filename"])
                safe_href = html.escape(href, quote=True)
                f.write(f'  <a href="{safe_href}">{safe_fn}</a><br>\n')
            f.write("</body>\n</html>\n")


def generate_landing_page(
    packages: dict,
    latest_versions: dict,
    repo: str,
    output_dir: Path,
):
    """Generate a modern dark-themed landing page for the private PyPI index."""
    repo_owner, repo_name = repo.split("/")
    base_url = f"https://{repo_owner}.github.io/{repo_name}"
    pip_index_url = f"{base_url}/simple/"
    pkg_count = len(packages)

    e_repo_name = html.escape(repo_name)
    e_base_url = html.escape(base_url)
    e_pip_index = html.escape(pip_index_url)
    e_repo = html.escape(repo)
    pip_cmd = html.escape(f"pip install PACKAGE --extra-index-url {pip_index_url}")

    rows_html = []
    for name in sorted(packages.keys()):
        safe = html.escape(name)
        ver = html.escape(latest_versions.get(name, ""))
        fc = len(packages[name])
        badge = f'<span class="badge">{ver}</span>' if ver else ""
        rows_html.append(
            f'      <tr data-name="{safe}">'
            f'<td><a href="simple/{safe}/" class="pkg-link">{safe}</a></td>'
            f"<td>{badge}</td>"
            f'<td class="file-count">{fc} file{"s" if fc != 1 else ""}</td>'
            f"</tr>"
        )
    rows = "\n".join(rows_html)

    # CSS uses {{ / }} to escape braces inside the f-string
    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e_repo_name} &middot; Private PyPI</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg:       #0d1117;
      --surface:  #161b22;
      --surface2: #21262d;
      --border:   #30363d;
      --text:     #e6edf3;
      --muted:    #8b949e;
      --accent:   #58a6ff;
      --accent-h: #79b8ff;
      --badge-bg: #1c2b3a;
      --badge-bd: #1c4a7a;
      --green:    #3fb950;
      --r:        8px;
      --font:     -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      --mono:     "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }}
    body {{
      background: var(--bg); color: var(--text);
      font-family: var(--font); font-size: 14px;
      line-height: 1.6; min-height: 100vh;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: var(--accent-h); text-decoration: underline; }}

    .wrap {{ max-width: 860px; margin: 0 auto; padding: 36px 20px 64px; }}

    /* ── Header ─────────────────────────────── */
    .hdr {{ margin-bottom: 30px; padding-bottom: 22px; border-bottom: 1px solid var(--border); }}
    .hdr-top {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
    .icon {{
      width: 38px; height: 38px; border-radius: 8px; font-size: 20px;
      display: flex; align-items: center; justify-content: center;
      background: linear-gradient(135deg, #1c2b3a, #1a3a5c);
      border: 1px solid var(--border);
    }}
    h1 {{ font-size: 22px; font-weight: 600; }}
    .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 10px; }}
    .pill {{
      display: inline-flex; align-items: center; gap: 5px;
      background: var(--surface2); border: 1px solid var(--border);
      border-radius: 20px; padding: 2px 11px;
      font-size: 12px; color: var(--muted);
    }}
    .pill b {{ color: var(--text); }}

    /* ── Install card ───────────────────────── */
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); padding: 16px 18px; margin-bottom: 26px;
    }}
    .card-lbl {{
      font-size: 11px; font-weight: 600; letter-spacing: .08em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 9px;
    }}
    .cmd-row {{
      display: flex; align-items: center; gap: 10px;
      background: var(--bg); border: 1px solid var(--border);
      border-radius: 6px; padding: 10px 14px;
    }}
    .cmd-row code {{
      flex: 1; font-family: var(--mono); font-size: 13px;
      color: var(--accent); word-break: break-all;
    }}
    .copy-btn {{
      background: var(--surface2); border: 1px solid var(--border);
      border-radius: 6px; color: var(--muted); cursor: pointer;
      font-size: 12px; padding: 5px 13px; white-space: nowrap;
      font-family: var(--font);
      transition: background .15s, color .15s, border-color .15s;
    }}
    .copy-btn:hover {{ background: var(--border); color: var(--text); }}
    .copy-btn.ok {{ color: var(--green); border-color: var(--green); }}
    .idx-url {{ margin-top: 8px; font-size: 12px; color: var(--muted); }}
    .idx-url a {{ font-family: var(--mono); font-size: 12px; }}

    /* ── Search row ─────────────────────────── */
    .search-row {{
      display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
    }}
    .search {{
      flex: 1; background: var(--surface); border: 1px solid var(--border);
      border-radius: 6px; color: var(--text); font-family: var(--font);
      font-size: 13px; padding: 8px 14px; outline: none;
      transition: border-color .15s;
    }}
    .search::placeholder {{ color: var(--muted); }}
    .search:focus {{ border-color: var(--accent); }}
    .cnt {{ font-size: 12px; color: var(--muted); white-space: nowrap; }}

    /* ── Package table ──────────────────────── */
    .tbl {{
      width: 100%; border-collapse: collapse;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); overflow: hidden;
    }}
    .tbl thead tr {{ background: var(--surface2); border-bottom: 1px solid var(--border); }}
    .tbl th {{
      padding: 9px 16px; text-align: left;
      font-size: 11px; font-weight: 600;
      letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
    }}
    .tbl th:last-child {{ text-align: right; }}
    .tbl tbody tr {{ border-bottom: 1px solid var(--border); transition: background .1s; }}
    .tbl tbody tr:last-child {{ border-bottom: none; }}
    .tbl tbody tr:hover {{ background: var(--surface2); }}
    .tbl tbody tr.hidden {{ display: none; }}
    .tbl td {{ padding: 9px 16px; vertical-align: middle; }}
    .pkg-link {{ font-family: var(--mono); font-size: 13px; font-weight: 500; }}
    .badge {{
      display: inline-block;
      background: var(--badge-bg); color: var(--accent);
      border: 1px solid var(--badge-bd);
      border-radius: 20px; padding: 1px 9px;
      font-size: 11px; font-family: var(--mono); white-space: nowrap;
    }}
    .file-count {{ color: var(--muted); font-size: 12px; text-align: right; }}
    .no-match {{ text-align: center; padding: 32px 0; color: var(--muted); font-size: 13px; }}

    /* ── Footer ─────────────────────────────── */
    .footer {{
      margin-top: 36px; padding-top: 16px;
      border-top: 1px solid var(--border);
      color: var(--muted); font-size: 12px; text-align: center;
    }}
    .footer a {{ color: var(--muted); }}
    .footer a:hover {{ color: var(--accent); }}
  </style>
</head>
<body>
<div class="wrap">

  <header class="hdr">
    <div class="hdr-top">
      <div class="icon">&#128230;</div>
      <h1>{e_repo_name}</h1>
    </div>
    <p class="sub">Private Python Package Index &mdash; powered by GitHub Releases</p>
    <span class="pill"><b>{pkg_count}</b> package{"s" if pkg_count != 1 else ""}</span>
  </header>

  <div class="card">
    <div class="card-lbl">Install a package</div>
    <div class="cmd-row">
      <code id="pip-cmd">{pip_cmd}</code>
      <button class="copy-btn" onclick="doCopy(this)">Copy</button>
    </div>
    <p class="idx-url">Index URL: <a href="{e_pip_index}">{e_pip_index}</a></p>
  </div>

  <div class="search-row">
    <input class="search" type="search" id="q"
           placeholder="Filter packages&hellip;"
           oninput="doFilter(this.value)"
           autocomplete="off" spellcheck="false">
    <span class="cnt" id="cnt">{pkg_count} package{"s" if pkg_count != 1 else ""}</span>
  </div>

  <table class="tbl" id="tbl">
    <thead>
      <tr>
        <th>Package</th>
        <th>Latest</th>
        <th>Files</th>
      </tr>
    </thead>
    <tbody>
{rows}
      <tr id="no-match" class="hidden">
        <td colspan="3"><div class="no-match">No packages match your search.</div></td>
      </tr>
    </tbody>
  </table>

  <footer class="footer">
    <a href="{e_base_url}/simple/">Simple Index (PEP&nbsp;503)</a>
    &nbsp;&middot;&nbsp;
    <a href="https://github.com/{e_repo}">GitHub Repository</a>
  </footer>

</div>
<script>
  var TOTAL = {pkg_count};

  function doCopy(btn) {{
    var txt = document.getElementById('pip-cmd').textContent;
    navigator.clipboard.writeText(txt).then(function () {{
      btn.textContent = 'Copied!';
      btn.classList.add('ok');
      setTimeout(function () {{ btn.textContent = 'Copy'; btn.classList.remove('ok'); }}, 2000);
    }}).catch(function () {{
      btn.textContent = 'Error';
      setTimeout(function () {{ btn.textContent = 'Copy'; }}, 2000);
    }});
  }}

  function doFilter(q) {{
    q = q.toLowerCase().trim();
    var rows = document.querySelectorAll('#tbl tbody tr[data-name]');
    var n = 0;
    rows.forEach(function (r) {{
      var show = !q || r.dataset.name.indexOf(q) !== -1;
      r.classList.toggle('hidden', !show);
      if (show) n++;
    }});
    document.getElementById('no-match').classList.toggle('hidden', n > 0);
    var lbl = q ? (n + ' of ' + TOTAL) : TOTAL;
    document.getElementById('cnt').textContent = lbl + ' package' + (TOTAL === 1 ? '' : 's');
  }}
</script>
</body>
</html>"""

    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(content)


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    output_dir = Path(os.environ.get("OUTPUT_DIR", "site"))

    if not repo:
        print(
            "Error: GITHUB_REPOSITORY environment variable is required",
            file=sys.stderr,
        )
        sys.exit(1)

    if "/" not in repo or repo.count("/") != 1:
        print(
            f"Error: GITHUB_REPOSITORY must be 'owner/repo', got '{repo}'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Generating PyPI index for {repo} ...")

    releases = get_all_releases(repo, token)
    print(f"Found {len(releases)} release(s)")

    packages, latest_versions = collect_packages(releases, token)
    print(f"Indexed {len(packages)} package(s)")

    output_dir.mkdir(parents=True, exist_ok=True)
    generate_simple_index(packages, output_dir)
    generate_landing_page(packages, latest_versions, repo, output_dir)

    print(f"Index written to {output_dir}/")


if __name__ == "__main__":
    main()
