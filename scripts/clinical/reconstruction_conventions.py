"""User-approved experiments, not authenticated original SAS programming rules."""
CONVENTIONS = [
    {"field":"BMIBL","rule":"Normalize HEIGHTBL and WEIGHTBL to declared decimal precision before calculating BMI; then normalize BMI precision.",
     "status":"Approved for testing; original SAS logic unconfirmed"},
    {"field":"BMIBLGR1","rule":"Use >=30 as the coded label for BMI greater than or equal to 30.",
     "status":"Approved for testing; legacy code-list discrepancy retained in audit"},
    {"field":"DURDIS","rule":"Elapsed days / (365/12), then declared decimal precision.",
     "status":"Approved for testing; fractional-month convention not specified in original definition"},
    {"field":"VISNUMEN","rule":"Map disposition visit 13 to 12 regardless of disposition reason.",
     "status":"Approved for testing; extends the legacy completed-subject exception"},
]

REFERENCE_COMPATIBILITY_CONVENTIONS = [
    {"field":"DURDIS","rule":"Inclusive elapsed days / (365.25/12), then declared decimal precision.",
     "status":"Approved reference-compatibility experiment; original SAS formula unconfirmed"},
    {"field":"BMIBLGR1","rule":"Assign <25 to missing BMI only in reference-compatible mode; retain missing-BMI quality warning and conservative blank-category alternative.",
     "status":"Approved reference reproduction; not evidence of clinically correct categorization"},
]

CIBIC_IMPUTATION_POLICY = {
    "decision":"Preserve the SAP interpretation",
    "basis":"SAP section 8.2: imputation uses the targeted assessments within the windows.",
    "implementation":"Carry forward only analysis-selected observations; never backfill an earlier visit.",
    "alternative":"Do not substitute the latest unselected observation to obtain reference agreement.",
    "referenceDiscrepancy":"Retain source-date and traceability mismatches in the full-reference audit.",
    "gate":"User-authorized CIBIC+ exception only: 730 matching scores and 35 LOCF rows differing in the six documented traceability fields. Other fields and all other datasets must pass.",
    "status":"User approved PASSED (SAP-Aligned Convention), retaining the discrepancy audit; not an exact-reference match.",
}
