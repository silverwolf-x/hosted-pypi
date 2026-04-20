from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS_FILE = REPO_ROOT / ".github" / "talib-requirements.txt"
TALIB_RELEASE_API = "https://api.github.com/repos/TA-Lib/ta-lib/releases/latest"
PYTHON_EOL_API = "https://endoflife.date/api/python.json"


def read_talib_python_version() -> str:
    pattern = re.compile(r"^ta-lib==(?P<version>\S+)$", re.IGNORECASE)
    for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = pattern.match(stripped)
        if match:
            return match.group("version")
    raise RuntimeError(f"Unable to read ta-lib version from {REQUIREMENTS_FILE}")


def fetch_json(url: str, *, token: str | None = None) -> object:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request) as response:  # noqa: S310
        return json.load(response)


def read_talib_c_version(token: str | None) -> str:
    payload = fetch_json(TALIB_RELEASE_API, token=token)
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected TA-Lib release response payload")
    tag_name = str(payload.get("tag_name", "")).strip()
    if not tag_name:
        raise RuntimeError("Latest TA-Lib release payload is missing tag_name")
    return tag_name.lstrip("v")


def compute_cibw_build() -> str:
    payload = fetch_json(PYTHON_EOL_API)
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected endoflife.date response payload")

    today = date.today().isoformat()
    supported: list[tuple[int, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        cycle = str(item.get("cycle", ""))
        eol = item.get("eol", "")
        latest = str(item.get("latest", ""))
        if not cycle.startswith("3."):
            continue
        if (isinstance(eol, bool) and eol) or (isinstance(eol, str) and eol <= today):
            continue
        if re.search(r"[a-zA-Z]", latest):
            continue
        try:
            supported.append((int(cycle.split(".", 1)[1]), cycle))
        except (IndexError, ValueError):
            continue

    supported.sort(key=lambda item: item[0], reverse=True)
    top_three = sorted(
        (cycle for _, cycle in supported[:3]),
        key=lambda cycle: int(cycle.split(".", 1)[1]),
    )
    if len(top_three) != 3:
        raise RuntimeError(f"Expected 3 supported Python cycles, got {top_three!r}")
    return " ".join(f"cp{cycle.replace('.', '')}-*" for cycle in top_three)


def write_outputs(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    try:
        token = os.environ.get("GH_TOKEN")
        values = {
            "talib_py_ver": read_talib_python_version(),
            "talib_c_ver": read_talib_c_version(token),
            "cibw_build": compute_cibw_build(),
        }
    except (HTTPError, URLError, OSError, RuntimeError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    for key, value in values.items():
        print(f"{key}={value}")
    write_outputs(values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())