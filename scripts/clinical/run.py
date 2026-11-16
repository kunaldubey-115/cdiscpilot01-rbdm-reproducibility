"""Run: python scripts/clinical/run.py. Public synthetic pilot study only."""
import json
import hashlib
from datetime import datetime, timezone
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fetch_data import ROOT, DATA, SDTM, fetch_all
from rules import evaluate_rules, classify_variables
from clinical_statistics import analyse, powered_simulation
from tables import audit_tables
from blueprint import build_blueprint

OUT = ROOT / "generated-artifacts/clinical"
CSR = "https://raw.githubusercontent.com/phuse-org/phuse-scripts/master/data/adam/TDF_ADaM_v1.0/cdiscpilot_docs/cdiscpilot01.pdf"

def sheet(w, name, headers, rows):
    if name in w:
        pos = w.sheetnames.index(name)
        del w[name]
        s = w.create_sheet(name, pos)
    else:
        s = w.create_sheet(name)
    s.append(headers)
    for r in rows:
        s.append(r)
    s.freeze_panes = "A2"
    s.auto_filter.ref = s.dimensions
    for cell in s[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="245C58")
    for col in s.columns:
        s.column_dimensions[col[0].column_letter].width = min(65, max(15, len(str(col[0].value))+3))
        for cell in col:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    return s

