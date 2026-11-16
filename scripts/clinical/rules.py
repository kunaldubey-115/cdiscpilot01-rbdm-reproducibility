"""Explicit rule implementations. Unavailable specifications never become zero counts."""
import re
import pandas as pd
from extended_rules import extra_check

NON_XPT = {11,33,37,47,99,114,10,21,48,116}

def missing(s):
    return s.isna() | s.astype(str).str.strip().eq("")

def evaluate_rules(workbook, data, *, ledger=None):
    results = []
    dm = data["dm"].set_index("USUBJID")
    for row in workbook["Published_Control_DRP_A"].iter_rows(min_row=5, max_row=129, values_only=True):
        rid, _, domain, targets, modality, description, _, tier, disposition = row[:9]
        if not str(rid).startswith("DRP-A-"):
            continue
        d = data[domain.lower()]
        number = int(rid[-3:])
        evaluated = None
        count = None
        reason = "No validated executable implementation yet. Requires specification review and, for some rules, manual adjudication or external evidence; not replaced by a proxy."
        status = "blocked_specification"
        try:
            mask = None
            if number == 1:
                ids = data["adsl"].loc[data["adsl"].ITTFL.eq("Y"), "USUBJID"]
                d = d[d.USUBJID.isin(ids)]
                mask = missing(d.ARMCD) | d.ARMCD.ne(d.ACTARMCD)
            elif number == 2:
                starts = data["ex"].groupby("USUBJID").EXSTDTC.min()
                d = d[d.USUBJID.isin(starts.index)]
                mask = missing(d.RFSTDTC) | d.RFSTDTC.ne(d.USUBJID.map(starts))
            elif number == 4:
                mask = ~d.AGE.between(50, 95)
            elif number == 8:
                mask = missing(d.ETHNIC) | d.ETHNIC.eq("UNKNOWN")
            elif number == 13:
                mask = ~missing(d.AGE) & missing(d.AGEU)
            elif number == 14:
                mask = d.STUDYID.ne("CDISCPILOT01") | d.DOMAIN.ne("DM")
            elif number == 17:
                d = d[d.DSDECOD.eq("ADVERSE EVENT")]
                ae = data["ae"]
                ids = ae.loc[ae.AEACN.eq("DRUG WITHDRAWN"), "USUBJID"]
                mask = ~d.USUBJID.isin(ids)
            elif number == 18:
                d = d[d.DSCAT.eq("DISPOSITION EVENT")]
                mask = d.duplicated(["USUBJID", "DSCAT", "DSDECOD"], keep="first")
            elif number == 30:
                mask = missing(d.EXDOSFRM) | missing(d.EXDOSFRQ) | missing(d.EXROUTE)
            elif number == 38:
                d = d[d.AEACN.eq("DRUG WITHDRAWN")]
                ds = data["ds"]
                mask = ~d.USUBJID.isin(ds.loc[ds.DSDECOD.eq("ADVERSE EVENT"), "USUBJID"])
            elif number in (39, 40):
                start = d.USUBJID.map(dm.RFSTDTC)
                # Only complete ISO dates can be classified without imputation rules.
                d = d[d.AESTDTC.str.len().ge(10) & start.str.len().ge(10) & d.AESTDTC.ge(start)]
                mask = ~d.AESEV.isin(["MILD", "MODERATE", "SEVERE"]) if number == 39 else missing(d.AEREL)
            elif number == 42:
                d = d[d.AEOUT.eq("RECOVERED/RESOLVED")]
                mask = missing(d.AEENDTC) | d.AEENDTC.str[:10].lt(d.AESTDTC.str[:10])
            elif number in (65, 81):
                # Sequence gaps are not duplicates. Flag every participant in a
                # subject/sequence collision, without requiring consecutive IDs.
                mask = d.duplicated(["USUBJID", domain + "SEQ"], keep=False)
                description = f"Verify uniqueness of USUBJID + {domain}SEQ; sequence gaps are allowed."
            elif number in (22, 51, 93, 104, 118, 125):
                seq = domain + "SEQ"
                d = d.sort_values(["USUBJID", seq])
                expected = d.groupby("USUBJID").cumcount() + 1
                mask = d[seq].ne(expected)
            elif number == 62:
                mask = d.QSCAT.ne(d.QSCAT.str.upper()) | d.QSSCAT.ne(d.QSSCAT.str.upper())
            elif number == 66:
                d = d[d.LBTESTCD.isin(["ALT", "AST", "BILI", "CREAT"])]
                mask = missing(d.LBSTRESN) | missing(d.LBSTRESU)
            elif number == 76:
                mask = ~d.LBDTC.str.contains(r"T\d{2}:\d{2}", regex=True)
            elif number == 78:
                d = d[d.LBCAT.str.contains("URINALYSIS", case=False)]
                mask = d.LBCAT.ne(d.LBCAT.str.upper())
            elif number == 84:
                d = d[d.VSTESTCD.isin(["TEMP", "RESP"])]
                mask = missing(d.VSPOS)
            elif number == 85:
                d = d[d.VSTESTCD.isin(["SYSBP", "DIABP"])]
                mask = missing(d.VSLOC)
            elif number == 86:
                d = d[d.VSTESTCD.eq("TEMP") & d.VSSTRESU.eq("C")]
                mask = d.VSSTRESN.between(36, 36.4)
            elif number == 89:
                mask = ~d.VSDTC.str.contains(r"T\d{2}:\d{2}", regex=True)
            elif number == 106:
                mask = missing(d.CMDECOD)
            elif number == 119:
                d = d[d.SCTESTCD.eq("EDLEVEL")]
                mask = pd.to_numeric(d.SCORRES, errors="coerce").isna()
            elif number == 122:
                mask = d.SCCAT.ne(d.SCCAT.str.upper())
            extra_note = ""
            if mask is None and number not in NON_XPT:
                d, mask, extra_note = extra_check(number,d,data)
            if mask is not None:
                evaluated, count = len(d), int(mask.sum())
                if ledger is not None:
                    from discrepancy_ledger import collect_flags
                    ledger.extend(collect_flags(rid,domain,data[domain.lower()],d,mask))
                status = "evaluated"
                reason = "Programmatic Rule Discrepancies: record-level predicate failures, not confirmed clinical errors or actual site queries. See executable rule definition."
                reason += " " + extra_note
                if number in (39, 40):
                    reason += " Complete-date TEAE subset only; partial dates require adjudication."
            else:
                if extra_note:
                    reason=extra_note
                # Do not infer rule truth from generic missingness.
                tokens = re.findall(r"\b[A-Z][A-Z0-9]{2,8}\b", targets or "")
                absent = [v for v in tokens if (v.startswith(domain) or v=="EPOCH") and v not in d.columns]
                if absent:
                    status = "blocked_missing_fields"
                    reason = "Required fields unavailable in source XPT: " + ", ".join(sorted(set(absent))) + "."
        except KeyError as exc:
            status = "blocked_missing_fields"
            reason = "Required field unavailable: " + str(exc)
        if number in NON_XPT:
            status, evaluated, count = "non_xpt", None, None
            reason = "Requires external-system, vendor, verbatim adjudication, or EDC audit-trail evidence; excluded from the 115 in-database candidate rules."
        if status == "blocked_specification":
            reason = ("Blocked — "+extra_note if extra_note else "Blocked — requires a validated executable specification or reference evidence for this exact predicate: " + description)
        labels={"evaluated":"XPT-Executable", "non_xpt":"N/A — Non-XPT",
                "blocked_missing_fields":"Blocked — required field absent",
                "blocked_specification":"Blocked — specification/reference required"}
        results.append(dict(id=rid, domain=domain, description=description, tier=tier,
                            disposition=disposition, status=status, evaluated=evaluated,
                            discrepancies=count, reason=reason,
                            evaluabilityStatus=labels[status]))
    return results

