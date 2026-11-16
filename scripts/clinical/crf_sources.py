"""Discover official CDISC documents and preserve actual PDF annotation evidence."""
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
import pymupdf
from fetch_data import DATA

TREE_URL = "https://api.github.com/repos/cdisc-org/sdtm-adam-pilot-project/git/trees/master?recursive=1"

def official_crf():
    with urllib.request.urlopen(TREE_URL, timeout=90) as response:
        tree = json.load(response)
    if tree.get("truncated"):
        raise RuntimeError("CDISC repository tree is truncated; cannot establish document availability.")
    (DATA/"cdisc-repository-tree.json").write_text(json.dumps(tree, indent=2))
    sources, paths = [], {}
    for name in ["blankcrf.pdf", "csdrg.pdf", "adrg.pdf", "dataguide.pdf"]:
        matches = [r["path"] for r in tree["tree"] if r["type"] == "blob" and r["path"].split("/")[-1].lower() == name]
        if not matches:
            sources.append(dict(name="CDISC "+name, url=TREE_URL, status="Absent from official repository tree", sha256="",
                                note=f"No exact filename in the complete recursive tree at commit {tree['sha']}. No substitute renamed."))
        for remote in matches:
            url = f"https://raw.githubusercontent.com/cdisc-org/sdtm-adam-pilot-project/{tree['sha']}/{remote}"
            # Content-addressed cache prevents a newer source tree using stale PDF bytes.
            local = DATA/f"cdisc-{tree['sha']}-{name}"
            if not local.exists():
                with urllib.request.urlopen(url, timeout=90) as response:
                    payload = response.read()
                if not payload.startswith(b"%PDF"):
                    raise ValueError("Unexpected document format: "+url)
                local.write_bytes(payload)
            sources.append(dict(name="CDISC "+name, url=url, status="Cached from official repository",
                                sha256=hashlib.sha256(local.read_bytes()).hexdigest(),
                                note=f"Discovered path: {remote}. "+
                                ("Historical ADaM data guide; not a file named adrg.pdf." if name=="dataguide.pdf" else "Original filename preserved.")))
            paths[name] = (local, url)
    if "blankcrf.pdf" not in paths:
        raise RuntimeError("Official annotated CRF was not found.")
    path, url = paths["blankcrf.pdf"]
    rows, domains = [], defaultdict(lambda: {"pages":set(), "variables":set(), "count":0})
    with pymupdf.open(path) as doc:
        page_count = len(doc)
        for page_number, page in enumerate(doc, 1):
            for annotation in page.annots() or []:
                info = annotation.info
                subject = info.get("subject", "")
                content = info.get("content", "").replace("\r", "\n").strip()
                # Subjects are authored domain assignments, not guesses from printed form headings.
                names = [n.strip() for n in subject.split(",") if n.strip() and n.strip()!="NEID"]
                variables = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", content)))
                rows.append(dict(page=page_number, subject=subject, domains=", ".join(names),
                                 annotation=content, source=f"{url}#page={page_number}"))
                for name in names:
                    entry=domains[name]
                    entry["pages"].add(page_number)
                    entry["variables"].update(v for v in variables if v.startswith(name) and v!=name)
                    entry["count"]+=1
    mapping=[dict(domain=name,pages=sorted(d["pages"]),variables=sorted(d["variables"]),count=d["count"])
             for name,d in sorted(domains.items())]
    result=dict(pageCount=page_count, annotationCount=len(rows), domains=mapping, annotations=rows,
                source=url, repositoryCommit=tree["sha"],
                note="One-based physical PDF pages, not printed visit-page labels. Multi-domain annotations appear in each authored subject. NEID means Not Entered In Database and is preserved separately; annotation presence does not prove a field exists in XPT.")
    (DATA.parent/"CRF_Page_Domain_Annotations.json").write_text(json.dumps(result,indent=2))
    return sources,result
