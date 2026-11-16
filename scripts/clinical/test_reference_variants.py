"""Source-only construction and explicit compatibility boundaries."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from validate_rebuild import DATA, SDTM, specifications
from rebuild_adsl import rebuild_adsl
from rebuild_bds import rebuild_advs, rebuild_adlbc, rebuild_adlbh
from rebuild_questionnaires import rebuild_adqsadas, rebuild_adqsnpix

class ReferenceVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=specifications()
        cls.source={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
        cls.source["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        cls.adsl,_=rebuild_adsl(cls.source,cls.spec["adsl"],mode="reference-compatible")

    def test_builders_do_not_load_target_or_other_files(self):
        builders={"advs":rebuild_advs,"adlbc":rebuild_adlbc,"adlbh":rebuild_adlbh,
                  "adqsadas":rebuild_adqsadas,"adqsnpix":rebuild_adqsnpix}
        with patch("builtins.open",side_effect=AssertionError("Builder must use supplied inputs")), \
             patch("pandas.read_sas",side_effect=AssertionError("Target access forbidden")):
            for name,builder in builders.items():
                out,_=builder(self.source,self.adsl,self.spec[name],mode="reference-compatible")
                self.assertGreater(len(out),0)

    def test_vs_reconstruction_responds_to_source_change(self):
        original,_=rebuild_advs(self.source,self.adsl,self.spec["advs"],mode="reference-compatible")
        row=original.loc[original.AVAL.notna() & original.AVISITN.between(4,24)].iloc[0]
        changed=dict(self.source);changed["vs"]=self.source["vs"].copy()
        mask=changed["vs"].USUBJID.eq(row.USUBJID)&changed["vs"].VSSEQ.eq(row.VSSEQ)
        self.assertEqual(int(mask.sum()),1)
        changed["vs"].loc[mask,"VSSTRESN"]+=1
        result,_=rebuild_advs(changed,self.adsl,self.spec["advs"],mode="reference-compatible")
        actual=result.loc[result.USUBJID.eq(row.USUBJID)&result.VSSEQ.eq(row.VSSEQ)&result.AVISITN.eq(row.AVISITN),"AVAL"]
        self.assertTrue(np.allclose(actual,row.AVAL+1))

    def test_npi_mean_conflict_is_explicit(self):
        result,proof=rebuild_adqsnpix(self.source,self.adsl,self.spec["adqsnpix"],mode="reference-compatible")
        observed=result.loc[result.PARAMCD.eq("NPTOT")&result.ANL01FL.eq("Y")]
        expected=observed.loc[observed.AVISITN.gt(4)&observed.AVISITN.le(12)].groupby("USUBJID").AVAL.mean()
        actual=result.loc[result.PARAMCD.eq("NPTOTMN")&result.AVISITN.eq(98)].set_index("USUBJID").AVAL
        self.assertEqual(set(expected.index),set(actual.index))
        self.assertTrue(np.allclose(actual.reindex(expected.index),expected))
        self.assertIn("conflict",proof["AVAL"])
        sap_mean=observed.loc[observed.AVISITN.between(4,24)].groupby("USUBJID").AVAL.mean()
        self.assertTrue((actual.subtract(sap_mean).abs()>1e-8).any())

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            rebuild_advs(self.source,self.adsl,self.spec["advs"],mode="ignore-errors")

if __name__=="__main__":unittest.main()
