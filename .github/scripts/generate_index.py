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
    """Generate a human-friendly landing page at /index.html."""
    repo_owner, repo_name = repo.split("/")
    base_url = f"https://{repo_owner}.github.io/{repo_name}"

    # Build package card HTML fragments
    cards_html = ""
    for name in sorted(packages.keys()):
        files = packages[name]
        versions = sorted(set(f["version"] for f in files))
        latest = latest_versions.get(name, versions[-1] if versions else "?")

        # Collect unique platform tags from wheel filenames
        architectures = set()
        for f in files:
            fname = f["filename"]
            if fname.endswith(".whl"):
                parts = fname[:-4].split("-")
                if len(parts) >= 5:
                    architectures.add(parts[-1])

        arch_badges = "".join(
            f'<span class="badge">{a}</span>' for a in sorted(architectures)
        )
        if not arch_badges:
            arch_badges = '<span class="badge">any</span>'

        cards_html += (
            '<div class="card">'
            f'<h3>\U0001f40d {name} <span class="version">v{latest}</span></h3>'
            f'<div class="meta">{len(versions)} version(s) &middot; '
            f'{len(files)} file(s)</div>'
            f'<div style="margin-top:.5rem">{arch_badges}</div>'
            "</div>\n"
        )

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>\U0001f4e6 {repo_name} \u2013 Private PyPI Index</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
             background:#f5f5f5;color:#333}}
        .container{{max-width:900px;margin:0 auto;padding:2rem 1rem}}
        header{{text-align:center;margin-bottom:2rem}}
        header h1{{font-size:2rem;margin-bottom:.5rem}}
        header p{{color:#666}}
        .install-box{{background:#1e1e1e;color:#d4d4d4;padding:1rem 1.5rem;
            border-radius:8px;margin:1.5rem 0;
            font-family:"Fira Code","Cascadia Code",monospace;font-size:.9rem;
            overflow-x:auto}}
        .install-box code{{color:#9cdcfe}}
        .install-box .cmt{{color:#6a9955}}
        h2{{margin:1.5rem 0 .5rem}}
        .cards{{display:grid;gap:1rem}}
        .card{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;
            padding:1.25rem;transition:box-shadow .2s}}
        .card:hover{{box-shadow:0 2px 8px rgba(0,0,0,.1)}}
        .card h3{{font-size:1.1rem;margin-bottom:.5rem}}
        .version{{background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:4px;
            font-size:.85rem;font-weight:600}}
        .meta{{color:#888;font-size:.85rem;margin-top:.5rem}}
        .badge{{display:inline-block;background:#f0f0f0;color:#555;padding:2px 6px;
            border-radius:3px;font-size:.75rem;margin:2px;font-family:monospace}}
        footer{{text-align:center;margin-top:3rem;color:#999;font-size:.85rem}}
        a{{color:#1565c0;text-decoration:none}}
        a:hover{{text-decoration:underline}}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>\U0001f4e6 {repo_name}</h1>
            <p>Private PyPI repository hosted on GitHub Pages</p>
        </header>

        <div class="install-box">
            <span class="cmt"># Install a package from this index</span><br>
            <code>pip install &lt;package_name&gt; --extra-index-url {base_url}/simple/</code>
        </div>

        <h2>\U0001f4cb Packages ({len(packages)})</h2>
        <div class="cards">
{cards_html}        </div>

        <footer>
            <p>
                <a href="simple/">\U0001f4c2 Simple Index (PEP 503)</a> &middot;
                <a href="https://github.com/{repo}">\U0001f517 GitHub Repository</a>
            </p>
            <p style="margin-top:.5rem">
                Powered by GitHub Pages &middot; Auto-generated from GitHub Releases
            </p>
        </footer>
    </div>
</body>
</html>"""

    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(page_html)


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
