"""Fetch the public PHUSE pilot data; retain byte hashes for provenance."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "generated-artifacts" / "clinical" / "data"
SDTM = "dm ds ex ae qs lb vs mh cm sc".split()
ADAM = "adsl adqsadas adqscibc adqsnpix adae adtte adlbc adlbh advs".split()

def fetch(pair):
    standard, name = pair
    dest = DATA / f"{name}.xpt"
    url = f"https://raw.githubusercontent.com/phuse-org/phuse-scripts/master/data/{standard}/cdiscpilot01/{name}.xpt"
    if not dest.exists():
        with urllib.request.urlopen(url, timeout=90) as response:
            content = response.read()
        if not content.startswith(b"HEADER RECORD"):
            raise ValueError(f"Invalid XPT response: {url}")
        dest.write_bytes(content)
    return name, url

def fetch_all():
    DATA.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(pool.map(fetch, [("sdtm", n) for n in SDTM] + [("adam", n) for n in ADAM]))

if __name__ == "__main__":
    print(fetch_all())
