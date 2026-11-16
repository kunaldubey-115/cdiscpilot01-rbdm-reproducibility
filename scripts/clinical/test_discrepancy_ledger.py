import unittest
import pandas as pd
from discrepancy_ledger import collect_flags

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.source=pd.DataFrame({"USUBJID":["x","x","y"],"QSSEQ":[1.,2.,1.]})
    def test_filters_preserve_source_row_identity(self):
        selected=self.source.iloc[[2,0]]
        rows=collect_flags("rule","QS",self.source,selected,pd.Series([True,False],index=selected.index))
        self.assertEqual(rows[0]["sourceRow"],2)
    def test_subject_flags_do_not_authorize_all_records(self):
        grouped=pd.DataFrame({"USUBJID":["x"]})
        row=collect_flags("rule","QS",self.source,grouped,pd.Series([True]))[0]
        self.assertFalse(row["automaticCorrectionEligible"])
        self.assertIsNone(row["sourceRow"])
    def test_duplicate_sequence_is_not_arbitrarily_corrected(self):
        source=self.source.copy();source.loc[1,"QSSEQ"]=1
        rows=collect_flags("rule","QS",source,source,pd.Series([True,True,False]))
        self.assertTrue(all(not r["automaticCorrectionEligible"] for r in rows))
    def test_deduplication_is_across_rules(self):
        mask=pd.Series([True,False,False])
        a=collect_flags("rule-a","QS",self.source,self.source,mask)
        b=collect_flags("rule-b","QS",self.source,self.source,mask)
        self.assertEqual(a[0]["episodeId"],b[0]["episodeId"])
    def test_mask_alignment_is_required(self):
        with self.assertRaises(ValueError):
            collect_flags("rule","QS",self.source,self.source,pd.Series([True,False,False],index=[2,1,0]))
if __name__=="__main__":unittest.main()
