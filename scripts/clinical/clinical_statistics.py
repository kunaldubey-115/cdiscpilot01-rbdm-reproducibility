"""Reproducible fixed-data error-injection sensitivity, not prospective power."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import t, nct, ttest_ind
from scipy.optimize import brentq
from statsmodels.stats.proportion import proportion_confint

FORMULA = 'CHG ~ C(TRTP, Treatment(reference="Placebo")) + C(SITEGR1) + BASE'
TERM = 'C(TRTP, Treatment(reference="Placebo"))[T.Xanomeline High Dose]'

def cohort(d, param, two_arm=False):
    x = d[(d.PARAMCD == param) & (d.AVISIT == "Week 24") & (d.EFFFL == "Y") & (d.ANL01FL == "Y")].copy()
    if two_arm:
        x = x[x.TRTP.isin(["Placebo", "Xanomeline High Dose"])]
    if x.USUBJID.duplicated().any():
        raise ValueError("Duplicate Week 24 analysis records; cannot fit independent-subject model.")
    return x

def powered_simulation(iterations=1000):
    """Independent synthetic superiority trials; never substitute for pilot-study evidence."""
    n, alpha, sigma, seed = 100, .05, 1.0, 20261116
    df = 2*n-2
    critical = t.ppf(1-alpha/2, df)
    def power(effect):
        nc = effect / (sigma*np.sqrt(2/n))
        return nct.sf(critical, df, nc) + nct.cdf(-critical, df, nc)
    effect = float(brentq(lambda e: power(e)-.8, .01, 2))
    rng = np.random.default_rng(seed)
    clean = rng.normal(0, sigma, (iterations, 2*n))
    clean[:, n:] -= effect
    mask = rng.random(clean.shape)
    noise = rng.normal(0, 2*sigma, clean.shape)
    results = []
    for rate in [0,.01,.02,.05,.1,.15]:
        dirty = clean + (mask < rate)*noise
        p = ttest_ind(dirty[:,:n], dirty[:,n:], axis=1, equal_var=True).pvalue
        rejected = int((p < alpha).sum())
        lo, hi = proportion_confint(rejected, iterations, method="wilson")
        results.append(dict(errorRate=100*rate, power=100*rejected/iterations,
                            lower=100*float(lo), upper=100*float(hi), iterations=iterations))
    return dict(targetPower=.8, theoreticalCleanPower=float(power(effect)), nPerArm=n, effect=effect,
                residualSD=sigma, alpha=alpha, seed=seed, noiseSD=2*sigma,
                model="Two-sided equal-variance two-sample t-test; normal independent outcomes; 100 subjects per arm",
                interpretation="Synthetic design with 80% theoretical clean power, not fitted CDISCPILOT01 power. Gaussian contamination SD=2 residual SD is an explicit illustrative assumption."), results

def analyse(data, iterations=1000):
    all3 = cohort(data["adqsadas"], "ACTOT", False)
    x = cohort(data["adqsadas"], "ACTOT")
    fit = smf.ols(FORMULA, x).fit()
    published = smf.ols(FORMULA, all3).fit()
    delta, p = float(published.params[TERM]), float(published.pvalues[TERM])
    cibc = cohort(data["adqscibc"], "CIBICVAL")
    cmodel = 'AVAL ~ C(TRTP, Treatment(reference="Placebo")) + C(SITEGR1)'
    cf = smf.ols(cmodel, cibc).fit()
    baseline = dict(delta=float(fit.params[TERM]), pValue=float(fit.pvalues[TERM]),
                    se=float(fit.bse[TERM]), n=len(x), model=FORMULA,
                    csrStatus="Official three-arm treatment-comparison ANCOVA; high-dose versus placebo contrast verified at published precision.",
                    csrDelta=delta, csrPValue=p, csrSE=float(published.bse[TERM]), csrN=len(all3),
                    referenceDelta=-1.00601360, referencePValue=0.2326,
                    csrMatch=abs(delta + 1.00601360)<5e-8 and round(p,4)==0.2326,
                    cibicStatus="Three-arm CIBIC+ ANOVA with pooled-site factor; categorical-treatment contrast, not the continuous-dose response test.",
                    cibic=dict(delta=float(cf.params[TERM]),pValue=float(cf.pvalues[TERM]),se=float(cf.bse[TERM]),
                               n=len(cibc),model=cmodel,referencePValue=.799,match=round(float(cf.pvalues[TERM]),3)==.799))
    rng = np.random.default_rng(20261115)
    design = fit.model.exog.copy()
    y = fit.model.endog.copy()
    index = fit.model.exog_names.index(TERM)
    base_index = fit.model.exog_names.index("BASE")
    df = int(fit.df_resid)
    sigma = float(np.sqrt(fit.mse_resid))
    base_sd = float(x.BASE.std())
    results = []
    for rate in [0, .01, .02, .05, .10, .15]:
        effects, ses, ps = [], [], []
        for _ in range(iterations):
            # Identical independent Bernoulli error probability for each selected numeric field.
            xx = design.copy()
            yy = y.copy()
            yy += (rng.random(len(y)) < rate) * rng.normal(0, sigma, len(y))
            xx[:, base_index] += (rng.random(len(y)) < rate) * rng.normal(0, base_sd, len(y))
            inv = np.linalg.pinv(xx.T @ xx)
            beta = inv @ xx.T @ yy
            resid = yy - xx @ beta
            se = float(np.sqrt((resid @ resid / df) * inv[index,index]))
            effects.append(float(beta[index]))
            ses.append(se)
            ps.append(float(2*t.sf(abs(beta[index]/se),df)))
        results.append(dict(errorRate=rate*100, armA=float(fit.pvalues[TERM]<.05)*100,
                            armB=float(np.mean(np.array(ps)<.05)*100),
                            deltaA=float(fit.params[TERM]), deltaB=float(np.mean(effects)),
                            seA=float(fit.bse[TERM]), seB=float(np.mean(ses)),
                            pA=float(fit.pvalues[TERM]), pB=float(np.median(ps)), iterations=iterations,
                            deltaDrift=float(np.mean(effects)-fit.params[TERM]),
                            seInflation=float((np.mean(ses)/fit.bse[TERM]-1)*100),
                            pShift=float(np.median(ps)-fit.pvalues[TERM])))
    return baseline, results
