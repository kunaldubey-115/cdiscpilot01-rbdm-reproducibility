"""Regenerate scoped Section 14 summaries and audit every output cell.

This verifies frozen-ADaM summary dependencies, not SDTM-to-ADaM derivation.
No unverified SDTM field is authorized for query suppression by this test.
"""
import itertools
import numpy as np
import pandas as pd
from scipy.stats import f_oneway, chi2_contingency

METADATA = {"adsl": ["SUBJID"], "adqsnpix": ["AWRANGE", "AWU"],
            "adlbc": ["SUBJID"], "adlbh": ["SUBJID"], "advs": ["VISIT"]}

def numeric_rows(d, group, variables):
    rows = []
    for key, g in d.groupby(group, dropna=False, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        for variable in variables:
            s = pd.to_numeric(g[variable], errors="coerce").dropna()
            for stat, value in [("n",len(s)),("mean",s.mean()),("sd",s.std()),("median",s.median()),("min",s.min()),("max",s.max())]:
                rows.append([*key, variable,stat,None if pd.isna(value) else float(value)])
    return pd.DataFrame(rows,columns=[*group,"Variable","Statistic","Value"])

def demographic(d):
    x = d[d.ITTFL.eq("Y")].copy()
    x["TRTP"] = x.TRT01P
    total = x.copy()
    total["TRTP"] = "Total"
    x = pd.concat([x,total],ignore_index=True)
    result = numeric_rows(x,["TRTP"],["AGE","MMSETOT","EDUCLVL","HEIGHTBL","WEIGHTBL","BMIBL","DURDIS"])
    rows=[]
    for arm,g in x.groupby("TRTP",sort=True):
        for variable in ["AGEGR1","SEX","RACE","DURDSGR1","BMIBLGR1"]:
            for value in sorted(x[variable].fillna("Missing").unique()):
                count=int(g[variable].fillna("Missing").eq(value).sum())
                rows.extend([[arm,variable,f"{value}: n",count],[arm,variable,f"{value}: %",100*count/len(g)]])
    population=x[x.TRTP.ne("Total")]
    for variable in ["AGE","MMSETOT","EDUCLVL","HEIGHTBL","WEIGHTBL","BMIBL","DURDIS"]:
        values=[pd.to_numeric(g[variable],errors="coerce").dropna().to_numpy() for _,g in population.groupby("TRTP")]
        rows.append(["All treatments",variable,"ANOVA p",float(f_oneway(*values).pvalue)])
    for variable in ["AGEGR1","SEX","RACE","DURDSGR1","BMIBLGR1"]:
        tab=pd.crosstab(population.TRTP,population[variable])
        rows.append(["All treatments",variable,"Pearson chi-square p",float(chi2_contingency(tab,correction=False).pvalue)])
    return pd.concat([result,pd.DataFrame(rows,columns=result.columns)],ignore_index=True)

def npi(d):
    x=d[d.EFFFL.eq("Y") & d.ANL01FL.eq("Y") & d.PARAMCD.isin(["NPTOT","NPTOTMN"])].copy()
    x["AVISIT"]=x.AVISIT.str.strip()
    return numeric_rows(x,["TRTP","PARAMCD","AVISIT","DTYPE"],["AVAL","BASE","CHG"])

def lab(d):
    # define.xml: lab ANL01FL selects the maximum abnormality, NOT per-visit records.
    # Per-visit shift tables therefore must not restrict ANL01FL to Y.
    x=d[d.SAFFL.eq("Y") & ~d.PARAMCD.str.startswith("_")].copy()
    x["AVISIT"]=x.AVISIT.str.strip()
    x=x[~x.AVISIT.isin(["Baseline","","."])]
    rows=[]
    for key,g in x.groupby(["TRTP","PARAMCD","AVISIT"],sort=True):
        for b,a in itertools.product(["L","N","H","Missing"],repeat=2):
            bval=g.BNRIND.replace("", "Missing").fillna("Missing")
            aval=g.ANRIND.replace("", "Missing").fillna("Missing")
            rows.append([*key,b,a,int(g.loc[bval.eq(b)&aval.eq(a),"USUBJID"].nunique())])
    return pd.DataFrame(rows,columns=["TRTP","PARAMCD","AVISIT","Baseline category","Analysis category","Subjects"])

def vital(d):
    x=d[d.SAFFL.eq("Y") & d.ANL01FL.eq("Y")].copy()
    x=x[x.AVISIT.isin(["Baseline","Week 24","End of Treatment"])]
    return numeric_rows(x,["TRTP","PARAMCD","ATPT","AVISIT"],["AVAL","BASE","CHG"])

BUILDERS = {"adsl":demographic,"adqsnpix":npi,"adlbc":lab,"adlbh":lab,"advs":vital}
NAMES = {"adsl":"14-2.01 Demographic descriptive summaries",
         "adqsnpix":"14-3.10 NPI-X descriptive summaries (not 14-3.03)",
         "adlbc":"14-6.04 Chemistry shift summaries","adlbh":"14-6.04 Hematology shift summaries",
         "advs":"14-7.01/02 Vital values and change summaries"}

def compare_cells(before, after):
    if not before.columns.equals(after.columns) or before.shape != after.shape:
        raise ValueError("Table structure changed; cannot silently compare misaligned cells.")
    equal = before.eq(after) | (before.isna() & after.isna())
    rows=[]
    for i,col in zip(*np.where(~equal.to_numpy())):
        rows.append([int(i)+2,str(before.columns[col]),str(before.iat[i,col]),str(after.iat[i,col])])
    return rows

def audit_tables(data, path):
    rng=np.random.default_rng(20261117)
    audits=[]
    with pd.ExcelWriter(path,engine="openpyxl") as writer:
        for name,builder in BUILDERS.items():
            original=data[name]
            changed=original.copy(deep=True)
            modified=0
            for col in METADATA[name]:
                # Explicitly scoped summary-only non-input metadata, not globally approved Tier 3.
                mask=rng.random(len(changed)) < .15
                modified+=int(mask.sum())
                changed.loc[mask,col]="PERTURBED_METADATA"
            assert modified > 0
            before,after=builder(original),builder(changed)
            diffs=compare_cells(before,after)
            # Positive control ensures a real downstream value change is detectable.
            control_source=original.copy(deep=True)
            if name in ("adlbc","adlbh"):
                control_source["ANRIND"]=control_source.ANRIND.replace({"N":"H","H":"L","L":"N"})
            else:
                variable="AGE" if name=="adsl" else "AVAL"
                control_source[variable]=control_source[variable]+1
            control=builder(control_source)
            control_diffs=compare_cells(before,control)
            assert len(control_diffs) >= 1
            before.to_excel(writer,sheet_name=name+"_before",index=False)
            after.to_excel(writer,sheet_name=name+"_after",index=False)
            pd.DataFrame(diffs,columns=["Excel row","Column","Before","After"]).to_excel(writer,sheet_name=name+"_diff",index=False)
            pd.DataFrame(control_diffs,columns=["Excel row","Column","Before","Positive control"]).to_excel(writer,sheet_name=name+"_positive",index=False)
            audits.append(dict(name=NAMES[name],cells=int(before.size),differences=len(diffs),changedMetadataCells=modified,
                scope=f"Cell mismatch rate: {100*len(diffs)/before.size:.4f}%. 15% Bernoulli perturbation of "+", ".join(METADATA[name])+
                "; all cells compared exactly with paired missing values equal. Positive control passed. Frozen-ADaM summary test only; not a full published-table reproduction or SDTM derivation validation."))
        pd.DataFrame(audits).to_excel(writer,sheet_name="Audit_summary",index=False)
        pd.DataFrame([
            ["Demographics","ITTFL Y; treatment and Total; numeric summaries; age/sex/race/disease-duration/BMI categories; ANOVA and Pearson chi-square p-values. Unrounded cells, not a typeset facsimile."],
            ["NPI-X","EFFFL Y, ANL01FL Y, NPTOT/NPTOTMN; visits and DTYPE separated. The official NPI-X summary is 14-3.10; 14-3.03 is ADAS-Cog Week 8."],
            ["Labs","SAFFL Y; non-underscore parameters, post-baseline visits; distinct subjects in BNRIND × ANRIND categories, including missing. Do NOT filter ANL01FL: define.xml says this selects maximum abnormality rather than per-visit records. Published typesetting not reproduced."],
            ["Vitals","SAFFL Y, ANL01FL Y; baseline, Week24 and EOT by parameter and time point. ADVS lacks ANRIND/BNRIND; report values and changes, not invented clinical-normality thresholds."],
            ["Suppression boundary","Perturbed columns are non-inputs to these summary functions only. This does not authorize suppressing them upstream or verify all CSR Section 14 outputs."]
        ],columns=["Scope","Specification"]).to_excel(writer,sheet_name="Scope_and_methods",index=False)
    return audits
