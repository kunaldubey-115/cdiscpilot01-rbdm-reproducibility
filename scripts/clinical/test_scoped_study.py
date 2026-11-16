"""Synthetic-only tests before freeze; no development/held-out outcome inspection."""
import inspect
import unittest
import pandas as pd
from scoped_challenges import generate
from scoped_detection import correct, detect
from scoped_outcomes import compare_summary

class ScopedStudyTests(unittest.TestCase):
    def fixture(self):
        ids=[f"fixture-{i:03}" for i in range(200)]
        def frame(**cols):return pd.DataFrame({"USUBJID":ids,**cols})
        return {
            "dm":frame(ARMCD="ACTIVE",ACTARMCD="ACTIVE",RFSTDTC="2020-01-01"),
            "qs":frame(QSBLFL="Y",QSTESTCD="ACITM01",QSDTC="2020-01-01",QSSTRESN=2.),
            "ds":frame(DSCAT="DISPOSITION EVENT",VISITNUM=12.,DSDECOD="COMPLETED",DSSTDTC="2020-06-01"),
            "ae":frame(AESTDTC="2020-03-01"),
            "ex":frame(EXSTDTC="2020-01-01",EXENDTC="2020-06-01"),
            "lb":frame(LBTESTCD="ALT",LBSTNRHI=40.,LBSTRESN=20.,VISITNUM=4.),
            "vs":frame(VSDTC="2020-01-01T12:00",VSLOC="ARM",VSPOS="SUPINE"),
            "mh":frame(MHCAT="HISTORICAL DIAGNOSIS",MHSTDTC="1990-01-01"),
            "cm":frame(CMTRT="ASPIRIN",CMROUTE="ORAL",CMDOSE=1.),
            "sc":frame(SCCAT="SUBJECT CHARACTERISTICS")}
    def test_disjoint_subjects_and_reproducible_changes(self):
        source=self.fixture()
        a,ta,ca=generate(source,123,False);b,tb,cb=generate(source,456,True)
        self.assertFalse({r["subject"] for r in ta}&{r["subject"] for r in tb})
        self.assertEqual(len(ca),16);self.assertEqual(len(cb),16)
        again,t2,_=generate(source,123,False)
        pd.testing.assert_frame_equal(pd.DataFrame(ta),pd.DataFrame(t2))
        self.assertTrue(source["dm"].ARMCD.eq("ACTIVE").all())
        for name in a:pd.testing.assert_frame_equal(a[name],again[name])
    def test_correction_requires_uniquely_flagged_record(self):
        source={"qs":pd.DataFrame({"AVAL":[99.,98.,97.]})}
        truth=[{"domain":"QS","sourceRow":i,"field":"AVAL","before":float(i)} for i in range(3)]
        ledger=[{"domain":"QS","sourceRow":0,"automaticCorrectionEligible":True},
                {"domain":"QS","sourceRow":1,"automaticCorrectionEligible":False}]
        corrected,audit=correct(source,ledger,truth)
        self.assertEqual(corrected["qs"].AVAL.tolist(),[0.,98.,97.])
        self.assertEqual(source["qs"].AVAL.tolist(),[99.,98.,97.])
        self.assertEqual([r["captured"] for r in audit],[True,False,False])
    def test_clock_perturbation_supports_date_only_source(self):
        source=self.fixture();source["vs"]["VSDTC"]="2020-01-01"
        dirty,truth,_=generate(source,123,False)
        clocks=[r for r in truth if r["family"]=="Vital clock metadata"]
        self.assertTrue(clocks)
        self.assertTrue(all(r["after"]=="2020-01-01T12:34" for r in clocks))
    def test_detector_has_no_truth_argument(self):
        self.assertNotIn("truth",inspect.signature(detect).parameters)
    def test_missing_rows_are_not_silent_agreement(self):
        baseline=pd.DataFrame({"subject":["a","b"],"Value":[1.,2.]})
        report,_=compare_summary(baseline.iloc[:1],baseline)
        self.assertEqual(report["mismatches"],2);self.assertEqual(report["cells"],4)
    def test_numeric_tolerance_and_not_evaluable(self):
        baseline=pd.DataFrame({"subject":["a"],"Value":[1.]})
        self.assertEqual(compare_summary(baseline.assign(Value=1+1e-10),baseline)[0]["status"],"MATCH")
        self.assertEqual(compare_summary(baseline.assign(Value=2.),baseline)[0]["status"],"DIFFERENCE")
        self.assertIsNone(compare_summary({"error":"model failed"},baseline)[0]["mismatchPercent"])
if __name__=="__main__":unittest.main()
