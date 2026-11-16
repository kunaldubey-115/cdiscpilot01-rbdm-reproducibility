"""Counterfactual source fixtures for adverse events, survival and windowed LOCF."""
import unittest
import numpy as np
import pandas as pd
from validate_rebuild import DATA, SDTM, specifications, compare_records, compare_cibic
from rebuild_adsl import rebuild_adsl
from rebuild_adae import rebuild_adae
from rebuild_adtte import rebuild_adtte
from rebuild_cibic import rebuild_cibic

class OutcomeRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
        cls.sources["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        cls.spec=specifications()
        cls.adsl,_=rebuild_adsl(cls.sources,cls.spec["adsl"],mode="reference-compatible")

    def event_fixture(self):
        ae=pd.concat([self.sources["ae"].iloc[[0]]]*3,ignore_index=True)
        ae["AESEQ"]=[1.,2.,3.]
        ae["AESTDTC"]=["2020-01-02","2020-01","2020"]
        ae["AEENDTC"]="2020-01-05"
        ae["AEDECOD"]="DERMATITIS"
        ae["AEBODSYS"]="SKIN AND SUBCUTANEOUS TISSUE DISORDERS"
        adsl=self.adsl.copy(deep=True)
        mask=adsl.USUBJID.eq(ae.USUBJID.iloc[0])
        adsl.loc[mask,"TRTSDT"]=(pd.Timestamp("2020-01-01")-pd.Timestamp("1960-01-01")).days
        adsl.loc[mask,"RFSTDTC"]="2020-01-01"
        adsl.loc[mask,"RFENDTC"]="2020-01-31"
        return ae,adsl

    def test_duration_precedes_imputation_and_source_is_unchanged(self):
        ae,adsl=self.event_fixture()
        before=ae.copy(deep=True)
        out,_=rebuild_adae({**self.sources,"ae":ae},adsl,self.spec["adae"])
        self.assertEqual(out.ADURN.iloc[0],4.)
        self.assertTrue(out.ADURN.iloc[1:].isna().all())
        self.assertEqual(out.ASTDTF.tolist(),["","D",""])
        self.assertEqual(out.TRTEMFL.tolist(),["Y","Y","N"])
        self.assertEqual(out.AOCC01FL.tolist(),["","Y",""])
        pd.testing.assert_frame_equal(ae,before)

    def test_survival_uses_reconstructed_event_and_censors_others(self):
        ae,adsl=self.event_fixture()
        events,_=rebuild_adae({**self.sources,"ae":ae},adsl,self.spec["adae"])
        tte,_=rebuild_adtte(adsl,events,self.spec["adtte"])
        event=tte.loc[tte.USUBJID.eq(ae.USUBJID.iloc[0])].iloc[0]
        self.assertEqual((event.CNSR,event.SRCSEQ,event.AVAL),(0.,2.,1.))
        self.assertEqual(int(tte.CNSR.eq(0).sum()),1)
        self.assertTrue(tte.loc[tte.CNSR.eq(1),"SRCSEQ"].isna().all())

    def cibic_fixture(self,days,values):
        q=self.sources["qs"]
        q=q.loc[q.QSTESTCD.eq("CIBIC") & q.USUBJID.isin(self.adsl.USUBJID)].iloc[[0]]
        q=pd.concat([q]*len(days),ignore_index=True)
        start=self.adsl.set_index("USUBJID").loc[q.USUBJID.iloc[0],"TRTSDT"]
        q["QSDTC"]=[(pd.Timestamp("1960-01-01")+pd.Timedelta(days=start+day-1)).strftime("%Y-%m-%d") for day in days]
        q["QSSTRESN"]=values
        q["QSSEQ"]=np.arange(1,len(days)+1,dtype=float)
        return q

    def test_locf_carries_selected_not_later_unselected_score(self):
        q=self.cibic_fixture([56,83,168],[2.,7.,5.])
        out,_=rebuild_cibic({**self.sources,"qs":q},self.adsl,self.spec["adqscibc"])
        imputed=out.loc[out.DTYPE.eq("LOCF")].iloc[0]
        self.assertEqual((imputed.AVISITN,imputed.QSSEQ,imputed.AVAL),(16.,1.,2.))
        self.assertEqual(out.loc[out.QSSEQ.eq(2),"ANL01FL"].iloc[0],"")

    def test_locf_never_backfills_an_earlier_visit(self):
        q=self.cibic_fixture([112],[3.])
        out,_=rebuild_cibic({**self.sources,"qs":q},self.adsl,self.spec["adqscibc"])
        self.assertEqual(set(out.AVISITN),{16.,24.})

    def test_composite_comparison_is_order_independent_and_detects_missing_rows(self):
        frame=pd.DataFrame({"USUBJID":["a","a"],"AESEQ":[1.,2.],"AVAL":[2.,3.]})
        results=compare_records(frame,frame.iloc[::-1],{},["USUBJID","AESEQ"])
        self.assertTrue(all(r["status"]=="MATCH" for r in results))
        results=compare_records(frame.iloc[:1],frame,{},["USUBJID","AESEQ"])
        self.assertTrue(all(r["status"]=="MISMATCH" for r in results))
        with self.assertRaises(ValueError):
            compare_records(pd.concat([frame,frame]),frame,{},["USUBJID","AESEQ"])

    def test_locf_provenance_remains_a_required_comparison(self):
        frame=pd.DataFrame({"USUBJID":["a"],"PARAMCD":["CIBICVAL"],"AVISITN":[16.],
                            "DTYPE":["LOCF"],"QSSEQ":[1.],"AVAL":[2.]})
        other=frame.assign(QSSEQ=2.)
        result={r["variable"]:r for r in compare_cibic(frame,other,{})}
        self.assertEqual(result["QSSEQ"]["mismatches"],1)
        self.assertEqual(result["AVAL"]["status"],"MATCH")
        self.assertEqual(len(result),len(frame.columns))
        self.assertTrue(all(r["status"]=="MISMATCH" for r in compare_cibic(frame.iloc[:0],frame,{})))

if __name__=="__main__":
    unittest.main()
