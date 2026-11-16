import unittest
import pandas as pd
from critical_rule_checks import check, controlled_terms
from discrepancy_ledger import collect_flags

class CriticalRuleTests(unittest.TestCase):
    def test_demographic_controlled_terms(self):
        terms=controlled_terms()
        d=pd.DataFrame({"SEX":[next(iter(terms["DM.SEX"])),"INVALID"],
                        "RACE":[next(iter(terms["DM.RACE"]))]*2})
        self.assertEqual(check(7,d,{})[1].tolist(),[False,True])
    def test_missing_disposition_is_not_silent(self):
        d=pd.DataFrame({"USUBJID":["a"],"DSCAT":["DISPOSITION EVENT"],
                        "DSDECOD":[next(iter(controlled_terms()["DS.DSDECOD"]))],"DSSEQ":[1.]})
        out,mask,_=check(15,d,{"dm":pd.DataFrame({"USUBJID":["a","b"]})})
        self.assertEqual(out.loc[mask,"USUBJID"].tolist(),["b"])
        ledger=collect_flags("015","DS",d,out,mask)
        self.assertFalse(ledger[0]["automaticCorrectionEligible"])
    def fixture(self):
        codes=[1,2,4,5,6,7,8,11,12,13,14]
        return pd.DataFrame({"USUBJID":"a","VISITNUM":3.,"QSDTC":"2020-01-01",
            "QSCAT":"ALZHEIMER'S DISEASE ASSESSMENT SCALE",
            "QSTESTCD":[f"ACITM{i:02}" for i in codes],"QSSTRESN":0.,
            "QSSEQ":range(1,12)})
    def test_complete_items_and_out_of_bounds(self):
        d=self.fixture();self.assertFalse(check(53,d,{})[1].any())
        d.loc[0,"QSSTRESN"]=11
        self.assertEqual(int(check(53,d,{})[1].sum()),1)
    def test_missing_item_and_duplicate_item(self):
        d=self.fixture().iloc[1:]
        out,mask,_=check(53,d,{})
        self.assertEqual(int(mask.sum()),1);self.assertTrue(out.loc[mask,"QSSEQ"].isna().all())
        duplicate=pd.concat([self.fixture(),self.fixture().iloc[[0]]])
        self.assertEqual(int(check(53,duplicate,{})[1].sum()),2)
    def test_missing_value_is_flagged(self):
        d=self.fixture();d.loc[0,"QSSTRESN"]=float("nan")
        self.assertEqual(int(check(53,d,{})[1].sum()),1)
    def test_baseline_date_calendar_policy(self):
        d=pd.concat([self.fixture().iloc[[0]]]*3,ignore_index=True)
        d["QSDTC"]=["2020-01-01T18:00","2020-01-02","2020-01"]
        d["QSBLFL"]="Y";d["VISIT"]="BASELINE"
        dm=pd.DataFrame({"USUBJID":["a"],"RFSTDTC":["2020-01-01"]})
        self.assertEqual(check(55,d,{"dm":dm})[1].tolist(),[False,True,True])
if __name__=="__main__":unittest.main()
