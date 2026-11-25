"""Verify the frozen CDISCPILOT01 source files against SHA256SUMS.txt.
Usage: python verify_frozen_sources.py   (run from the extracted archive folder)"""
import hashlib, sys
from pathlib import Path
here = Path(__file__).resolve().parent
bad = 0
lines = [l for l in (here / "SHA256SUMS.txt").read_text().splitlines() if l.strip()]
for line in lines:
    digest, rel = line.split("  ", 1)
    path = here / "files" / rel
    if not path.is_file():
        print("MISSING ", rel); bad += 1; continue
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        print("CHANGED ", rel); bad += 1
print(f"{len(lines) - bad}/{len(lines)} files verified")
sys.exit(1 if bad else 0)
