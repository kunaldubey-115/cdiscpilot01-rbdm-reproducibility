"""Evaluate opt-in reconstruction hypotheses without opening the paired gate."""
import json
import hashlib
import pandas as pd
from validate_rebuild import DATA, OUT, SDTM, specifications, compare_bds
from rebuild_adsl import rebuild_adsl
from rebuild_bds import rebuild_advs, rebuild_adlbc, rebuild_adlbh
from rebuild_questionnaires import rebuild_adqsadas, rebuild_adqsnpix

CONVENTIONS=[
    {"dataset":"ADVS","experiment":"Last observed scheduled Week 4–26 value for EOT, rather than postbaseline through Week 24.","authority":"Empirical hypothesis; conflicts with SAP boundary; not original SAS authentication."},
    {"dataset":"ADQSADAS","experiment":"Carry selected total into non-selected total records; label LOCF only if value changes. Later missing windows use latest carried provenance. Keep source QSSEQ, select closest records including missing item values, suppress baseline CHG/PCHG, clear baseline flag and set analysis flag on added LOCF rows.","authority":"Empirical hypothesis; non-selected totals can differ from item sums. Not authenticated original SAS logic."},
    {"dataset":"ADQSNPIX","experiment":"NPTOTMN uses selected observations at analysis Weeks 6, 8, 10 and 12 (4 < AVISITN <= 12), without whole-number rounding. Retain original Week 4–24 label, window bounds, target day 98 and zero window difference. Baseline derived records retain baseline flag; CHG includes baseline; zero baselines have missing PCHG.","authority":"Substantive conflict with described Week 4–24 mean. Target-informed reconstruction hypothesis, not evidence that SAP was followed."},
    {"dataset":"ADLBC / ADLBH eligibility","experiment":"Exclude source VISITNUM 2, 3, 6 and 201. Maximal abnormality and EOT use scheduled visits 4,5,7,8,9,10,11,12. Previous-visit changes use scheduled visits 1,4,5,7,8,9,10,11,12,13. Do not flag all-missing maxima.","authority":"Empirical eligibility hypothesis; does not use target record identities or per-subject exceptions."},
    {"dataset":"ADLBC / ADLBH calculations","experiment":"Use max absolute distance from 0.5*raw LLN / 1.5*raw ULN; preserve this measure on derived rows. LO/HI ratios use LLN/ULN respectively. Represent zero analysis LLN as missing, but use raw bounds for distance and scaled change. Apply value-level define precision to scaled changes after rounding floating arithmetic to 12 decimal places; suppress baseline CHG.","authority":"Reference-compatible interpretation, including differences from literal define comments. Comparison tolerances unchanged."},
    {"dataset":"ADLBC / ADLBH categories","experiment":"For raw ANRIND retain default N even when result is missing; map source ABNORMAL to H when numeric upper limit is missing. Derived missing changes retain blank ANRIND.","authority":"Reference-quality warning: N for missing results is not evidence of clinical normality and must not suppress missing-data review."},
    {"dataset":"Formatting","experiment":"Use 16-character right-aligned visit labels for labs/NPI; lab missing visit label is a right-aligned dot. NPI window labels include spaces; Item B label has an extra space before Score. SAS transport-zero magnitudes are treated as zero in numeric keys and questionnaire denominators.","authority":"Explicit formatting/transport conventions, not changes to clinical comparison tolerances."},
]

def main():
    files=[p for p in DATA.rglob("*") if p.suffix in (".xpt",".pdf",".xml",".sas")]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    spec=specifications()
    source={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
    source["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
    adsl,_=rebuild_adsl(source,spec["adsl"],mode="reference-compatible")
    builders={"adqsadas":rebuild_adqsadas,"adqsnpix":rebuild_adqsnpix,
              "adlbc":rebuild_adlbc,"adlbh":rebuild_adlbh,"advs":rebuild_advs}
    # Construction precedes any target loading. Targets never enter builders.
    frames={(name,mode):builder(source,adsl,spec[name],mode=mode)
            for name,builder in builders.items() for mode in ("sap","reference-compatible")}
    summary=[];comparisons={}
    with pd.ExcelWriter(OUT/"ADaM_Reference_Compatibility_Experiments.xlsx",engine="openpyxl") as writer:
        pd.DataFrame([{"status":"EXPERIMENT ONLY — no paired gate waiver or activation",
                       "scope":"CIBIC+ policy, passing builders and numeric tolerances unchanged."}]).to_excel(writer,sheet_name="Experiment_Status",index=False)
        pd.DataFrame(CONVENTIONS).to_excel(writer,sheet_name="Tested_Conventions",index=False)
        for name in builders:
            target=pd.read_sas(DATA/f"{name}.xpt",format="xport",encoding="utf8")
            for mode,short in [("sap","SAP"),("reference-compatible","Reference")]:
                frame,proof=frames[name,mode]
                try:
                    results=compare_bds(frame,target,proof,name)
                    matching=sum(r["status"]=="MATCH" for r in results)
                    status="MATCH" if matching==len(target.columns) else "NOT MATCHED"
                except (ValueError,KeyError,TypeError) as error:
                    results=[{"status":"BLOCKED","reason":str(error)}];matching=0;status="BLOCKED"
                summary.append(dict(dataset=name.upper(),mode=mode,status=status,rebuiltRows=len(frame),
                                    targetRows=len(target),matchingFields=matching,targetFields=len(target.columns)))
                comparisons[name+"_"+short]=results
                pd.DataFrame(results).to_excel(writer,sheet_name=name.upper()+"_"+short,index=False)
                if short=="Reference":
                    frame.to_csv(OUT/(name.upper()+"_Experimental_Reference.csv"),index=False)
        pd.DataFrame(summary).to_excel(writer,sheet_name="Mode_Comparison",index=False)
        for sheet in writer.book:
            sheet.freeze_panes="A2"
            sheet.auto_filter.ref=sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width=28
    assert all(hashlib.sha256(__import__("pathlib").Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()),"Cache changed"
    result=dict(status="EXPERIMENT ONLY",pairedRunsExecuted=False,pairedGateChanged=False,
                limitation="Conventions were developed against these targets. Agreement is reconstruction calibration, not independent validation or original-program authentication.",
                numericTolerance={"absolute":1e-8,"relative":1e-10},conventions=CONVENTIONS,
                summary=summary,comparisons=comparisons,sourceHashes=hashes)
    (OUT/"reference_compatibility_experiments.json").write_text(json.dumps(result,indent=2))
    print(pd.DataFrame(summary).to_string(index=False))

if __name__=="__main__":
    main()
