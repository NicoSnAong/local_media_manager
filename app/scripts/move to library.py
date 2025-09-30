#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from pathlib import Path
import sys, shutil

TO_PROCESS_COMP = Path("/to process/images/compressé")
LIBRARY_DIR = Path("/library")

def unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem, suf = base.stem, base.suffix
    i = 1
    while True:
        cand = base.with_name(f"{stem}_dup{i}{suf}")
        if not cand.exists():
            return cand
        i += 1

def mirror_event(event: str):
    src = TO_PROCESS_COMP / event
    if not src.exists():
        print(f"[INFO] Rien à mirrorer, introuvable: {src}")
        return
    dst = LIBRARY_DIR / event
    dst.mkdir(parents=True, exist_ok=True)

    moved = 0
    for p in sorted(src.iterdir()):
        if not p.is_file():
            continue
        target = unique_path(dst / p.name)
        try:
            shutil.move(str(p), str(target))
            print(f"[OK] {p.name} → {target}")
            moved += 1
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
    print(f"✔ Event '{event}': {moved} fichier(s) déplacé(s) vers /library.")

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_and_mirror_to_library.py <event>", file=sys.stderr)
        sys.exit(2)
    mirror_event(sys.argv[1])

if __name__ == "__main__":
    main()
