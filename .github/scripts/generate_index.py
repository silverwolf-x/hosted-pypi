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
    PAGES_BASE_URL     - Optional. Pages base URL (default: https://<owner>.github.io/<repo>)

Outputs:
    <OUTPUT_DIR>/simple/        PEP 503 index for pip
    <OUTPUT_DIR>/packages.json  metadata for the web frontend (web/)
"""

import html
import os
import re
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

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


def parse_wheel_tags(filename: str) -> dict:
    """Return python / abi / platform tags of a wheel filename."""
    parts = filename[:-4].split("-")
    return {"python": parts[-3], "abi": parts[-2], "platform": parts[-1]}


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


def version_key(version: str) -> tuple:
    """Approximate PEP 440 ordering without third-party dependencies."""
    key = []
    for part in re.findall(r"\d+|[a-z]+", version.lower()):
        # Numbers sort above pre-release labels (1.0 > 1.0rc1); "post" above both.
        if part.isdigit():
            key.append((2, int(part), ""))
        elif part in ("post", "rev", "r"):
            key.append((3, 0, part))
        else:
            key.append((0, 0, part))
    key.append((1, 0, ""))
    return tuple(key)


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


def collect_packages(releases: list) -> dict:
    """
    Scan releases and collect all package files.

    Returns:
        {normalized_name: {"display_name": str, "versions": {version: info}}}
        info = {"release_tag", "release_url", "published_at", "files": [...]}
    """
    packages = {}
    seen_files = set()

    for release in releases:
        if release.get("draft"):
            continue

        tag = release.get("tag_name", "")
        assets = release.get("assets", [])

        # Process each asset
        for asset in assets:
            filename = asset["name"]

            if filename.endswith(".whl"):
                pkg_name, version = parse_wheel_filename(filename)
                kind = "wheel"
            elif filename.endswith(".tar.gz") or filename.endswith(".zip"):
                pkg_name, version = parse_sdist_filename(filename)
                kind = "sdist"
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

            digest = asset.get("digest") or ""
            file_info = {
                "filename": filename,
                "url": asset["browser_download_url"],
                "kind": kind,
                "size": asset.get("size", 0),
                "sha256": digest[7:] if digest.startswith("sha256:") else None,
                "uploaded_at": asset.get("updated_at") or release.get("published_at"),
                "downloads": asset.get("download_count", 0),
            }
            if kind == "wheel":
                file_info.update(parse_wheel_tags(filename))

            pkg = packages.setdefault(
                norm_name, {"display_name": pkg_name, "versions": {}}
            )
            ver = pkg["versions"].setdefault(
                version,
                {
                    "release_tag": tag,
                    "release_url": release.get("html_url"),
                    "published_at": release.get("published_at"),
                    "files": [],
                },
            )
            ver["files"].append(file_info)

    return packages


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
    for name, pkg in packages.items():
        pkg_dir = simple_dir / name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        files = [fi for v in pkg["versions"].values() for fi in v["files"]]

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
                # PEP 503 hash fragment lets pip verify the download
                if fi["sha256"]:
                    href += f"#sha256={fi['sha256']}"
                safe_fn = html.escape(fi["filename"])
                safe_href = html.escape(href, quote=True)
                f.write(f'  <a href="{safe_href}">{safe_fn}</a><br>\n')
            f.write("</body>\n</html>\n")


def generate_packages_json(
    packages: dict,
    repo: str,
    index_url: str,
    output_dir: Path,
) -> None:
    """Write packages.json consumed by the Astro frontend (web/)."""
    out = []
    for name in sorted(packages):
        pkg = packages[name]
        versions = []
        for version in sorted(pkg["versions"], key=version_key, reverse=True):
            info = pkg["versions"][version]
            versions.append(
                {
                    "version": version,
                    **info,
                    "files": sorted(info["files"], key=lambda x: x["filename"]),
                }
            )
        out.append(
            {
                "name": name,
                "display_name": pkg["display_name"],
                "latest": versions[0]["version"],
                "versions": versions,
            }
        )

    data = {
        "repo": repo,
        "index_url": index_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "packages": out,
    }
    with open(output_dir / "packages.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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

    packages = collect_packages(releases)
    print(f"Indexed {len(packages)} package(s)")

    owner, name = repo.split("/")
    base_url = os.environ.get("PAGES_BASE_URL") or f"https://{owner}.github.io/{name}"
    index_url = base_url.rstrip("/") + "/simple/"

    output_dir.mkdir(parents=True, exist_ok=True)
    generate_simple_index(packages, output_dir)
    generate_packages_json(packages, repo, index_url, output_dir)

    print(f"Index written to {output_dir}/")


if __name__ == "__main__":
    main()
