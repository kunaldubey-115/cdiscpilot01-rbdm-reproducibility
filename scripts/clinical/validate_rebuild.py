"""Independent cache-only clean-target gate. A failed gate prohibits challenge runs."""
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pymupdf
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rebuild_adsl import rebuild_adsl
from rebuild_adae import rebuild_adae
from rebuild_adtte import rebuild_adtte
from rebuild_cibic import rebuild_cibic
from rebuild_bds import rebuild_advs, rebuild_adlbc, rebuild_adlbh
from rebuild_questionnaires import rebuild_adqsadas, rebuild_adqsnpix
from reconstruction_conventions import CONVENTIONS, REFERENCE_COMPATIBILITY_CONVENTIONS, CIBIC_IMPUTATION_POLICY

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"generated-artifacts/clinical/data"
OUT=ROOT/"generated-artifacts/clinical"
TARGETS="adsl adqsadas adqscibc adqsnpix adae adtte adlbc adlbh advs".split()
SDTM="dm ds ex ae qs lb vs mh cm sc".split()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def all_targets_passed(coverage):
    """A single passing dataset, missing dataset, or duplicated row cannot open the gate."""
    required={n.upper() for n in TARGETS}
    return (len(coverage)==len(required)
            and {r["dataset"] for r in coverage}==required
            and all(r["status"]=="PASSED" or (
                r["dataset"]=="ADQSCIBC" and r["status"]=="PASSED (SAP-Aligned Convention)"
                and r.get("conventionVerified") is True) for r in coverage))

def cibic_convention_passed(fields):
    allowed={"VISIT","VISITNUM","ADY","ADT","AWTDIFF","QSSEQ"}
    return (len(fields)==36 and all(r["compared"]==730 for r in fields)
            and {r["variable"] for r in fields if r["status"]!="MATCH"}==allowed
            and all(r["mismatches"]==35 for r in fields if r["variable"] in allowed))

def cibic_exception_rows(rebuilt,target):
    """Require the same 35 LOCF records to explain all six field discrepancies."""
    keys=["USUBJID","AVISITN"]
    actual=rebuilt.loc[rebuilt.DTYPE.eq("LOCF")].set_index(keys).sort_index()
    expected=target.loc[target.DTYPE.eq("LOCF")].set_index(keys).sort_index()
    if not actual.index.equals(expected.index):return []
    masks=[]
    for field in ["VISIT","VISITNUM","ADY","ADT","AWTDIFF","QSSEQ"]:
        a,b=actual[field],expected[field]
        equal=(np.isclose(a,b,atol=1e-8,rtol=1e-10,equal_nan=True)
               if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)
               else (a.eq(b) | (a.isna() & b.isna())).to_numpy())
        masks.append(~equal)
    if not all(int(mask.sum())==35 and np.array_equal(mask,masks[0]) for mask in masks):
        return []
    return [dict(subject=subject,analysisVisit=float(visit),reason="Approved SAP-aligned LOCF provenance exception")
            for subject,visit in actual.index[masks[0]]]

def specifications():
    definition=DATA/"supplemental/adam-define.xml"
    if not definition.exists():
        definition=DATA/"adam-define.xml"
    root=ET.parse(definition).getroot()
    lists={}
    for node in root.iter():
        if node.tag.split("}")[-1]=="CodeList":
            lists[node.get("OID")]={c.get("CodedValue"):" ".join(c.itertext()).strip()
                                   for c in node if c.tag.split("}")[-1]=="CodeListItem"}
    items={}
    for item in root.iter():
        if item.tag.split("}")[-1]!="ItemDef":
            continue
        oid=item.get("OID","")
        if "." not in oid:
            continue
        domain=oid.split(".")[0].lower()
        if domain not in TARGETS:
            continue
        ref=next((c.get("CodeListOID") for c in item if c.tag.split("}")[-1]=="CodeListRef"),None)
        items.setdefault(domain,{})[item.get("Name")]=dict(oid=oid,comment=item.get("Comment",""),origin=item.get("Origin",""),
                                                          codes=lists.get(ref,{}),precision=item.get("SignificantDigits"))
        parts=oid.split(".")
        if len(parts)==3 and parts[1] in items[domain]:
            items[domain][parts[1]].setdefault("values",{})[parts[2]]=dict(
                comment=item.get("Comment",""),precision=item.get("SignificantDigits"))
    return items

