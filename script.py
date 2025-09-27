# On importe un module standard de Python : pathlib
# pathlib sert à manipuler les fichiers et dossiers de manière simple et portable.
from pathlib import Path


# Path.cwd() renvoie le dossier actuel (là où le script est lancé)
dossier = Path.cwd()


# On définit un chemin vers un fichier hello.txt dans ce dossier helo
fichier =dossier/"demo.txt"


# On écrit du texte dans ce fichier
fichier.write_text("hello les amis\n", encoding="utf-8")