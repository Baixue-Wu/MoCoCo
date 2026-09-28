"""Download a demo film that is legal to show in public.

Usage:  uv run python scripts/fetch_film.py sintel [--dest data/films]
        uv run python scripts/fetch_film.py charade
        uv run python scripts/fetch_film.py street-angel
        uv run python scripts/fetch_film.py --list
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import httpx

FILMS = {
    "sintel": {
        "url": "https://download.blender.org/durian/movies/Sintel.2010.720p.mkv.zip",
        "file": "Sintel.2010.720p.mkv",
        "zip": True,
        "license": "CC-BY 3.0, Blender Foundation (2010), 15 min",
    },
    "street-angel": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Street_Angel_%281937%29.webm",
        "file": "StreetAngel.1937.webm",
        "zip": False,
        "license": "马路天使, PD-China and PD-US per Wikimedia Commons (1937), 91 min, Mandarin",
    },
    "charade": {
        "url": "https://archive.org/download/charade-1963-cary-grant-audrey-hepburn-comedy-mystery-romance-thriller-full-movie/Charade_READY.mp4",
        "file": "Charade.1963.mp4",
        "zip": False,
        "license": "US public domain (1963, defective copyright notice), 113 min",
    },
}


def fetch(name: str, dest: Path) -> Path:
    info = FILMS[name]
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / info["file"]
    if target.exists():
        print(f"already have {target}")
        return target
    tmp = dest / (info["file"] + (".zip" if info["zip"] else ".part"))
    print(f"downloading {info['url']}")
    headers = {"User-Agent": "MoCoCo/0.1 (research prototype; https://github.com/Baixue-Wu/MoCoCo)"}
    with httpx.stream("GET", info["url"], headers=headers, follow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r{done / 1e6:.0f}/{total / 1e6:.0f} MB", end="", flush=True)
    print()
    if info["zip"]:
        with zipfile.ZipFile(tmp) as z:
            z.extractall(dest)
        tmp.unlink()
    else:
        tmp.rename(target)
    if not target.exists():
        raise RuntimeError(f"download finished but {target} is missing")
    return target


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?", choices=sorted(FILMS))
    ap.add_argument("--dest", type=Path, default=Path("data/films"))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list or not a.name:
        for k, v in FILMS.items():
            print(f"{k:10s} {v['file']:24s} {v['license']}")
        return 0
    print(fetch(a.name, a.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
