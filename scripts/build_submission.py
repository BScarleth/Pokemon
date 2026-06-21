"""
Build submission.tar.gz for the Kaggle arena.

The archive bundles, at its root:
    main.py   (= submission.py — the entry point defining `agent`)
    cg/       (engine helper package, from src/cg — includes libcg.so)
    ptcg/     (our agent package, from src/ptcg)

This mirrors the official sample notebook's submission format. No code is
inlined or rewritten — the real modules are shipped as-is.

Usage:
    python scripts/build_submission.py
    kaggle competitions submit pokemon-tcg-ai-battle -f submission.tar.gz -m "..."
"""

import os
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "submission.tar.gz")


def _exclude_pycache(info: tarfile.TarInfo):
    """Skip __pycache__ dirs and compiled files."""
    if "__pycache__" in info.name or info.name.endswith(".pyc"):
        return None
    return info


def main() -> None:
    with tarfile.open(OUTPUT, "w:gz") as tar:
        tar.add(os.path.join(ROOT, "submission.py"), arcname="main.py")
        tar.add(os.path.join(ROOT, "src", "cg"),   arcname="cg",   filter=_exclude_pycache)
        tar.add(os.path.join(ROOT, "src", "ptcg"), arcname="ptcg", filter=_exclude_pycache)

    print(f"Built {OUTPUT}")
    print('Submit: kaggle competitions submit pokemon-tcg-ai-battle -f submission.tar.gz -m "..."')


if __name__ == "__main__":
    main()