def compare_adsl(rebuilt,target,evidence):
    return compare_records(rebuilt,target,evidence,["USUBJID"])

def compare_cibic(rebuilt,target,evidence):
    # LOCF has one record per subject/parameter/analysis visit. Its source
    # sequence is a value to validate, not its identity. Observed records
    # retain sequence in their identity because a window may hold several.
    def keyed(frame):
        result=frame.copy()
        if frame.empty:
            result["__record_key"]=pd.Series(index=frame.index,dtype=str)
            return result
        identity=frame[["USUBJID","PARAMCD","AVISITN","DTYPE"]].astype(str).apply(
            lambda row: json.dumps(row.tolist(),ensure_ascii=True),axis=1)
        sequence=frame.QSSEQ.where(frame.DTYPE.ne("LOCF"),0.).astype(str)
        result["__record_key"]=identity+"|"+sequence
        return result
    rows=compare_records(keyed(rebuilt),keyed(target),evidence,["__record_key"])
    return [r for r in rows if r["variable"]!="__record_key"]

def compare_bds(rebuilt,target,evidence,name):
    """Match derived records by analysis identity, validating provenance as values."""
    def keyed(frame):
        frame=frame.copy()
        parts=[]
        for row in frame.to_dict("records"):
            visit=row.get("AVISITN")
            if pd.notna(visit) and abs(visit)<1e-70:visit=0.
            if row.get("DTYPE") in ("LOCF","AVERAGE"):
                key=[row["USUBJID"],row["PARAMCD"],row["DTYPE"],visit]
            elif name=="advs":
                key=[row["USUBJID"],row["PARAMCD"],row["ATPT"],
                     "EOT" if visit==99 else "OBS",None if visit==99 else row["VSSEQ"]]
            elif name.startswith("adlb"):
                key=[row["USUBJID"],row["PARAMCD"],"EOT" if visit==99 else "OBS",
                     None if visit==99 else row["LBSEQ"]]
            else:
                key=[row["USUBJID"],row["PARAMCD"],"OBS",row["VISITNUM"],row["ADT"]]
            parts.append(json.dumps(key,ensure_ascii=True))
        frame["__record_key"]=pd.Series(parts,index=frame.index,dtype=str)
        return frame
    rows=compare_records(keyed(rebuilt),keyed(target),evidence,["__record_key"])
    return [r for r in rows if r["variable"]!="__record_key"]

def compare_records(rebuilt,target,evidence,keys):
    rebuilt=rebuilt.copy()
    target=target.copy()
    # SAS XPORT numeric zero may decode to its tiny transport representation.
    # Canonicalize only numerical keys indistinguishable from zero at tolerance.
    for frame in (rebuilt,target):
        for key in keys:
            if pd.api.types.is_numeric_dtype(frame[key]):
                frame.loc[frame[key].abs().lt(1e-70),key]=0.
    if rebuilt.duplicated(keys).any() or target.duplicated(keys).any():
        raise ValueError("Nonunique validation key")
    actual=rebuilt.set_index(keys)
    expected=target.set_index(keys)
    union=actual.index.union(expected.index)
    key_diff=len(actual.index.symmetric_difference(expected.index))
    result=[dict(variable=key,status="MATCH" if not key_diff else "MISMATCH",
                 compared=len(union),mismatches=key_diff,evidence=evidence.get(key,""),example="") for key in keys]
    for column in expected:
        if column not in actual:
            result.append(dict(variable=column,status="NOT REBUILT",compared=0,mismatches=None,
                               evidence=evidence.get(column,"No implemented, validated specification-based derivation."),example=""))
            continue
        a=actual[column].reindex(union);b=expected[column].reindex(union)
        if pd.api.types.is_numeric_dtype(b) and pd.api.types.is_numeric_dtype(a):
            eq=pd.Series(np.isclose(a,b,rtol=1e-10,atol=1e-8,equal_nan=True),index=union)
        else:
            eq=a.eq(b) | (a.isna() & b.isna())
        eq &= union.isin(actual.index) & union.isin(expected.index)
        bad=union[~eq]
        example="; ".join(f"{k}: rebuilt={a.loc[k]!r}, target={b.loc[k]!r}" for k in bad[:3])
        result.append(dict(variable=column,status="MATCH" if not len(bad) else "MISMATCH",
                           compared=len(union),mismatches=len(bad),evidence=evidence.get(column,""),example=example))
    return result

