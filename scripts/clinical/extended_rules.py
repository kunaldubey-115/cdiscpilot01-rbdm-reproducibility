"""Additional explicit XPT checks; never replace unavailable predicates with generic missingness."""
import numpy as np
import pandas as pd

def date(s):
    return pd.to_datetime(s.astype(str).str[:10], format="%Y-%m-%d", errors="coerce")

def extra_check(number, d, data):
    from critical_rule_checks import check
    checked=check(number,d,data)
    if checked is not None:return checked
    if number in (16,23,26,67,82):
        explanations={
            16:"SAP section 10 (CSR p429) explicitly permits off-drug efficacy assessments. Do not truncate QS at last exposure; full reconciliation needs separately specified tolerances and event scope.",
            23:"Start/end ordering is testable, but a single fixed treatment-window cutoff is not established here; do not use rederived TRTSDT/TRTEDT from those same EX dates as an independent validator.",
            26:"SAP section 9.3 (CSR p429): treatment compliance will not be provided. EX dose totals are not a validated patch-application compliance denominator.",
            67:"SAP section 8.3 (CSR p427) defines >1.5*ULN/<0.5*LLN analysis thresholds, not a universal Grade 3/4 scale. Do not equate these with the workbook's >3*ULN example.",
            82:"SAP section 11.6 (CSR p432) defines vital-sign summaries, not universal physiologic outlier bounds. Completeness can be tested separately; clinical limits remain unspecified."
        }
        return d,None,explanations[number]
    note = ""
    dm=data["dm"].set_index("USUBJID")
    if number == 5:
        consent=date(d.RFICDTC)
        screening=date(d.DMDTC)
        dose=date(d.RFSTDTC)
        return d, consent.isna() | (screening.notna() & consent.gt(screening)) | (dose.notna() & consent.gt(dose)), "Screening uses DM.DMDTC; comparisons use calendar dates, not imputed partial dates."
    if number == 6:
        ds=data["ds"]; ae=data["ae"]
        dsdead=set(ds.loc[ds.DSDECOD.eq("DEATH"),"USUBJID"])
        aedead=set(ae.loc[ae.AEOUT.eq("FATAL"),"USUBJID"])
        flagged=d.DTHFL.eq("Y")
        mask=flagged.ne(d.USUBJID.isin(dsdead)) | flagged.ne(d.USUBJID.isin(aedead))
        death_dates=ae.loc[ae.AEOUT.eq("FATAL")].groupby("USUBJID").AEENDTC.max()
        ds_dates=ds.loc[ds.DSDECOD.eq("DEATH")].groupby("USUBJID").DSSTDTC.max()
        mask |= flagged & (date(d.DTHDTC).isna() | date(d.DTHDTC).ne(date(d.USUBJID.map(death_dates))) | date(d.DTHDTC).ne(date(d.USUBJID.map(ds_dates))))
        return d,mask,"Fatal AE end date and death disposition date reconciled to DM.DTHDTC."
    if number == 24:
        expected=d.USUBJID.map(dm.ACTARM).map({"Placebo":0,"Xanomeline Low Dose":54,"Xanomeline High Dose":81})
        return d,expected.isna() | ~np.isclose(d.EXDOSE,expected,atol=1e-8,rtol=0),"Workbook's fixed-dose predicate; protocol titration can produce legitimate flags. SAS near-zero placebo doses normalized by tolerance."
    if number == 25:
        last=d.groupby("USUBJID",as_index=False).EXENDTC.max()
        ds=data["ds"]; ds=ds[ds.DSCAT.eq("DISPOSITION EVENT")]
        end=ds.groupby("USUBJID").DSSTDTC.max()
        delta=(date(last.EXENDTC)-date(last.USUBJID.map(end))).dt.days
        return last,delta.isna() | delta.abs().gt(1),"One comparison per exposed subject; final DISPOSITION EVENT date, tolerance ±1 calendar day."
    if number == 35:
        return d,date(d.AESTDTC).isna() | date(d.USUBJID.map(dm.RFSTDTC)).isna(),"Flags incomplete or invalid onset/reference dates requiring imputation; does not itself classify pre-treatment AEs as errors."
    if number == 41:
        d=d[d.AEOUT.eq("FATAL")].copy()
        return d, d.AESDTH.ne("Y") | d.USUBJID.map(dm.DTHFL).ne("Y") | date(d.AEENDTC).isna() | date(d.AEENDTC).ne(date(d.USUBJID.map(dm.DTHDTC))),"Fatal AE end date compared to DM death date."
    if number == 54:
        ids=data["adsl"].loc[data["adsl"].EFFFL.eq("Y"),"USUBJID"]
        expected=pd.MultiIndex.from_product([ids,[8,16,24]],names=["USUBJID","AVISITN"]).to_frame(index=False)
        a=data["adqscibc"]
        a=a[a.PARAMCD.eq("CIBICVAL") & a.ANL01FL.eq("Y") & a.AVISITN.isin([8,16,24])]
        out=expected.merge(a[["USUBJID","AVISITN","AVAL"]],on=["USUBJID","AVISITN"],how="left",validate="one_to_one")
        return out,~out.AVAL.between(1,7),"Expected subject × visit grid from efficacy ADSL joined to analysis-selected CIBIC+ XPT. Includes LOCF; this tests derived availability, not raw visit completion."
    if number == 57:
        a=data["adsl"]
        return a,~a.MMSETOT.between(10,24),"Screening MMSE as stored in ADSL; includes all randomized subjects, not a rederivation from questionnaire items."
    if number == 58:
        a=data["adqsadas"]
        a=a[a.PARAMCD.eq("ACTOT") & a.ANL01FL.eq("Y") & a.DTYPE.ne("LOCF")].sort_values(["USUBJID","AVISITN"])
        delta=a.groupby("USUBJID").AVAL.diff().abs()
        return a,delta.ge(15),"Observed analysis-selected ADAS-Cog total changes between adjacent visits; first visit has no predecessor."
    if number == 121:
        char=pd.to_numeric(d.SCSTRESC,errors="coerce")
        return d, char.isna() | d.SCSTRESN.isna() | ~np.isclose(char,d.SCSTRESN,atol=1e-8,rtol=0),"Numeric echo for the EDLEVEL characteristic actually present in this source."
    return d,None,note
