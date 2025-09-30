# Media Manager

Pipeline d’ingestion & tri des médias (images/vidéos/audio), avec index global par `(event, year)`.

## Dossiers (externalités)
- `/inbox` (arrivées)
- `/to process` (tri en cours)
- `/library` (validé/archivé)

> Ces dossiers NE font PAS partie du repo. Le code vit dans `/media-manager`.

## Scripts (CLI)
1. `python3 app/scripts/rename_with_index.py --event <tag>`
2. `python3 app/scripts/tri_and_move_from_inbox.py`
3. (tri manuel)
4. `python3 app/scripts/validate_and_mirror_to_library.py <event>`

## Index global
- Stocké dans `app/state/increment_index.csv` (ignoré par Git).
- Géré **uniquement** par `rename_with_index.py`.

## GUI (à venir)
- `app/gui/app.py` (Tkinter).


## Project structure
/projet/
├─ app/
│  ├─ scripts/
│  │  ├─ rename_with_index.py
│  │  ├─ tri_and_move_from_inbox.py
│  │  └─ validate_and_mirror_to_library.py
│  ├─ gui/
│  │  ├─ app.py
│  │  ├─ views/
│  │  ├─ services/
│  │  └─ utils/
│  └─ state/
│     └─ increment_index.csv
├─ inbox/
├─ to process/
│  ├─ images/
│  │  ├─ compressed/
│  │  └─ raw/
│  ├─ video/
│  └─ audio/
└─ library/