def main():
    # No download/fetch operation. Hash every existing cached source before work.
    protected=[p for p in DATA.rglob("*") if p.is_file() and p.suffix in (".xpt",".xml",".pdf",".sas")]
    before={str(p):digest(p) for p in protected}
    spec=specifications()
    sdtm={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
    sv=DATA/"supplemental/sv.xpt"
    if sv.exists():
        sdtm["sv"]=pd.read_sas(sv,format="xport",encoding="utf8")
        if not set(sdtm["sv"].USUBJID).issubset(set(sdtm["dm"].USUBJID)):
            raise ValueError("Supplemental SV contains subjects outside the cached DM universe.")
        if set(sdtm["sv"].STUDYID)!=set(sdtm["dm"].STUDYID):
            raise ValueError("Supplemental SV study IDs do not match cached DM.")
    # Target bytes are deliberately loaded only AFTER construction.
    conservative,conservative_evidence=rebuild_adsl(sdtm,spec["adsl"])
    rebuilt,evidence=rebuild_adsl(sdtm,spec["adsl"],mode="reference-compatible")
    adverse,adverse_evidence=rebuild_adae(sdtm,rebuilt,spec["adae"])
    survival,survival_evidence=rebuild_adtte(rebuilt,adverse,spec["adtte"])
    cibic,cibic_evidence=rebuild_cibic(sdtm,rebuilt,spec["adqscibc"])
    candidates={};candidate_errors={}
    builders={"adqsadas":rebuild_adqsadas,"adqsnpix":rebuild_adqsnpix,
              "adlbc":rebuild_adlbc,"adlbh":rebuild_adlbh,"advs":rebuild_advs}
    for name,builder in builders.items():
        try:
            candidates[name]=builder(sdtm,rebuilt,spec[name])
        except (ValueError,KeyError,TypeError) as error:
            candidate_errors[name]=f"{type(error).__name__}: {error}"
    targets={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in TARGETS}
    fields=compare_adsl(rebuilt,targets["adsl"],evidence)
    conservative_fields=compare_adsl(conservative,targets["adsl"],conservative_evidence)
    adverse_fields=compare_records(adverse,targets["adae"],adverse_evidence,["USUBJID","AESEQ"])
    survival_fields=compare_records(survival,targets["adtte"],survival_evidence,["USUBJID","PARAMCD"])
    cibic_fields=compare_cibic(cibic,targets["adqscibc"],cibic_evidence)
    accepted_cibic_rows=cibic_exception_rows(cibic,targets["adqscibc"])
    imputed=cibic.loc[cibic.DTYPE.eq("LOCF")].set_index(["USUBJID","AVISITN"])
    reference_imputed=targets["adqscibc"].loc[targets["adqscibc"].DTYPE.eq("LOCF")].set_index(["USUBJID","AVISITN"]).reindex(imputed.index)
    cibic_diagnostics=[
        dict(check="LOCF records compared",count=len(imputed),interpretation="SAP-selected observations carried forward."),
        dict(check="LOCF source-sequence differences",count=int(imputed.QSSEQ.ne(reference_imputed.QSSEQ).sum()),
             interpretation="Reference provenance differs from the SAP-selected observation. Do not silently substitute a different imputation algorithm."),
        dict(check="LOCF score differences",count=int((~np.isclose(imputed.AVAL,reference_imputed.AVAL,atol=1e-8,rtol=1e-10,equal_nan=True)).sum()),
             interpretation="Equal scores on this clean sample cannot establish equivalence when competing observations have different values."),
    ]
    checks={"adsl":fields,"adae":adverse_fields,"adtte":survival_fields,"adqscibc":cibic_fields}
    for name,(frame,proof) in candidates.items():
        keys=(["USUBJID","PARAMCD","VISITNUM","ADT","DTYPE","AVISITN"] if name.startswith("adqs")
              else ["USUBJID","PARAMCD","LBSEQ" if name.startswith("adlb") else "VSSEQ","AVISITN"])
        try:
            checks[name]=compare_bds(frame,targets[name],proof,name)
        except (ValueError,KeyError,TypeError) as error:
            candidate_errors[name]=f"Comparison blocked: {type(error).__name__}: {error}"
    mismatched=sum(r["status"]=="MISMATCH" for r in fields)
    unbuilt=sum(r["status"]=="NOT REBUILT" for r in fields)
    adsl_pass=not mismatched and not unbuilt
    convention_results=[{k:r[k] for k in ("variable","status","compared","mismatches")}
                        for r in fields if r["variable"] in {c["field"] for c in CONVENTIONS}]
    modes=[dict(mode=name,subjects=len(frame),targetFields=len(results),
                matchingFields=sum(r["status"]=="MATCH" for r in results),
                differingFields=sum(r["status"]!="MATCH" for r in results),
                differingCells=sum(r["mismatches"] or 0 for r in results),
                purpose=purpose)
           for name,frame,results,purpose in [
               ("Conservative",conservative,conservative_fields,"Missing BMI remains uncategorized; 365-day elapsed-duration convention."),
               ("Reference-compatible",rebuilt,fields,"Reference reproduction only; missing BMI categorized <25 with an explicit quality warning.")]]
    reference_issues=[]
    adsl_reference=targets["adsl"]
    inconsistent=adsl_reference.BMIBL.isna() & adsl_reference.BMIBLGR1.fillna("").ne("")
    for _,row in adsl_reference.loc[inconsistent].iterrows():
        reference_issues.append(dict(dataset="ADSL",subject=row.USUBJID,field="BMIBLGR1",
                                     finding=f"Reference BMI is missing but reference category is {row.BMIBLGR1}.",
                                     treatment="Quality warning persists in both modes. Conservative mode leaves category blank; reference-compatible mode reproduces <25 without endorsing clinical correctness."))
    coverage=[];dependencies=[]
    for name in TARGETS:
        defined=set(spec.get(name,{}));target=targets[name]
        results=checks.get(name)
        missing=sum(r["status"]=="NOT REBUILT" for r in results) if results else None
        different=sum(r["status"]=="MISMATCH" for r in results) if results else None
        coverage.append(dict(dataset=name.upper(),targetRows=len(target),targetColumns=len(target.columns),
                             matchingFields=sum(r["status"]=="MATCH" for r in results) if results else 0,
                             status=("PASSED" if not missing and not different else f"FAILED — {different} mismatched fields, {missing} not rebuilt") if results
                             else ("NOT REBUILT — implementation pending" if adsl_pass else "BLOCKED — upstream ADSL gate failed; not rebuilt"),
                             targetColumnsAbsentFromDefine=", ".join(sorted(set(target.columns)-defined))))
        if name=="adqscibc" and cibic_convention_passed(cibic_fields) and len(accepted_cibic_rows)==35:
            coverage[-1]["status"]="PASSED (SAP-Aligned Convention)"
            coverage[-1]["conventionVerified"]=True
        if name in candidate_errors:
            coverage[-1]["status"]="BLOCKED — "+candidate_errors[name]
        elif name in candidates:
            coverage[-1]["rebuiltRows"]=len(candidates[name][0])
        for variable,definition in spec.get(name,{}).items():
            refs=sorted(set(re.findall(r"\b([A-Z]{2,8})\.([A-Z][A-Z0-9]{1,7})\b",definition["comment"])))
            unavailable=[f"{d}.{v}" for d,v in refs if not d.startswith("AD") and (d.lower() not in sdtm or v not in sdtm[d.lower()].columns)]
            dependencies.append(dict(dataset=name.upper(),variable=variable,definition=definition["comment"],
                                     unavailableSources=", ".join(unavailable)))
    blockers=[
        ["Supplemental source status","Official SV and updated define added separately. Original cached sources preserved. SV-dependent treatment and population derivations now evaluated." if "sv" in sdtm else "SV unavailable; no substitution approved."],
        ["Documented compatibility interpretations","YEARSEDU→EDLEVEL supported by EDUCATION LEVEL / YEARS; ENDDT→RFENDT. Their target comparisons are reported independently, not assumed to pass."],
        ["Approved reconstruction experiments","Conservative conventions and reference-compatibility overrides are documented separately. Approval to test and target agreement do not authenticate original SAS logic."],
        ["Declared numeric precision","Numeric fields with SignificantDigits metadata use that decimal precision with deterministic round-half-up, fixed before target comparison; numerical comparison tolerances are unchanged."],
        ["Downstream scope","All nine complete ADaM targets must pass. Matching a subset of ADSL fields is not a successful clean rebuild."],
        ["Challenge gate","Neither development seed 20261120 nor held-out seed 20261121 has been executed or tuned."]
    ]
    blockers.append(["CIBIC+ provenance",f"{cibic_diagnostics[1]['count']} LOCF source-sequence differences; {cibic_diagnostics[2]['count']} LOCF score differences. SAP §8.2 requires imputation using targeted assessments; retain this mismatch rather than changing the algorithm to fit the reference."])
    blockers.append(["Confirmed CIBIC+ methodology",CIBIC_IMPUTATION_POLICY["status"]+" "+CIBIC_IMPUTATION_POLICY["gate"]])
    blockers.append(["ADVS end-of-treatment definition","SAP section 11.6 defines last visit on or before Week 24; the reference includes Week 26 EOT records. No exception has been authorized for ADVS."])
    blockers.append(["New candidate builders","ADQSADAS, ADQSNPIX, ADLBC, ADLBH and ADVS are implemented candidates, not validated derivations. Dataset-specific comparison sheets disclose record and field discrepancies."])
    blockers.extend([[f"Observed {r['variable']} mismatch",f"{r['mismatches']} subject values differ. {r['example']}"]
                     for r in fields if r["status"]=="MISMATCH"])
    guide=[]
    with pymupdf.open(DATA/"adam-dataguide.pdf") as doc:
        for page,text in enumerate(doc,1):
            guide.append(dict(page=page,text=text.get_text()))
    permitted=all_targets_passed(coverage)
    result=dict(status="PASSED" if permitted else "BLOCKED",pairedRunsPermitted=permitted,coverage=coverage,adslFields=fields,
                validationMode="reference-compatible",modeComparison=modes,
                conservativeAdslFields=conservative_fields,
                conservativeAdslGatePassed=all(r["status"]=="MATCH" for r in conservative_fields),
                adslGatePassed=adsl_pass,reconstructionConventions=CONVENTIONS,
                referenceCompatibilityConventions=REFERENCE_COMPATIBILITY_CONVENTIONS,
                adaeFields=adverse_fields,
                adtteFields=survival_fields,
                adqscibcFields=cibic_fields,
                cibicDiagnostics=cibic_diagnostics,
                cibicImputationPolicy=CIBIC_IMPUTATION_POLICY,
                acceptedCibicRows=accepted_cibic_rows,
                candidateComparisons={n:checks.get(n,[]) for n in builders},
                candidateErrors=candidate_errors,
                conventionResults=convention_results,referenceIssues=reference_issues,
                blockers=[dict(issue=k,evidence=v) for k,v in blockers],
                numericTolerance=dict(absolute=1e-8,relative=1e-10),
                sourceHashes=before,
                definitionSource=str(DATA/"supplemental/adam-define.xml") if (DATA/"supplemental/adam-define.xml").exists() else str(DATA/"adam-define.xml"),
                supplementalProvenance=json.loads((DATA/"supplemental/manifest.json").read_text()) if (DATA/"supplemental/manifest.json").exists() else [],
                targetUsage="Comparison only; target data are not passed into derivation functions.")
    assert all(digest(Path(p))==h for p,h in before.items()),"Cached sources changed"
    with pd.ExcelWriter(OUT/"ADaM_Clean_Rebuild_Validation.xlsx",engine="openpyxl") as writer:
        for name,rows in [("Clean_Validation_Gate",coverage),("ADSL_Field_Comparison",fields),
                          ("ADAE_Field_Comparison",adverse_fields),
                          ("ADTTE_Field_Comparison",survival_fields),
                          ("CIBIC_Field_Comparison",cibic_fields),
                          ("CIBIC_Diagnostics",cibic_diagnostics),
                          ("CIBIC_Methodology_Decision",[CIBIC_IMPUTATION_POLICY]),
                          ("CIBIC_Accepted_Rows",accepted_cibic_rows),
                          ("Mode_Comparison",modes),("Conservative_ADSL_Comparison",conservative_fields),
                          ("Reconstruction_Conventions",CONVENTIONS),
                          ("Reference_Compatibility",REFERENCE_COMPATIBILITY_CONVENTIONS),
                          ("Convention_Test_Results",convention_results),
                          ("Reference_Issues",reference_issues),
                          ("Definition_Source_Audit",dependencies),("Blocking_Findings",result["blockers"]),
                          ("Cached_Data_Guide",guide),
                          ("Input_Hashes",[dict(file=p,sha256=h) for p,h in before.items()])]:
            pd.DataFrame(rows).to_excel(writer,sheet_name=name,index=False)
            sheet=writer.sheets[name]
            sheet.freeze_panes="A2"
            sheet.auto_filter.ref=sheet.dimensions
            for cell in sheet[1]:
                cell.font=Font(bold=True,color="FFFFFF")
                cell.fill=PatternFill("solid",fgColor="245C58")
            for column in sheet.columns:
                index=column[0].column
                width=min(85,max(18,max(len(str(c.value or "")) for c in column)+2))
                sheet.column_dimensions[get_column_letter(index)].width=width
                for cell in column:
                    cell.alignment=Alignment(vertical="top",wrap_text=True)
        for name in builders:
            pd.DataFrame(checks.get(name,[{"status":"BLOCKED","reason":candidate_errors.get(name,"Not built")}])).to_excel(
                writer,sheet_name=name.upper()+"_Comparison",index=False)
    conservative.to_csv(OUT/"ADSL_Partial_Reconstruction.csv",index=False)
    conservative.to_csv(OUT/"ADSL_Conservative_Reconstruction.csv",index=False)
    rebuilt.to_csv(OUT/"ADSL_Reference_Compatible_Reconstruction.csv",index=False)
    adverse.to_csv(OUT/"ADAE_Reconstruction.csv",index=False)
    survival.to_csv(OUT/"ADTTE_Reconstruction.csv",index=False)
    cibic.to_csv(OUT/"ADQSCIBC_Reconstruction.csv",index=False)
    for name,(frame,_) in candidates.items():
        frame.to_csv(OUT/(name.upper()+"_Candidate_Reconstruction.csv"),index=False)
    (OUT/"clean_rebuild_validation.json").write_text(json.dumps(result,indent=2))
    print(pd.DataFrame(coverage).to_string(index=False))
    print("ADSL field status:",pd.Series([x["status"] for x in fields]).value_counts().to_dict())
    print(pd.DataFrame(modes).to_string(index=False))
    print("PASSED: all nine targets validated." if permitted else "BLOCKED: all nine targets must pass before paired challenges; prior manuscript outputs unchanged.")
    return 0 if permitted else 2

if __name__=="__main__":
    raise SystemExit(main())
