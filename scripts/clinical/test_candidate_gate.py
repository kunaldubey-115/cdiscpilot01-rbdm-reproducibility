"""The SAP exception is narrow; candidate builders cannot silently pass."""
import unittest
import json
import pandas as pd
from validate_rebuild import DATA, TARGETS, cibic_convention_passed, cibic_exception_rows, all_targets_passed, compare_records

class CandidateGateTests(unittest.TestCase):
    def fields(self):
        report=json.loads((DATA.parent/"clean_rebuild_validation.json").read_text())
        return report["adqscibcFields"]

    def test_documented_cibic_exception(self):
        self.assertTrue(cibic_convention_passed(self.fields()))

    def test_changed_score_is_not_waived(self):
        fields=self.fields()
        score=next(r for r in fields if r["variable"]=="AVAL")
        score.update(status="MISMATCH",mismatches=1)
        self.assertFalse(cibic_convention_passed(fields))

    def test_different_row_count_is_not_waived(self):
        fields=self.fields()
        fields[0]["compared"]=731
        self.assertFalse(cibic_convention_passed(fields))

    def test_different_traceability_count_is_not_waived(self):
        fields=self.fields()
        next(r for r in fields if r["variable"]=="ADT")["mismatches"]=36
        self.assertFalse(cibic_convention_passed(fields))

    def test_all_nine_gate_checks_verified_exception(self):
        rows=[{"dataset":n.upper(),"status":"PASSED"} for n in TARGETS]
        cibic=next(r for r in rows if r["dataset"]=="ADQSCIBC")
        cibic["status"]="PASSED (SAP-Aligned Convention)"
        self.assertFalse(all_targets_passed(rows))
        cibic["conventionVerified"]=True
        self.assertTrue(all_targets_passed(rows))
        rows[-1]["status"]="FAILED"
        self.assertFalse(all_targets_passed(rows))

    def test_sas_transport_zero_does_not_create_missing_records(self):
        a=pd.DataFrame({"USUBJID":["a"],"VISIT":[0.],"VALUE":[1.]})
        b=a.assign(VISIT=5.397605346934028e-79)
        self.assertTrue(all(r["status"]=="MATCH" for r in compare_records(a,b,{},["USUBJID","VISIT"])))
        b=b.assign(VISIT=1.)
        self.assertTrue(any(r["status"]=="MISMATCH" for r in compare_records(a,b,{},["USUBJID","VISIT"])))

    def test_exception_requires_matching_locf_row_sets(self):
        a=pd.DataFrame({"USUBJID":[f"fixture-{i}" for i in range(35)],"AVISITN":16.,
                        "DTYPE":"LOCF","VISIT":"Week 8","VISITNUM":8.,
                        "ADY":56.,"ADT":20000.,"AWTDIFF":56.,"QSSEQ":1.})
        b=a.assign(VISIT="Week 12",VISITNUM=9.,ADY=84.,ADT=20028.,AWTDIFF=28.,QSSEQ=2.)
        self.assertEqual(len(cibic_exception_rows(a,b)),35)
        b.loc[0,"DTYPE"]=""
        self.assertEqual(cibic_exception_rows(a,b),[])
        b.loc[0,"DTYPE"]="LOCF";b.loc[0,"VISIT"]="Week 8"
        self.assertEqual(cibic_exception_rows(a,b),[])

if __name__=="__main__":
    unittest.main()