def main():
    sources = fetch_all()
    data = {n: pd.read_sas(DATA/f"{n}.xpt", format="xport", encoding="utf8") for n in sources}
    w = openpyxl.load_workbook(ROOT/"scripts/clinical/input/template.xlsx")
    w["Protocol_SAP_DRP_Matrix"]["D6"]="Treatment effect (Delta) in three-arm CIBIC+ ANOVA; pooled-site factor"
    w["Protocol_SAP_DRP_Matrix"]["D8"]="Pooled-site adjustment in three-arm ANCOVA/ANOVA"
    rules = evaluate_rules(w, data)
    mapping = classify_variables(w, data)
    baseline, simulation = analyse(data)
    baseline["poweredDesign"], supplementary = powered_simulation()
    gate2 = audit_tables(data, OUT/"Gate2_Before_After_Audit.xlsx")
    baseline["blueprint"], baseline["ruleAudit"], baseline["auditFixes"] = build_blueprint(data,w,rules,gate2)
    pd.DataFrame(mapping,columns=["Dataset","Variable","Tier","Rationale"]).to_csv(OUT/"Variable_Tier_Audit.csv",index=False)
    datasets = []
    for n,d in data.items():
        tier = "Mixed: see variable audit" if n in SDTM else ("Gate 2 / Tier 2" if n in ["adqsnpix","adlbc","adlbh","advs"] else "Gate 1 / Tier 1")
        datasets.append(dict(name=n.upper(), standard="SDTM" if n in SDTM else "ADaM", rows=len(d),
            variables=len(d.columns), subjects=int(d.USUBJID.nunique()), tier=tier, source=sources[n],
            sha256=hashlib.sha256((DATA/f"{n}.xpt").read_bytes()).hexdigest()))
    warnings = [
        f"Workbook policy among the 115 candidates is {baseline['ruleAudit']['retained']} retained / {baseline['ruleAudit']['suppressed']} suppressed, not the requested 40/75. Original rule dispositions are preserved; suppression is not authorized without lineage evidence.",
        "The active ADAS-Cog model is the official three-arm categorical-treatment ANCOVA. Its contrast matches the published result; the non-significant pilot baseline is not an 80%-powered effect.",
        "CIBIC+ now uses three-arm categorical-treatment ANOVA. Pairwise contrasts are distinct from the CSR's continuous-dose response test.",
        f"Of 115 in-database candidates, {baseline['ruleAudit']['executed']} have executed checks and {baseline['ruleAudit']['blocked']} are blocked by absent fields or missing predicate specifications. Exactly 10 external rules are N/A — Non-XPT. Null counts are unknown, never zero; Programmatic Rule Discrepancies are not confirmed site queries.",
        "Pilot simulations measure estimate drift, SE inflation and p-value shift. The supplementary 80%-powered simulation uses a separate synthetic cohort and explicit noise assumptions; it is not evidence about pilot-study power.",
        "Gate 2 descriptive/shift summaries are regenerated before and after scoped non-input metadata perturbation and compared cell by cell. Published inferential tests/layouts and upstream SDTM-to-ADaM derivations are not fully reproduced; zero diffs do not establish universal CSR concordance.",
        "Official CSR NPI-X summaries are Table 14-3.10, not 14-3.03. Vital values/changes are Tables 14-7.01/02; ADVS has no normality shift flags. No clinical thresholds were invented.",
        "Variable tiers are provisional workbook mappings. Dates and identifiers are protected when their downstream lineage is uncertain; not every --DTC or --DY field is safely suppressible.",
        f"Source counts: DM {data['dm'].USUBJID.nunique()} distinct subjects; ADSL {data['adsl'].USUBJID.nunique()}. Every file's footprint uses its own exact rows and unique subjects."
    ]
    methodology = [
        "Sources: 10 SDTM and 9 ADaM XPT files from the user-specified public PHUSE repository. SHA-256 hashes identify the exact bytes used.",
        "Analysis cohort: PARAMCD ACTOT, AVISIT Week 24, EFFFL Y, ANL01FL Y. Retain observed and LOCF records selected by ANL01FL, rather than selecting only DTYPE LOCF. Enforce one record per subject.",
        f"Active ANCOVA retains all three treatment groups ({baseline['n']} subjects) and estimates the high-dose versus placebo contrast with pooled site and baseline covariates.",
        "Official comparator: supporting Table 14-3.01, treatment comparison PROC GLM: H vs P estimate -1.00601360, SE 0.84052936, p 0.2326. Numerical match tolerance: 5e-8 for delta and published four-decimal rounding for p. Source: "+CSR,
        "Seed 20261115; 1,000 iterations at each of 0%, 1%, 2%, 5%, 10%, 15%. Independent Bernoulli masks use the same probability for CHG and BASE; additive zero-mean normal errors have SD equal to clean residual SD and baseline SD respectively. No clipping. Treatment and site are held fixed.",
        "Pilot Analytical Estimate & TFL Stability: refit the three-arm ANCOVA per iteration; delta drift = mean perturbed contrast minus baseline; SE inflation = 100*(mean SE/clean SE-1); p shift = median perturbed p minus baseline p. Not prospective power.",
        "CIBIC+ uses AVAL ~ categorical TRTP + categorical SITEGR1, EFFFL Y, ANL01FL Y, Week24 CIBICVAL records across all arms; one observation per subject. Contrast reported high dose minus placebo.",
        "Supplementary 80%-Powered Superiority Simulation: 100 independent synthetic subjects per arm, normal residual SD 1, effect calibrated by noncentral t to theoretical 80% power at two-sided alpha .05. 1,000 independent trials per rate; Bernoulli contamination with Gaussian error SD 2, seed 20261116. Common random numbers across rates; Wilson 95% Monte Carlo intervals. These assumptions illustrate, not guarantee, erosion in clinical data.",
        "Gate2_Before_After_Audit.xlsx contains actual before/after/diff sheets for demographics, NPI-X, chemistry/hematology shifts and vital values/changes. Seed 20261117; 15% independent Bernoulli perturbation on explicitly named non-input metadata. Exact equality including paired missing cells, and positive controls must detect changed output values.",
        "No source field is globally certified Tier 3 from this test. All --DTC/--DY, ADT, treatment dates, analysis visits, treatment-emergent flags and sequence/subject keys are protected; remaining unverified Tier3 proposals are retained pending lineage evidence.",
        "Rules use explicit predicates in scripts/clinical/rules.py. Unavailable fields, source documents and manual clinical adjudication are flagged instead of substituting missingness counts. No site queries were actually issued.",
        "The original workbook's simulated dashboard and projected counts are replaced, not carried forward. Retained source traceability is documentary and provisional, not independently validated clinical governance."
    ]
    filenames = ["CDISCPILOT01_Final_Verified_Results.xlsx","Manuscript_Results_Figure.png","analysis.json","Gate2_Before_After_Audit.xlsx","Variable_Tier_Audit.csv"]
    report = dict(study="CDISCPILOT01", generatedAt=datetime.now(timezone.utc).isoformat(), subjects=int(data["adsl"].USUBJID.nunique()),
                  datasets=datasets, rules=rules, simulation=simulation, baseline=baseline, warnings=warnings,
                  supplementary=supplementary, gate2=gate2,
                  methodology=methodology, downloads=[dict(name=f,url="/api/analysis/files/"+f,
                  description="Audited results with explicit limitations" if f.endswith("xlsx") else "300-DPI sensitivity figure" if f.endswith("png") else "Machine-readable results and provenance") for f in filenames])
    headers = ["Rule ID","Domain","Exact specification","Workbook tier","Disposition","Evaluability_Status","Records evaluated","Programmatic Rule Discrepancies","Evidence / limitations"]
    rr = [[r[k] if r[k] is not None else r["evaluabilityStatus"] for k in ["id","domain","description","tier","disposition","evaluabilityStatus","evaluated","discrepancies","reason"]] for r in rules]
    sheet(w,"Published_Control_DRP_A",headers,rr)
    sheet(w,"Published_RiskBased_DRP_B",headers,[row for row in rr if row[4]=="RETAINED"])
    sheet(w,"Domain_Footprint_Queries",["Domain","Exact rows","Exact variables","Distinct subjects","Rows per subject","Cell footprint","Rules evaluated","Rules unresolved","Programmatic Rule Discrepancies","Actual site queries"],[
        [d["name"],d["rows"],d["variables"],d["subjects"],d["rows"]/d["subjects"],d["rows"]*d["variables"],
         sum(r["status"]=="evaluated" for r in rules if r["domain"]==d["name"]),
         sum(r["status"]!="evaluated" for r in rules if r["domain"]==d["name"]),
         sum(r["discrepancies"] or 0 for r in rules if r["domain"]==d["name"]),"Not measured"]
        for d in datasets if d["standard"]=="SDTM"])
    sheet(w,"Power_Erosion_Simulation",["Error rate (%)","Clean delta","Mean perturbed delta","Delta drift","Clean SE","Mean perturbed SE","SE inflation (%)","Clean p","Median perturbed p","p-value shift","Iterations"],[
        [s[k] for k in ["errorRate","deltaA","deltaB","deltaDrift","seA","seB","seInflation","pA","pB","pShift","iterations"]] for s in simulation])
    sheet(w,"Supplementary_Powered_Cohort",["Error rate (%)","Power (%)","95% MC lower","95% MC upper","Iterations"],[[s[k] for k in ["errorRate","power","lower","upper","iterations"]] for s in supplementary])
    sheet(w,"Gate2_Cell_Diff_Audit",["Summary","Cells compared","Differences","Metadata cells perturbed","Scope"],[[s[k] for k in ["name","cells","differences","changedMetadataCells","scope"]] for s in gate2])
    sheet(w,"Executive_Dashboard",["Measure","Computed value","Interpretation"],[
        ["Verification status","PARTIAL","Filename requested by user is not certification of all claims."],
        ["Active three-arm delta",baseline["delta"],f"High dose minus placebo; {baseline['n']} subjects"],
        ["Active three-arm p",baseline["pValue"],"Not statistically significant"],
        ["CIBIC+ three-arm ANOVA delta",baseline["cibic"]["delta"],"High dose minus placebo"],
        ["CIBIC+ three-arm ANOVA p",baseline["cibic"]["pValue"],"Published contrast rounded p = 0.799"],
        ["CSR three-arm delta",baseline["csrDelta"],"Matches -1.00601360"],
        ["CSR three-arm p",baseline["csrPValue"],"Matches published 0.2326 after rounding"],
        ["CSR numerical reproduction",str(baseline["csrMatch"]),"Supporting Table 14-3.01"],
        ["SDTM records",sum(d["rows"] for d in datasets if d["standard"]=="SDTM"),"All source rows"],
        ["SDTM variables",sum(d["variables"] for d in datasets if d["standard"]=="SDTM"),"Sum of domain columns"],
        *[["Limitation",warning,"Read before interpretation"] for warning in warnings]])
    sheet(w,"Variable_Tier_Audit",["Dataset","Variable","Provisional tier","Rationale"],mapping)
    # Retain the user's documentary lineage without presenting its old aggregates as measurements.
    source_map = w.copy_worksheet(w["ADaM_TFL_Submission_Map"])
    source_map.title = "Original_Map_Unverified"
    source_map["A1"] = "ORIGINAL USER-SUPPLIED MAP — UNVERIFIED DOCUMENTARY REFERENCE"
    for row in source_map:
        for cell in row:
            if cell.data_type == "f":
                cell.value = "Original projected formula — not a measured result"
    # Replace unsupported aggregate claims in the submission map with explicit dataset inventory.
    destinations={"ADQSADAS":"14-3.01: three-arm ANCOVA","ADQSCIBC":"14-3.02: three-arm ANOVA",
                  "ADQSNPIX":"14-3.10: NPI-X summaries","ADSL":"14-2.01: baseline demographics",
                  "ADLBC":"14-6.04: chemistry shifts","ADLBH":"14-6.04: hematology shifts",
                  "ADVS":"14-7.01/02: vital values and changes"}
    sheet(w,"ADaM_TFL_Submission_Map",["Dataset","Standard","Rows","Variables","Gate","Source","SHA-256","Active CSR traceability"],
          [[d[k] for k in ["name","standard","rows","variables","tier","source","sha256"]]+[destinations.get(d["name"],"Source/dependency: see variable tier audit")] for d in datasets])
    sheet(w,"Methods_and_Limitations",["Section","Details"],[["Method",m] for m in methodology]+[["Warning",v] for v in warnings])
    sheet(w,"Replit_and_XPT_Guide",["Command","Purpose"],[["python scripts/clinical/run.py","Reproduce analysis and exports"],["Public synthetic study only","Not a validated clinical production system"]])
    blueprint=baseline["blueprint"]
    bp=sheet(w,"Protocol_SAP_Blueprint",["Blueprint ID","Study aim / scope","Evidence / source"],[
        [s["id"],s["title"]+": "+s["summary"],s["source"]] for s in blueprint["sections"]])
    w.move_sheet(bp,offset=-w.index(bp))
    crf=json.loads((OUT/"CRF_Page_Domain_Annotations.json").read_text())
    sheet(w,"CRF_Page_Domain_Annotations",["PDF page (1-based)","Authored subject","Domains (excluding NEID)","Annotation text / conditions","Source page"],
          [[r[k] for k in ["page","subject","domains","annotation","source"]] for r in crf["annotations"]])
    sheet(w,"Blueprint_Rule_Traceability",["Rule","Domain","Blueprint references","Original protocol/SAP reference","Disposition","Evaluability_Status"],
          [[s[k] for k in ["id","domain","blueprintRef","protocolLink","disposition","status"]] for s in blueprint["traceability"]])
    sheet(w,"Blueprint_Source_Manifest",["Document","Status","URL","SHA-256","Note"],
          [[s[k] for k in ["name","status","url","sha256","note"]] for s in blueprint["sources"]])
    trial_summary=pd.read_sas(DATA/"ts.xpt",format="xport",encoding="cp1252")
    sheet(w,"Trial_Summary_TS",list(trial_summary.columns),
          trial_summary.astype(object).where(trial_summary.notna(),None).values.tolist())
    sheet(w,"Seven_CSR_Audit_Fixes",["Audit fix","Status","Evidence"],
          [[s[k] for k in ["fix","status","evidence"]] for s in baseline["auditFixes"]])
    w.save(OUT/filenames[0])
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    axes[0].plot([s["errorRate"] for s in simulation],[s["deltaDrift"] for s in simulation],"o-",color="#245c58")
    axes[0].set(xlabel="Injected error probability (%)",ylabel="Mean contrast drift (ADAS-Cog points)",title="A. Pilot: analytical estimate stability")
    measured=[r for r in rules if r["status"]=="evaluated"]
    powers=[s["power"] for s in supplementary]
    axes[1].errorbar([s["errorRate"] for s in supplementary],powers,
        yerr=[[p-s["lower"] for p,s in zip(powers,supplementary)],[s["upper"]-p for p,s in zip(powers,supplementary)]],
        fmt="o-",color="#b77535",capsize=3)
    axes[1].set(xlabel="Injected error probability (%)",ylabel="Power (%) with 95% Monte Carlo interval",title="B. Supplementary synthetic 80%-powered cohort",ylim=(0,100))
    fig.suptitle("Analytical Estimate & TFL Stability | Separate synthetic power experiment",fontweight="bold")
    fig.text(.05,.02,"1,000 iterations per rate. Synthetic power is not pilot-study power. Scoped Gate 2 cell diffs are supplied in a separate audit workbook.",fontsize=8)
    fig.tight_layout(rect=[0,.06,1,.94])
    fig.savefig(OUT/filenames[1],dpi=300)
    fig.savefig(OUT/"Power_Erosion_and_Query_Reduction.png",dpi=300)
    plt.close(fig)
    temp=OUT/"analysis.tmp"
    temp.write_text(json.dumps(report,indent=2,allow_nan=False))
    temp.replace(OUT/"analysis.json")
    print(json.dumps({"stage1":"Protocol_SAP_Blueprint is Tab 1",
                      "rules":baseline["ruleAudit"],
                      "ADAS_delta":baseline["delta"],"ADAS_p":baseline["pValue"],
                      "CIBIC_p":baseline["cibic"]["pValue"],
                      "sevenAuditFixes":[{"fix":a["fix"],"status":a["status"]} for a in baseline["auditFixes"]],
                      "gate2Cells":sum(a["cells"] for a in gate2),
                      "gate2Differences":sum(a["differences"] for a in gate2),
                      "gate2Scope":"Regenerated frozen-ADaM summaries only",
                      "datasets":len(datasets)}))

if __name__=="__main__":
    if (OUT/"scoped-study/scoped_results.json").exists():
        from export_scoped_study import export
        export(json.loads((OUT/"scoped-study/scoped_results.json").read_text()))
        raise SystemExit(0)
    main()
    import subprocess
    result=subprocess.run(["python",str(ROOT/"scripts/clinical/validate_rebuild.py")],check=False)
    if result.returncode not in (0,2):
        raise RuntimeError("Clean-reference validation failed to execute; outputs must not be published as current.")
    from validate_variants import main as validate_variants
    validate_variants()
    from dual_track import main as validate_dual_tracks
    validate_dual_tracks()
    from refresh_outputs import refresh_outputs
    refresh_outputs(fresh_figures=True)
