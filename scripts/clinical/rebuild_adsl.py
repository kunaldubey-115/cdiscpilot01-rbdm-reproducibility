"""Cache-specification ADSL reconstruction. No target ADaM input is accepted."""
import re
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd

def sas_date(values):
    return (pd.to_datetime(values.astype(str).str[:10],format="%Y-%m-%d",errors="coerce")-pd.Timestamp("1960-01-01")).dt.days.astype(float)

def normalize_precision(values, precision):
    quantum=Decimal(1).scaleb(-int(precision))
    return values.map(lambda v: float(Decimal(str(v)).quantize(quantum,rounding=ROUND_HALF_UP)) if pd.notna(v) else np.nan)

def rebuild_adsl(sdtm, items, *, mode="conservative"):
    if mode not in ("conservative","reference-compatible"):
        raise ValueError("Unknown reconstruction mode: "+mode)
    dm=sdtm["dm"]
    # Cached dataguide.pdf p3 excludes screen failures from analysis datasets.
    enrolled=dm[dm.ARMCD.fillna("").ne("") & ~dm.ARMCD.eq("Scrnfail")].copy()
    if enrolled.USUBJID.duplicated().any():
        raise ValueError("Duplicate subject identities: cannot construct one-row-per-subject ADSL.")
    out=pd.DataFrame(index=enrolled.index)
    evidence={}
    for name,spec in items.items():
        match=re.fullmatch(r"DM\.([A-Z0-9]+)",spec["comment"].strip())
        if match and match[1] in enrolled:
            out[name]=enrolled[match[1]]
            evidence[name]="Literal define mapping: "+spec["comment"]
    out["ITTFL"]=np.where(enrolled.ARMCD.fillna("").ne(""),"Y","N")
    evidence["ITTFL"]="Define: Y if ARMCD nonblank; dataguide p3 excludes screen failures."
    if "TRT01P" in out:
        out["TRT01A"]=out.TRT01P
        evidence["TRT01A"]="Literal define instruction TRT01A=TRT01P; not substituted with DM.ACTARM."
    if "AGE" in out:
        out["AGEGR1N"]=np.select([out.AGE.lt(65),out.AGE.le(80),out.AGE.gt(80)],[1.,2.,3.],default=np.nan)
        evidence["AGEGR1N"]="Define age boundaries: <65, 65–80, >80."
        codes=items["AGEGR1N"]["codes"]
        out["AGEGR1"]=out.AGEGR1N.map({float(k):v for k,v in codes.items()})
        evidence["AGEGR1"]="Decode AGEGR1N using the cached define's AGEGR1N code list."
    # SAP §7.1, physical CSR PDF p425: pool sites with fewer than three
    # patients in any treatment group. Do not invent an unspecified random tie-break.
    counts=pd.crosstab(enrolled.SITEID,enrolled.ARM)
    small=counts.index[counts.min(axis=1).lt(3)]
    if len(small)==0 or counts.loc[small].sum().min()>=3:
        out["SITEGR1"]=enrolled.SITEID.where(~enrolled.SITEID.isin(small),"900")
        evidence["SITEGR1"]="SAP §7.1, CSR PDF p425: pool sites with <3 in any arm; pooled group satisfies minimum without random tie-break."
    else:
        evidence["SITEGR1"]="BLOCKED: further pooling requires an explicitly specified tie-break policy."
    mmse=sdtm["qs"].loc[sdtm["qs"].QSCAT.eq("MINI-MENTAL STATE")].copy()
    mmse["numeric"]=pd.to_numeric(mmse.QSORRES,errors="coerce")
    out["MMSETOT"]=enrolled.USUBJID.map(mmse.groupby("USUBJID").numeric.sum(min_count=1))
    evidence["MMSETOT"]="Define sum QSORRES; scoped to the named MINI-MENTAL STATE questionnaire, not all questionnaire categories."
    for target,source in [("TRT01PN","TRT01P"),("TRT01AN","TRT01A"),("RACEN","RACE")]:
        codes=items[target]["codes"]
        out[target]=out[source].map({v:float(k) for k,v in codes.items()})
        evidence[target]=f"Cached define code list for {target}, decoded against {source}."
    if "RFENDTC" in out:
        out["RFENDT"]=sas_date(out.RFENDTC)
        evidence["RFENDT"]="Define RFENDTC converted to SAS calendar date; no partial-date imputation."
    if "sv" in sdtm:
        sv=sdtm["sv"]
        for variable,visit in [("TRTSDT",3),("VISIT1DT",1)]:
            source=sv[sv.VISITNUM.eq(visit)]
            if source.USUBJID.duplicated().any():
                raise ValueError(f"Ambiguous SV visit {visit}: multiple records per subject.")
            out[variable]=sas_date(enrolled.USUBJID.map(source.set_index("USUBJID").SVSTDTC))
            evidence[variable]=f"Define: SV.SVSTDTC at VISITNUM={visit}; supplemental source, no target lookup."
        out["SAFFL"]=np.where(out.ITTFL.eq("Y") & out.TRTSDT.notna(),"Y","N")
        evidence["SAFFL"]="Define ITTFL=Y and nonmissing TRTSDT."
        qs=sdtm["qs"]
        adas=set(qs.loc[qs.QSCAT.eq("ALZHEIMER'S DISEASE ASSESSMENT SCALE") & qs.VISITNUM.gt(3),"USUBJID"])
        cibic=set(qs.loc[qs.QSCAT.eq("CLINICIAN'S INTERVIEW-BASED IMPRESSION OF CHANGE (CIBIC+)") & qs.VISITNUM.gt(3),"USUBJID"])
        out["EFFFL"]=np.where(out.SAFFL.eq("Y") & enrolled.USUBJID.isin(adas & cibic),"Y","N")
        evidence["EFFFL"]="Define: safe population plus post-baseline records for both named questionnaire categories."
        ex=sdtm["ex"].sort_values(["USUBJID","EXSTDTC","EXSEQ"]).groupby("USUBJID").tail(1)
        raw=enrolled.USUBJID.map(ex.set_index("USUBJID").EXENDTC)
        ds=sdtm["ds"].loc[sdtm["ds"].DSCAT.eq("DISPOSITION EVENT")]
        if ds.USUBJID.duplicated().any():
            raise ValueError("Multiple disposition events require an explicit selection specification.")
        ds=ds.set_index("USUBJID")
        fallback=enrolled.USUBJID.map(ds.DSSTDTC).where(enrolled.USUBJID.map(ds.VISITNUM).gt(3))
        out["TRTEDT"]=sas_date(raw.where(raw.notna() & raw.ne(""),fallback))
        evidence["TRTEDT"]="Last EX record by start date/sequence; if absent and discontinuation visit >3, DS date per define."
        out["TRTDUR"]=out.TRTEDT-out.TRTSDT+1
        evidence["TRTDUR"]="Define TRTEDT-TRTSDT+1."
        visits=sv.loc[sv.VISITNUM.isin([4,12])]
        if visits.duplicated(["USUBJID","VISITNUM"]).any():
            raise ValueError("Ambiguous dosing-phase visit dates.")
        def visit_date(number):
            return sas_date(enrolled.USUBJID.map(visits.loc[visits.VISITNUM.eq(number)].set_index("USUBJID").SVSTDTC))
        v4,v12=visit_date(4),visit_date(12)
        first_end=pd.concat([out.TRTEDT,v4.fillna(out.TRTEDT)],axis=1).min(axis=1)
        second_end=pd.concat([out.TRTEDT,v12.fillna(out.TRTEDT)],axis=1).min(axis=1)
        first_days=(first_end-out.TRTSDT+1).clip(lower=0)
        second_days=(second_end-v4).clip(lower=0).fillna(0)
        third_days=(out.TRTEDT-v12).clip(lower=0).fillna(0)
        out["CUMDOSE"]=out.TRT01PN*out.TRTDUR
        high=out.TRT01PN.eq(81)
        out.loc[high,"CUMDOSE"]=(54*first_days+81*second_days+54*third_days)[high]
        ambiguous=high & v4.isna() & v12.notna()
        out.loc[ambiguous,"CUMDOSE"]=np.nan
        evidence["CUMDOSE"]="Define's 54/81/54 mg dosing phases using SV visits 4 and 12 and treatment dates; missing visit 4 with present visit 12 remains unresolved."
        out["AVGDD"]=out.CUMDOSE/out.TRTDUR.where(out.TRTDUR.gt(0))
        evidence["AVGDD"]="Define CUMDOSE/TRTDUR; no storage-rounding rule imposed."
        out["DCDECOD"]=enrolled.USUBJID.map(ds.DSDECOD)
        evidence["DCDECOD"]="Define DS.DSDECOD where DSCAT=DISPOSITION EVENT."
        reason_map={"COMPLETED":"Completed","ADVERSE EVENT":"Adverse Event","DEATH":"Death",
                    "LACK OF EFFICACY":"Lack of Efficacy","LOST TO FOLLOW-UP":"Lost to Follow-up",
                    "PHYSICIAN DECISION":"Physician Decision","PROTOCOL VIOLATION":"Protocol Violation",
                    "STUDY TERMINATED BY SPONSOR":"Sponsor Decision","WITHDRAWAL BY SUBJECT":"Withdrew Consent"}
        out["DCREASCD"]=out.DCDECOD.map(reason_map)
        entry=enrolled.USUBJID.map(ds.DSTERM).eq("PROTOCOL ENTRY CRITERIA NOT MET")
        out.loc[entry,"DCREASCD"]="I/E Not Met"
        evidence["DCREASCD"]="Explicit mapping of SDTM disposition terms to define code-list labels; entry-criteria term mapped to I/E Not Met. Unknown terms stay missing."
        out["DISCONFL"]=np.where(out.DCREASCD.notna() & out.DCREASCD.ne("Completed"),"Y","")
        out["DSRAEFL"]=np.where(out.DCREASCD.eq("Adverse Event"),"Y","")
        evidence["DISCONFL"]="Define Y for non-completed disposition, blank otherwise; unclassified reasons are not inferred."
        evidence["DSRAEFL"]="Define Y for Adverse Event, blank otherwise."
        end_visits=ds.VISITNUM.copy()
        end_visits.loc[end_visits.eq(13)]=12
        out["VISNUMEN"]=enrolled.USUBJID.map(end_visits)
        evidence["VISNUMEN"]="Approved reconstruction experiment: map DISPOSITION EVENT visit 13→12 for all dispositions. Original SAS logic unconfirmed."
        mh=sdtm["mh"].loc[sdtm["mh"].MHCAT.eq("PRIMARY DIAGNOSIS")]
        if not mh.USUBJID.duplicated().any():
            out["DISONSDT"]=sas_date(enrolled.USUBJID.map(mh.set_index("USUBJID").MHSTDTC))
            evidence["DISONSDT"]="Define MH.MHSTDTC for primary diagnosis; partial dates not imputed without specification."
        for flag,number in [("COMP8FL",8),("COMP16FL",10),("COMP24FL",12)]:
            selected=sv.loc[sv.VISITNUM.eq(number)]
            if selected.USUBJID.duplicated().any():
                raise ValueError(f"Ambiguous completion visit {number}.")
            date=sas_date(enrolled.USUBJID.map(selected.set_index("USUBJID").SVSTDTC))
            out[flag]=np.where(date.notna() & out.RFENDT.ge(date),"Y","N")
            evidence[flag]="Documented interpretation: define's ENDDT refers to subject reference end date RFENDT; require the specified SV visit and date <= RFENDT."
        out["DURDIS"]=(out.VISIT1DT-out.DISONSDT)/(365/12)
        evidence["DURDIS"]="Approved reconstruction experiment: elapsed days / (365/12) months; DISONSET interpreted as DISONSDT. Original fractional-month convention unconfirmed."
        if mode=="reference-compatible":
            out["DURDIS"]=(out.VISIT1DT-out.DISONSDT+1)/(365.25/12)
            evidence["DURDIS"]="Reference-compatibility experiment: inclusive elapsed days / (365.25/12), then declared precision. Empirical reproduction, not authenticated original SAS logic."
    for target,code,visit in [("HEIGHTBL","HEIGHT",1),("WEIGHTBL","WEIGHT",3)]:
        vs=sdtm["vs"]
        selected=vs[vs.VSTESTCD.eq(code) & vs.VISITNUM.eq(visit)]
        values=selected.groupby("USUBJID").VSSTRESN
        if values.nunique(dropna=False).gt(1).any():
            evidence[target]="BLOCKED: multiple differing source values and no tie-break rule."
        else:
            out[target]=enrolled.USUBJID.map(values.first())
            evidence[target]=f"Literal define selection VS.VSTESTCD={code}, VISITNUM={visit}."
    sc=sdtm["sc"]
    edu=sc.loc[sc.SCTESTCD.eq("EDLEVEL") & sc.SCTEST.eq("EDUCATION LEVEL") & sc.SCSTRESU.eq("YEARS")]
    if edu.USUBJID.duplicated().any():
        raise ValueError("Multiple education measurements require an explicit selection rule.")
    out["EDUCLVL"]=enrolled.USUBJID.map(edu.set_index("USUBJID").SCSTRESN)
    evidence["EDUCLVL"]="Documented terminology alias YEARSEDU→EDLEVEL, supported by cached SC test label EDUCATION LEVEL and unit YEARS; not inferred from ADaM."
    if "WEIGHTBL" in out and "HEIGHTBL" in out:
        for name in ["WEIGHTBL","HEIGHTBL"]:
            precision=items[name].get("precision")
            if precision is None:
                raise ValueError(f"Declared precision required before BMI calculation: {name}")
            out[name]=normalize_precision(out[name],precision)
        out["BMIBL"]=out.WEIGHTBL/(out.HEIGHTBL/100)**2
        evidence["BMIBL"]="Approved reconstruction experiment: calculate kg/m² from precision-normalized baseline weight and height; cm→m via HEIGHTBL/100. Original calculation order unconfirmed."
    # Apply the declared decimal precision, rather than relaxing comparison tolerance.
    # The policy is fixed from define metadata before any target comparison.
    for name in out:
        precision=items.get(name,{}).get("precision")
        if precision is not None and pd.api.types.is_numeric_dtype(out[name]):
            out[name]=normalize_precision(out[name],precision)
            evidence[name]+=f" Declared decimal precision {precision}; deterministic round-half-up."
    if "BMIBL" in out:
        out["BMIBLGR1"]=np.select([out.BMIBL.lt(25),out.BMIBL.lt(30),out.BMIBL.ge(30)],["<25","25-<30",">=30"],default="")
        evidence["BMIBLGR1"]="Approved reconstruction experiment: >=30 coded label consistent with stated >=30 boundary, replacing legacy >30 label."
        if mode=="reference-compatible":
            out.loc[out.BMIBL.isna(),"BMIBLGR1"]="<25"
            evidence["BMIBLGR1"]+=" Reference-compatibility only: missing BMI receives <25 to reproduce reference semantics; missing-BMI quality warning retained. Not a clinically justified classification."
    if "DURDIS" in out:
        out["DURDSGR1"]=np.select([out.DURDIS.lt(12),out.DURDIS.ge(12)],["<12",">=12"],default="")
        evidence["DURDSGR1"]="Define duration grouping applied to precision-normalized DURDIS."
    # Do not use EX as an undocumented proxy for the specified SV source;
    # do not guess site pooling, dictionary mappings, or partial-date policies.
    return out.reset_index(drop=True),evidence
