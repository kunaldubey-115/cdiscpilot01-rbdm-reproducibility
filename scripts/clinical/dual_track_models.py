"""Clean cross-track model comparison, never a paired challenge result."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.duration.survfunc import SurvfuncRight
from clinical_statistics import cohort, FORMULA

def model_summary(data):
    rows=[]
    adas=cohort(data["adqsadas"],"ACTOT")
    cibic=cohort(data["adqscibc"],"CIBICVAL")
    models=[
        ("ADAS three-arm ANCOVA",FORMULA,adas),
        ("CIBIC three-arm ANOVA",'AVAL ~ C(TRTP, Treatment(reference="Placebo")) + C(SITEGR1)',cibic),
        ("CIBIC continuous-dose trend",'AVAL ~ TRTPN + C(SITEGR1)',cibic),
    ]
    for name,formula,frame in models:
        fit=smf.ols(formula,frame,missing="raise").fit()
        rows.append([name,"N","subjects",float(fit.nobs)])
        for term in fit.params.index:
            for stat,values in [("estimate",fit.params),("SE",fit.bse),("p",fit.pvalues)]:
                rows.append([name,term,stat,float(values[term])])
    for arm,g in data["adtte"].groupby("TRTP"):
        survival=SurvfuncRight(g.AVAL,1-g.CNSR)
        rows.append(["TTDE Kaplan-Meier",arm,"N",float(len(g))])
        rows.append(["TTDE Kaplan-Meier",arm,"events",float((1-g.CNSR).sum())])
        for time,probability in zip(survival.surv_times,survival.surv_prob):
            rows.append(["TTDE Kaplan-Meier",arm,f"survival at day {time:g}",float(probability)])
    return pd.DataFrame(rows,columns=["Model","Term","Statistic","Value"])

def compare_models(reference,sap):
    keys=["Model","Term","Statistic"]
    a=model_summary(reference).set_index(keys)
    b=model_summary(sap).set_index(keys)
    joined=a.join(b,how="outer",lsuffix="_reference",rsuffix="_sap")
    joined["Status"]=np.where(np.isclose(joined.Value_reference,joined.Value_sap,atol=1e-8,rtol=1e-10,equal_nan=True),"MATCH","DIFFERENCE")
    joined.loc[~joined.index.isin(a.index) | ~joined.index.isin(b.index),"Status"]="MISSING MODEL CELL"
    return joined.reset_index()
