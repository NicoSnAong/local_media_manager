#!/usr/bin/env python3
"""
rename_by_date_exiftool_light.py
Solution minimaliste (1 dépendance : ExifTool)

- Renomme tous les fichiers du dossier courant.
- Format : YYYY-MM-DD_hham(fuseau)
  Exemple : 2010-07-11_05am(+7), 2010-07-11_09am(none)
- Pas de secondes, pas de minutes.
- Si fuseau absent → (none)
- Si doublons → ajoute _1, _2, ...

Usage :
  python rename_by_date_exiftool_light.py --dry-run   # simulation
  python rename_by_date_exiftool_light.py --run       # renommer pour de vrai
"""

from pathlib import Path
import sys
import subprocess
from datetime import datetime
from typing import Optional, List
import json
import re

# Champs de date à essayer (ordre de priorité)
DATE_KEYS: List[str] = [
    "DateTimeOriginal",
    "CreateDate",
    "MediaCreateDate",
    "TrackCreateDate",
    "CreationDate",
    "ModifyDate",
    "FileCreateDate",
    "FileModifyDate",
]

INVALID = r'[<>:"/\\|?*]'
def sanitize(name: str) -> str:
    """Nettoie les caractères interdits sous Windows."""
    return re.sub(INVALID, "_", name).rstrip(" .")

def check_exiftool() -> None:
    """Vérifie qu'ExifTool est installé et accessible."""
    try:
        cp = subprocess.run(["exiftool", "-ver"], capture_output=True, text=True, timeout=5)
        if cp.returncode != 0:
            raise RuntimeError(cp.stderr.strip() or "ExifTool indisponible")
    except FileNotFoundError:
        raise SystemExit("ExifTool n'est pas trouvé dans le PATH. Installe-le puis réessaie.")
    except Exception as e:
        raise SystemExit(f"Impossible de lancer ExifTool : {e}")

def exiftool_json(path: Path) -> Optional[dict]:
    """Retourne les métadonnées ExifTool en JSON (ou None)."""
    try:
        cp = subprocess.run(
            ["exiftool", "-j", "-n", str(path)],
            capture_output=True, text=True, timeout=20
        )
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        data = json.loads(cp.stdout)
        return data[0] if isinstance(data, list) and data else None
    except Exception:
        return None

def parse_date_and_tz(s: str) -> tuple[Optional[datetime], str]:
    """
    Tente de parser une date et retourne aussi le fuseau formaté.
    """
    s = s.strip()
    tz_str = "(none)"

    # Cas ISO avec Z (UTC)
    if s.endswith("Z"):
        tz_str = "(+0)"
        try:
            dt = datetime.strptime(s[:-1], "%Y-%m-%dT%H:%M:%S")
            return dt, tz_str
        except Exception:
            pass

    # Cas avec offset explicite (+HH:MM ou -HH:MM)
    if "+" in s or "-" in s[-6:]:
        parts = s.split()
        if len(parts) >= 2:
            base = parts[0] + " " + parts[1][:8]  # date + HH:MM:SS
            tz_raw = parts[1][8:]

            # Normalisation fuseau
            if tz_raw:
                if tz_raw.endswith(":00"):  # ex: +07:00
                    tz_str = f"({tz_raw[:-3]})"
                else:  # ex: +05:30 → (+5h30)
                    sign = tz_raw[0]
                    h, m = tz_raw[1:].split(":")
                    tz_str = f"({sign}{int(h)}h{m})"

            try:
                dt = datetime.strptime(base, "%Y:%m:%d %H:%M:%S")
                return dt, tz_str
            except Exception:
                pass

    # Cas simple sans tz
    for f in ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(s, f)
            return dt, tz_str
        except Exception:
            continue

    return None, tz_str

def choose_datetime(meta: Optional[dict]) -> tuple[Optional[datetime], str]:
    """Choisit la meilleure date et retourne aussi le fuseau détecté."""
    if not meta:
        return None, "(none)"
    for key in DATE_KEYS:
        val = meta.get(key)
        if not val:
            continue
        dt, tz = parse_date_and_tz(str(val))
        if dt:
            return dt, tz
    return None, "(none)"

def filesystem_date(path: Path) -> datetime:
    """Fallback : date de modification du fichier (mtime)."""
    return datetime.fromtimestamp(path.stat().st_mtime)

def name_fmt(dt: datetime, tz: str) -> str:
    """Format final : YYYY-MM-DD_hham(fuseau)"""
    s = dt.strftime("%Y-%m-%d_%I%p")  # ex. 2010-07-11_05AM
    s = s[:-2] + s[-2:].lower()       # am/pm en minuscules
    return f"{s}{tz}"

def unique_target(target: Path) -> Path:
    """Ajoute _1, _2... en cas de doublon."""
    if not target.exists():
        return target
    base, ext = target.stem, target.suffix
    i = 1
    while True:
        cand = target.with_name(f"{base}_{i}{ext}")
        if not cand.exists():
            return cand
        i += 1

def main(dry_run: bool):
    check_exiftool()
    cwd = Path.cwd()
    # __file__ peut être absent (exécution interactive VS Code) → repli sur sys.argv[0]
    me = Path(globals().get("__file__", sys.argv[0] if sys.argv else "")).name

    print(f"📂 Dossier: {cwd}")
    print("💡 Mode:", "DRY-RUN (simulation)" if dry_run else "RENOMMAGE RÉEL")
    print("————————————————————————————————————————")

    files = [p for p in sorted(cwd.iterdir()) if p.is_file() and p.name not in {me, "exiftool.exe"}]

    for p in files:
        meta = exiftool_json(p)
        dt, tz = choose_datetime(meta)

        if not dt:
            dt = filesystem_date(p)
            tz = "(none)"
            print(f"↩️  {p.name}: pas de date capture → fallback fichier ({dt})")

        newbase = name_fmt(dt, tz)
        newname = sanitize(f"{newbase}{p.suffix.lower()}")
        target = unique_target(p.with_name(newname))

        if dry_run:
            print(f"[DRY] {p.name}  →  {target.name}")
        else:
            try:
                print(f"[DO ] {p.name}  →  {target.name}")
                p.rename(target)
            except Exception as e:
                print(f"   ⚠️  Échec: {e}")

if __name__ == "__main__":
    dry = True
    if len(sys.argv) > 1 and sys.argv[1] in ("--run", "--do"):
        dry = False
    main(dry_run=dry)


# ——————————————————————————————————————————————————————————————
# 📜 RÈGLES DE GESTION DES DATES ET FUSEAUX
#
# - (Z) → (+0)
# - +HH:00 / -HH:00 → (+H) / (-H)
# - +HH:MM (minutes ≠ 00) → (+HhMM) / (-HhMM)  (pas de ":")
# - Pas de fuseau → (none)
#
# Exemples :
#   "2010:07:11 05:52:00+07:00"  →  2010-07-11_05am(+7)
#   "2010:07:11 05:52:00+05:30"  →  2010-07-11_05am(+5h30)
#   "2010:07:11 05:52:00Z"       →  2010-07-11_05am(+0)
#   "2010:07:11 05:52:00"        →  2010-07-11_05am(none)
# ——————————————————————————————————————————————————————————————
