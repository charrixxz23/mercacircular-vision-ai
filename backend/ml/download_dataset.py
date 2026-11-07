"""Descarga SOLO las carpetas de Fruits-360 que usa el modelo (≈ 400 MB).

Uso (desde la carpeta backend, con el entorno virtual activo):

    python -m ml.download_dataset

Requiere Git. Usa un clon parcial (sparse checkout) del repositorio oficial:
https://github.com/fruits-360/fruits-360-100x100 — licencia CC BY-SA 4.0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE / "data" / "fruits-360"
REPO = "https://github.com/fruits-360/fruits-360-100x100"


def folders() -> list[str]:
    splits = json.loads((HERE / "splits.json").read_text(encoding="utf-8"))
    out: list[str] = []
    for groups in splits["clases"].values():
        out += groups["train"] + groups["test"]
    return out


def run(*args: str, cwd: Path | None = None) -> None:
    print("$", " ".join(args))
    subprocess.run(args, cwd=cwd, check=True)


def main() -> int:
    if shutil.which("git") is None:
        print("Se necesita Git: https://git-scm.com/download/win", file=sys.stderr)
        return 1
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if not (DEST / ".git").exists():
        run("git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", REPO, str(DEST))
    run("git", "sparse-checkout", "init", "--no-cone", cwd=DEST)
    patterns = [f"/{split}/{name}/" for name in folders() for split in ("Training", "Test")]
    (DEST / ".git" / "info" / "sparse-checkout").write_text("\n".join(patterns) + "\n", encoding="utf-8")
    run("git", "checkout", "main", cwd=DEST)
    missing = [n for n in folders() if not (DEST / "Training" / n).is_dir()]
    if missing:
        print("Faltan carpetas:", missing, file=sys.stderr)
        return 1
    print(f"Listo: {len(folders())} carpetas en {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
