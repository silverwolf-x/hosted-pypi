from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
DOWNLOAD_DIR = REPO_ROOT / "talib-dist"
SOURCE_DIR = REPO_ROOT / "talib-py"
PYPI_RELEASE_API = "https://pypi.org/pypi/ta-lib/{version}/json"


def reset_path(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def download_source_distribution(version: str) -> Path:
    reset_path(DOWNLOAD_DIR)
    with urlopen(PYPI_RELEASE_API.format(version=version)) as response:  # noqa: S310
        payload = json.load(response)

    urls = payload.get("urls", []) if isinstance(payload, dict) else []
    if not isinstance(urls, list):
        raise RuntimeError("Unexpected PyPI release payload")

    source_url = ""
    filename = ""
    for item in urls:
        if not isinstance(item, dict):
            continue
        if item.get("packagetype") != "sdist":
            continue
        source_url = str(item.get("url", "")).strip()
        filename = str(item.get("filename", "")).strip()
        if source_url and filename:
            break

    if not source_url or not filename:
        raise RuntimeError(f"Unable to locate TA-Lib sdist for {version}")

    archive_path = DOWNLOAD_DIR / filename
    with urlopen(source_url) as response, open(archive_path, "wb") as handle:  # noqa: S310
        shutil.copyfileobj(response, handle)
    return archive_path


def extract_source_archive(archive_path: Path) -> None:
    reset_path(SOURCE_DIR)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(temp_path)

        children = list(temp_path.iterdir())
        source_root = children[0] if len(children) == 1 and children[0].is_dir() else temp_path
        for item in source_root.iterdir():
            destination = SOURCE_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)


def main() -> int:
    version = os.environ.get("TALIB_PY_VER", "").strip()
    if not version:
        print("TALIB_PY_VER is required", file=sys.stderr)
        return 1

    try:
        archive_path = download_source_distribution(version)
        extract_source_archive(archive_path)
    except (HTTPError, URLError, OSError, RuntimeError, tarfile.TarError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Prepared TA-Lib Python source {version} in {SOURCE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())