def classify_variables(workbook, data):
    """Conservative provisional mapping: unknown fields stay unclassified, never auto-suppressed."""
    mapping = []
    for name, d in data.items():
        for col in d.columns:
            tier, reason = "Unclassified", "No verified downstream lineage; do not suppress."
            if name.startswith("ad"):
                if name in ("adqsadas", "adqscibc", "adtte", "adae", "adsl"):
                    tier, reason = "Tier 1", "Conservatively retain Gate 1 dataset; field-level lineage requires review."
                else:
                    tier, reason = "Tier 2", "Gate 2 analysis dataset; retain for submitted summaries."
            else:
                candidates = []
                for r in workbook["Published_Control_DRP_A"].iter_rows(min_row=5, max_row=129, values_only=True):
                    if r[2] == name.upper() and col in re.findall(r"\b[A-Z][A-Z0-9]+\b", r[3] or ""):
                        candidates.append(str(r[7]))
                if candidates:
                    tier = sorted(candidates)[0].split(":")[0]
                    reason = "Workbook rule target mapping; highest criticality wins."
                if col in ("USUBJID", "STUDYID") or col.endswith(("DTC", "DY")):
                    if tier.startswith("Tier 3") or tier == "Unclassified":
                        tier, reason = "Protected lineage", "Identifiers and dates may drive joins, baseline, exposure, or visit windows; suppression not validated."
            if col.endswith(("DTC", "DY")) or col in ("ADT","TRTSDT","TRTEDT","AVISIT","AVISITN","TRTEMFL","USUBJID","STUDYID") or col.endswith("SEQ"):
                tier, reason = "Protected lineage", "Retain date/imputation, visit-window, treatment-emergent or relational lineage. No suppression without verified upstream dependency evidence."
            elif tier.startswith("Tier 3"):
                tier, reason = "Unverified metadata — retain", "Workbook Tier 3 proposal is not verified non-ADaM lineage. Not eligible for suppression."
            mapping.append([name.upper(), col, tier, reason])
    return mapping
