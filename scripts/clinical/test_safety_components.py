import unittest
import pandas as pd
from safety_components import evaluate_components
from critical_rule_checks import check
from extended_rules import extra_check

class SafetyTests(unittest.TestCase):
    def source(self):
        return {
            "dm":pd.DataFrame({"USUBJID":["a"],"RFSTDTC":["2020-01-02"]}),
            "ex":pd.DataFrame({"USUBJID":["a"]*3,"EXSTDTC":["2020-01-02","2020-01-03","2020-01"],
                               "EXENDTC":["2020-01-02"]*3}),
            "lb":pd.DataFrame({"USUBJID":["a"]*5,"VISITNUM":[1.,4.,4.,4.,4.],
                "LBDTC":["2020-01-01","2020-01-03","2020-01-03","2020-01-03","2020-01-03"],
                "LBSTRESN":[150.,151.,50.,49.,10.],"LBSTNRLO":[100.]*5,"LBSTNRHI":[100.]*4+[float("nan")]}),
            "vs":pd.DataFrame({"USUBJID":["a"]*3,"VISITNUM":[3.,4.,4.],"VSBLFL":["Y","",""],
                "VSDTC":["2020-01-02","2020-01-01","2020-01-03"],"VSTESTCD":["SYSBP"]*3,
                "VSSTRESN":[120.,121.,float("nan")],"VSSTRESU":["mmHg"]*3})
        }
    def test_exposure_order_and_partial_dates(self):
        x=evaluate_components(self.source())
        self.assertEqual(x.loc[x.component.eq("023.date_order"),"status"].tolist(),["NO_FLAG","FLAG","FLAG"])
    def test_lab_strict_boundaries_and_unknown_limit(self):
        x=evaluate_components(self.source())
        self.assertEqual(x.loc[x.component.eq("067.sap_analysis_threshold"),"status"].tolist(),
                         ["NO_FLAG","FLAG","NO_FLAG","FLAG","UNASSESSABLE"])
    def test_vital_completeness_without_invented_range(self):
        s=self.source();s["vs"].loc[0,"VSSTRESN"]=999
        x=evaluate_components(s)
        self.assertEqual(x.loc[x.component.eq("082.completeness"),"status"].tolist(),["NO_FLAG","NO_FLAG","FLAG"])
    def test_baseline_and_postbaseline_chronology(self):
        s=self.source()
        self.assertFalse(check(68,s["lb"],s)[1].any())
        self.assertEqual(check(83,s["vs"],s)[1].tolist(),[False,True,False])
        s["lb"].loc[0,"LBDTC"]="2020-01-03"
        self.assertTrue(check(68,s["lb"],s)[1].iloc[0])
    def test_composite_rules_remain_blocked(self):
        s=self.source()
        for number in [16,23,26,67,82]:
            _,mask,reason=extra_check(number,s["ex"],s)
            self.assertIsNone(mask);self.assertTrue(reason)
if __name__=="__main__":unittest.main()
