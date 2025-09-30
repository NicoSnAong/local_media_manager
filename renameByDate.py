#!/usr/bin/env python3
"""
rename_by_capture_date.py
Renomme les fichiers du dossier courant en :
YYYY-MM-DD_<event>_<increment>.ext

- Date = date de capture (ExifTool). Fallback = date du fichier.
- Event = obligatoire (--event).
- Increment = compteur séquentiel, repart à 1 à chaque exécution.

Usage :
  python rename_by_capture_date.py --event bali-trip [--dry-run]
"""

from pathlib import Path
import sys, subprocess, json, re
from datetime import datetime
from typing import Optional

# Liste des tags ExifTool qui contiennent une date de capture potentielle
DATE_KEYS = [
    "DateTimeOriginal", "CreateDate", "MediaCreateDate", "TrackCreateDate",
    "CreationDate", "ModifyDate", "FileCreateDate", "FileModifyDate",
]

INVALID = r'[<>:"/\\|?*]'
def clean(s: str) -> str:
    return re.sub(INVALID, "_", s).strip().strip(" ._")

def argval(flag: str) -> Optional[str]:
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i+1 < len(sys.argv):
            return sys.argv[i+1]
    return None

def hasflag(flag: str) -> bool:
    return flag in sys.argv

def exiftool_json(path: Path) -> Optional[dict]:
    try:
        cp = subprocess.run(["exiftool", "-j", "-n", str(path)],
                            capture_output=True, text=True, timeout=15)
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        data = json.loads(cp.stdout)
        return data[0] if isinstance(data, list) and data else None
    except Exception:
        return None

def extract_capture_date(path: Path) -> str:
    meta = exiftool_json(path)
    raw = None
    if meta:
        for k in DATE_KEYS:
            v = meta.get(k)
            if v:
                raw = str(v).strip()
                break
    if raw:
        raw = re.sub(r'\.\d+$', '', raw)
        for f in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                  "%Y:%m:%d", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(raw, f)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
    # fallback = date de modification fichier
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    return dt.strftime("%Y-%m-%d")

def main():
    event = argval("--event")
    if not event:
        print("❌ Argument requis: --event <slug> (ex: --event bali-trip)")
        sys.exit(1)
    dry = hasflag("--dry-run")

    event_slug = clean(event.replace(" ", "-").lower())
    cwd = Path.cwd()
    files = [p for p in sorted(cwd.iterdir()) if p.is_file() and p.name != Path(__file__).name]

    print(f"📂 Dossier : {cwd}")
    print(f"🏷️  Événement : {event_slug}")
    print("🔎 Mode :", "DRY-RUN (simulation)" if dry else "RENOMMAGE")

    idx = 1
    for p in files:
        date_str = extract_capture_date(p)
        base = f"{date_str}_{event_slug}_{idx}"
        newname = clean(base) + p.suffix.lower()
        target = cwd / newname

        j = 1
        while target.exists():
            target = cwd / (clean(base) + f"_{j}" + p.suffix.lower())
            j += 1

        if dry:
            print(f"[DRY] {p.name}  →  {target.name}")
        else:
            try:
                p.rename(target)
                print(f"[OK ] {p.name}  →  {target.name}")
            except Exception as e:
                print(f"[ERR] {p.name}  →  {e}")

        idx += 1

if __name__ == "__main__":
    main()


