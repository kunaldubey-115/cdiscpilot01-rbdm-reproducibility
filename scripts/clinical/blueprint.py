"""Stage 1 provenance and blueprint-to-rule traceability."""
import hashlib
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from fetch_data import DATA, fetch
from crf_sources import official_crf

BASE="https://raw.githubusercontent.com/phuse-org/phuse-scripts/master/data/"
DOCS=[
    ("SDTM define.xml","sdtm/cdiscpilot01/define.xml","sdtm-define.xml"),
    ("ADaM define.xml","adam/cdiscpilot01/define.xml","adam-define.xml"),
]

def get_doc(spec):
    name,remote,local=spec
    path=DATA/local
    url=BASE+remote
    try:
        if not path.exists():
            with urllib.request.urlopen(url,timeout=90) as r:
                payload=r.read()
            if local.endswith(".pdf") and not payload.startswith(b"%PDF"):
                raise ValueError("Unexpected PDF response for "+name)
            path.write_bytes(payload)
        return dict(name=name,url=url,status="Cached",sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    note="Actual source filename retained. Availability is not evidence that all specifications were independently validated.")
    except urllib.error.HTTPError as e:
        if e.code!=404:
            raise
        return dict(name=name,url=url,status="Unavailable at requested path",sha256="",
                    note="HTTP 404; not silently replaced or renamed. Available historical documents are listed separately.")

