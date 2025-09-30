#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from pathlib import Path
import re, shutil, sys

INBOX_DIR = Path("/inbox")
TO_PROCESS_DIR = Path("/to process")

# extensions
RAW_EXT = {"cr2","cr3","nef","arw","dng","raf","orf","rw2","srw","pef"}
IMG_COMP_EXT = {"jpg","jpeg","png","gif","webp","heic","tif","tiff","bmp"}
VIDEO_EXT = {"mp4","mov","m4v","avi","mkv","webm","wmv"}
AUDIO_EXT = {"mp3","wav","aac","flac","m4a","ogg","wma","aiff"}

# YYYY-MM-DD_<event>_<inc>(...)?  (on ignore l'extension)
STEM_RX = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<event>[^_]+)_(?P<inc>\d+)(?:_.+)?$")

def parse_event(stem: str) -> str | None:
    m = STEM_RX.match(stem)
    return m.group("event") if m else None

def classify(ext: str) -> tuple[str, str|None]:
    e = ext.lower().lstrip(".")
    if e in IMG_COMP_EXT:
        return ("images", "compressé")
    if e in RAW_EXT:
        return ("images", "brute")
    if e in VIDEO_EXT:
        return ("video", None)
    if e in AUDIO_EXT:
        return ("audio", None)
    return ("other", None)

def target_dir(media: str, img_kind: str|None, event: str) -> Path:
    if media == "images":
        return TO_PROCESS_DIR / "images" / img_kind / event  # img_kind: compressé|brute
    if media == "video":
        return TO_PROCESS_DIR / "video" / event
    if media == "audio":
        return TO_PROCESS_DIR / "audio" / event
    return TO_PROCESS_DIR / "_unsorted" / event

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

def main():
    if not INBOX_DIR.exists():
        print(f"[ERR] Inbox introuvable: {INBOX_DIR}", file=sys.stderr)
        sys.exit(2)

    moved, skipped = 0, 0
    for p in sorted(INBOX_DIR.iterdir()):
        if not p.is_file():
            continue

        ev = parse_event(p.stem)
        if not ev:
            skipped += 1
            continue

        media, img_kind = classify(p.suffix)
        if media == "other":
            skipped += 1
            continue

        dest_dir = target_dir(media, img_kind, ev)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / p.name
        dest = unique_path(dest)

        try:
            shutil.move(str(p), str(dest))
            print(f"[OK] {p.name} → {dest}")
            moved += 1
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")

    print(f"\n✅ Terminé. Déplacés: {moved} | Ignorés: {skipped}")

if __name__ == "__main__":
    main()
