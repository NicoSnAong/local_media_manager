#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
rename_with_index.py
--------------------
Renomme TOUT le contenu de /inbox vers la convention:
    YYYY-MM-DD_<event>_<increment>.<ext>

- L'incrément est GLOBAL par (event, year), partagé pour tous médias.
- Le compteur est stocké dans un CSV :
    /projet/app/state/increment_index.csv
  format: event,year,last_inc,updated_at

- Ce script gère SEUL la lecture/mise à jour de l’index.
  Les autres scripts (tri/deplacement) n'ont rien à faire avec l'index.

- Auto-guérison :
  Si l'entrée (event,year) est absente du CSV, on scanne /to process/**/<event>/ et /library/<event>/
  pour retrouver le max déjà utilisé, sinon on démarre à 1.

Chemins FIXES (pas d'arguments de chemin) :
  INBOX_DIR  = "/inbox"
  STATE_CSV  = "/projet/app/state/increment_index.csv"
  TO_PROC    = "/to process"
  LIBRARY    = "/library"

Arguments pris en charge :
  --event <slug>   (obligatoire)
  --dry-run        (optionnel)
"""

from __future__ import annotations
from pathlib import Path
import sys, subprocess, json, re, csv, os
from datetime import datetime
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[3]

INBOX_DIR      = ROOT_DIR / "inbox"
TO_PROCESS_DIR = ROOT_DIR / "to process"
LIBRARY_DIR    = ROOT_DIR / "library"
STATE_DIR      = ROOT_DIR / "app" / "state"
STATE_CSV      = STATE_DIR / "increment_index.csv"


# === Constantes / outils ===
DATE_KEYS = [
    "DateTimeOriginal", "CreateDate", "MediaCreateDate", "TrackCreateDate",
    "CreationDate", "ModifyDate", "FileCreateDate", "FileModifyDate",
]

INVALID = r'[<>:"/\\|?*]'
def clean(s: str) -> str:
    # Nettoie pour un nom de fichier sûr
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
                            capture_output=True, text=True, timeout=20)
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        data = json.loads(cp.stdout)
        return data[0] if isinstance(data, list) and data else None
    except Exception:
        return None

def extract_capture_date(path: Path) -> str:
    """Renvoie YYYY-MM-DD (Exif si possible, sinon mtime du fichier)."""
    meta = exiftool_json(path)
    raw = None
    if meta:
        for k in DATE_KEYS:
            v = meta.get(k)
            if v:
                raw = str(v).strip()
                break
    if raw:
        raw = re.sub(r'\.\d+$', '', raw)  # drop .sss si présent
        for f in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                  "%Y:%m:%d", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(raw, f)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    return dt.strftime("%Y-%m-%d")

# Noms attendus (si on scanne l'existant): YYYY-MM-DD_<event>_<inc>(...)? .ext
STEM_RX = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<event>[^_]+)_(?P<inc>\d+)(?:_.+)?$")

def parse_stem(stem: str):
    m = STEM_RX.match(stem)
    if not m:
        return None
    try:
        return {
            "date": m.group("date"),
            "event": m.group("event"),
            "inc": int(m.group("inc")),
        }
    except Exception:
        return None

# === CSV index ===
def read_index(path: Path) -> dict[tuple[str,str], int]:
    idx = {}
    if not path.exists():
        return idx
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            event, year, last_inc = row[0], row[1], row[2]
            try:
                idx[(event, year)] = int(last_inc)
            except Exception:
                continue
    return idx

def write_index_atomic(path: Path, idx: dict[tuple[str,str], int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    now = datetime.now().isoformat(timespec="seconds")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for (event, year), last_inc in sorted(idx.items()):
            w.writerow([event, year, last_inc, now])
    os.replace(tmp, path)

# === Auto-guérison de l'entrée (event,year) si absente du CSV ===
def scan_max_existing(event: str, year: str) -> int:
    """
    Cherche le max inc existant pour (event,year) dans:
      /to process/images/compressé/<event>/
      /to process/images/brute/<event>/
      /to process/video/<event>/
      /to process/audio/<event>/
      /library/<event>/
    """
    candidates = [
        TO_PROCESS_DIR / "images" / "compressé" / event,
        TO_PROCESS_DIR / "images" / "brute" / event,
        TO_PROCESS_DIR / "video" / event,
        TO_PROCESS_DIR / "audio" / event,
        LIBRARY_DIR / event,
    ]
    max_inc = 0
    for d in candidates:
        if not d.exists():
            continue
        for p in d.iterdir():
            if not p.is_file():
                continue
            info = parse_stem(p.stem)
            if not info:
                continue
            if info["event"] != event:
                continue
            if info["date"][:4] != year:
                continue
            if info["inc"] > max_inc:
                max_inc = info["inc"]
    return max_inc

def next_free_name(dir_: Path, date_str: str, event: str, start_inc: int, ext: str) -> tuple[int, Path]:
    """
    Assure qu'on ne va pas écraser un fichier déjà présent dans /inbox.
    (Peu probable si l'index est cohérent, mais on reste safe.)
    """
    i = max(1, start_inc)
    while True:
        candidate = dir_ / f"{date_str}_{event}_{i}{ext}"
        if not candidate.exists():
            return i, candidate
        i += 1

def main():
    event_in = argval("--event")
    if not event_in:
        print("❌ Argument requis: --event <slug> (ex: --event bali-trip)")
        sys.exit(2)
    dry = hasflag("--dry-run")

    event_slug = clean(event_in.replace(" ", "-").lower())

    if not INBOX_DIR.exists():
        print(f"❌ Inbox introuvable: {INBOX_DIR}", file=sys.stderr)
        sys.exit(2)

    # Collecte des fichiers à renommer (on ignore ce script lui-même si présent en /inbox)
    files = [p for p in sorted(INBOX_DIR.iterdir()) if p.is_file() and p.name != Path(__file__).name]
    if not files:
        print("ℹ️  Rien à renommer dans /inbox.")
        return

    # Extraction des dates pour déterminer les années et préparer un ordre stable
    items = []
    for p in files:
        date_str = extract_capture_date(p)
        year = date_str[:4]
        items.append((p, date_str, year))

    # On traite par groupe d'année (l’index est par (event,year))
    from collections import defaultdict
    groups = defaultdict(list)
    for p, date_str, year in items:
        groups[year].append((p, date_str))

    # Lecture/MAJ index
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    idx = read_index(STATE_CSV)

    print(f"📂 Source   : {INBOX_DIR}")
    print(f"🏷️  Événement : {event_slug}")
    print("🔎 Mode     :", "DRY-RUN (simulation)" if dry else "RENOMMAGE")
    planned = 0
    renamed = 0

    # Pour chaque année concernée par le batch
    for year, lst in sorted(groups.items()):
        # Point de départ: CSV ou auto-guérison si manquant
        last_inc = idx.get((event_slug, year))
        if last_inc is None:
            last_inc = scan_max_existing(event_slug, year)
        next_inc = last_inc + 1

        # Ordre stable: par (date, nom d'origine)
        lst.sort(key=lambda x: (x[1], x[0].name))

        for p, date_str in lst:
            ext = p.suffix.lower()
            # On garantit qu'on n'écrase rien déjà présent dans /inbox
            inc, target_path = next_free_name(INBOX_DIR, date_str, event_slug, next_inc, ext)
            next_inc = inc + 1

            planned += 1
            if dry:
                print(f"[DRY] {p.name}  →  {target_path.name}")
            else:
                try:
                    p.rename(target_path)
                    print(f"[OK ] {p.name}  →  {target_path.name}")
                    renamed += 1
                except Exception as e:
                    print(f"[ERR] {p.name}  →  {e}")

        # Mise à jour de l’index pour (event,year)
        idx[(event_slug, year)] = next_inc - 1

    # Écriture atomique de l'index (une seule fois en fin de run)
    if not dry:
        write_index_atomic(STATE_CSV, idx)

    print(f"\n✅ Terminé. Prévu: {planned} | Renommés: {renamed} | Mode: {'DRY-RUN' if dry else 'LIVE'}")
    print(f"🗂  Index CSV: {STATE_CSV}")

if __name__ == "__main__":
    main()