def build_blueprint(data, workbook, rules, gate2):
    _,tsurl=fetch(("sdtm","ts"))
    # Legacy trial-summary prose contains Windows-1252 smart punctuation (0x92).
    ts=pd.read_sas(DATA/"ts.xpt",format="xport",encoding="cp1252")
    with ThreadPoolExecutor(max_workers=5) as pool:
        sources=list(pool.map(get_doc,DOCS))
    official_sources, crf = official_crf()
    sources.extend(official_sources)
    sources.insert(0,dict(name="ts.xpt",url=tsurl,status="Cached",sha256=hashlib.sha256((DATA/"ts.xpt").read_bytes()).hexdigest(),
                          note=f"{len(ts)} trial-summary records, {len(ts.columns)} variables; legacy text decoded as Windows-1252. Trial-level domain; no subject denominator."))
    csr="https://raw.githubusercontent.com/phuse-org/phuse-scripts/master/data/adam/TDF_ADaM_v1.0/cdiscpilot_docs/cdiscpilot01.pdf"
    sections=[
        dict(id="DESIGN",title="Three-arm Xanomeline TTS study",summary="Placebo, Xanomeline Low Dose and Xanomeline High Dose; efficacy and safety in mild-to-moderate Alzheimer's disease. Transdermal treatment; primary assessment at Week 24.",source=csr),
        dict(id="POPULATION",title="Screened and randomized populations",summary=f"SDTM DM: {data['dm'].USUBJID.nunique()} distinct subjects / {len(data['dm'])} rows. ADSL: {data['adsl'].USUBJID.nunique()} distinct subjects / {len(data['adsl'])} rows. Analysis populations use their own flags and exact denominators.",source=BASE+"sdtm/cdiscpilot01/dm.xpt"),
        dict(id="ADAS",title="Primary efficacy: ADAS-Cog (11)",summary="Week 24 LOCF, EFFFL=Y and ANL01FL=Y. Three-arm CHG ~ TRTP + C(SITEGR1) + BASE; categorical-treatment high-dose vs placebo contrast Δ=-1.0060, p=0.2326. This is the published treatment-comparison model, distinct from the primary continuous-dose response test.",source=csr),
        dict(id="CIBIC",title="Co-primary efficacy: CIBIC+",summary="Week 24 LOCF, efficacy population. Three-arm AVAL ~ TRTP + C(SITEGR1); high-dose vs placebo contrast p=0.799. No CMH substitution.",source=csr),
        dict(id="TTDE",title="Primary safety: time to dermatologic event",summary="ADTTE TTDE with event/censoring status; AE onset and exposure dates determine safety interpretation. Preserve SAE reconciliation, exposure and treatment-emergent lineage. TTDE survival reproduction is not claimed by the current endpoint checks.",source=csr),
        dict(id="GATE2",title="Submitted CSR Section 14 summaries",summary="Demographics 14-2.01, NPI-X descriptive summaries 14-3.10 (not 14-3.03), lab shifts 14-6.04, and vital values/changes 14-7.01/02. Current diffs cover named frozen-ADaM summary outputs, not all published TFLs or upstream derivations.",source=csr),
        dict(id="GOVERNANCE",title="Blueprint-driven DRP-B governance",summary="Gate 1 protects primary endpoints, populations and safety; Gate 2 retains submitted summary inputs. Protect dates, visits, treatment-emergent flags and identifiers. Workbook suppression labels remain proposals until downstream lineage is verified.",source="User workbook Protocol_SAP_DRP_Matrix and ADaM_TFL_Submission_Map"),
    ]
    sections.append(dict(id="CRF",title="Official annotated CRF: blankcrf.pdf",
                         summary=f"Parsed {crf['annotationCount']} embedded annotations across {crf['pageCount']} PDF pages. "+crf["note"],
                         source=crf["source"]))
    for domain in crf["domains"]:
        sections.append(dict(id="CRF-"+domain["domain"],title=domain["domain"]+" annotated CRF page map",
                             summary=f"{domain['count']} authored domain references. PDF pages: "+", ".join(map(str,domain["pages"]))+
                             ". Annotation variable tokens: "+(", ".join(domain["variables"]) or "No domain-prefixed variable tokens")+
                             ". Full annotation text and conditions are preserved in the workbook.",
                             source=crf["source"]+"#page="+str(domain["pages"][0])))
    byid={r["id"]:r for r in rules}
    trace=[]
    for row in workbook["Published_Control_DRP_A"].iter_rows(min_row=5,max_row=129,values_only=True):
        rid,_,domain,targets,_,description,link,tier,disposition=row[:9]
        if rid not in byid or disposition!="RETAINED":
            continue
        refs=["GOVERNANCE"]
        if domain in ["DM","DS","EX"]: refs.append("POPULATION")
        if domain in ["AE","EX"] or "Safety" in str(tier): refs.append("TTDE")
        if domain=="QS":
            refs.append("CIBIC" if "CIBIC" in str(targets)+description else "GATE2" if "NPI" in str(targets)+description else "ADAS")
        if str(tier).startswith("Tier 2") or domain in ["LB","VS","MH","CM"]: refs.append("GATE2")
        if any(d["domain"]==domain for d in crf["domains"]): refs.append("CRF-"+domain)
        trace.append(dict(id=rid,domain=domain,blueprintRef=" / ".join(dict.fromkeys(refs)),protocolLink=str(link),
                          disposition=disposition,status=byid[rid]["evaluabilityStatus"]))
    internal=[r for r in rules if r["status"]!="non_xpt"]
    counts=dict(assessed=len(internal),executed=sum(r["status"]=="evaluated" for r in internal),
                blocked=sum(r["status"].startswith("blocked") for r in internal),nonXpt=len(rules)-len(internal),
                retained=sum(r["disposition"]=="RETAINED" for r in internal),suppressed=sum(r["disposition"]=="SUPPRESSED" for r in internal))
    fixes=[
        dict(fix="Stage 1 before downstream review",status="Implemented",evidence="First workbook tab and first navigation item; retained rules linked to blueprint aims."),
        dict(fix="Official three-arm endpoint contrasts",status="Verified",evidence="ADAS-Cog delta/p and CIBIC+ p match published precision."),
        dict(fix="Exact source denominators",status="Verified",evidence="Rows and unique subjects measured per file; trial-summary TS has no subject denominator."),
        dict(fix="Date and identifier protection",status="Implemented",evidence="--DTC/--DY and derivation keys protected; no global Tier 3 certification."),
        dict(fix="Separate stability and synthetic power",status="Implemented",evidence="6,000 pilot iterations plus 6,000 independent synthetic trials across six rates."),
        dict(fix="Gate 2 cell-level concordance",status="Partial scope",evidence=f"{sum(x['cells'] for x in gate2)} cells compared; {sum(x['differences'] for x in gate2)} differences; {100*sum(x['differences'] for x in gate2)/sum(x['cells'] for x in gate2):.4f}% cell mismatch. Frozen-ADaM output scope, not full SDTM-to-CSR reproduction."),
        dict(fix="115 candidates separate from 10 Non-XPT rules",status="Partial execution" if counts["blocked"] else "Verified",evidence=f"{counts['executed']} executed, {counts['blocked']} blocked, {counts['nonXpt']} Non-XPT; {counts['retained']} retained and {counts['suppressed']} suppressed candidates under workbook policy.")
    ]
    return dict(title="Stage 1: Protocol & SAP Blueprint — What the Study Aims to Achieve",sections=sections,sources=sources,traceability=trace,
                crf={k:v for k,v in crf.items() if k!="annotations"}),counts,fixes
