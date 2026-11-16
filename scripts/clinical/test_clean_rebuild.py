"""Source-only reconstruction checks; target data are not used as derivation inputs."""
import unittest
import pandas as pd
from rebuild_adsl import rebuild_adsl
from validate_rebuild import DATA, SDTM, TARGETS, specifications, compare_adsl, all_targets_passed

class CleanRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
        cls.spec=specifications()["adsl"]

    def test_source_change_reaches_output_without_target_access(self):
        changed={**self.sources,"dm":self.sources["dm"].copy(deep=True)}
        mask=changed["dm"].ARMCD.eq("Pbo")
        changed["dm"].loc[mask,"AGE"]=60
        rebuilt,_=rebuild_adsl(changed,self.spec)
        ids=set(changed["dm"].loc[mask,"USUBJID"])
        self.assertTrue(rebuilt.loc[rebuilt.USUBJID.isin(ids),"AGE"].eq(60).all())
        self.assertTrue(rebuilt.loc[rebuilt.USUBJID.isin(ids),"AGEGR1N"].eq(1).all())

    def test_no_source_mutation_or_undocumented_sv_substitution(self):
        original=self.sources["dm"].copy(deep=True)
        rebuilt,_=rebuild_adsl(self.sources,self.spec)
        pd.testing.assert_frame_equal(original,self.sources["dm"])
        self.assertNotIn("TRTSDT",rebuilt)
        self.assertNotIn("COMP24FL",rebuilt)
        self.assertEqual(len(rebuilt),254)

    def test_comparator_catches_values_and_missing_columns(self):
        actual=pd.DataFrame({"USUBJID":["a"],"AGE":[60.]})
        target=pd.DataFrame({"USUBJID":["a"],"AGE":[61.],"EFFFL":["Y"]})
        result={r["variable"]:r for r in compare_adsl(actual,target,{})}
        self.assertEqual(result["AGE"]["status"],"MISMATCH")
        self.assertEqual(result["EFFFL"]["status"],"NOT REBUILT")

    def test_supplemental_sv_is_a_real_derivation_input(self):
        sv=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        source={**self.sources,"sv":sv}
        before,_=rebuild_adsl(source,self.spec)
        altered=sv.copy(deep=True)
        i=altered.index[altered.VISITNUM.eq(3)][0]
        subject=altered.loc[i,"USUBJID"]
        altered.loc[i,"SVSTDTC"]=(pd.Timestamp(altered.loc[i,"SVSTDTC"])+pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        after,_=rebuild_adsl({**source,"sv":altered},self.spec)
        self.assertEqual(after.set_index("USUBJID").loc[subject,"TRTSDT"],
                         before.set_index("USUBJID").loc[subject,"TRTSDT"]+1)

    def test_approved_bmi_rounding_order_and_boundary(self):
        vs=self.sources["vs"].copy(deep=True)
        vs.loc[vs.VSTESTCD.eq("HEIGHT") & vs.VISITNUM.eq(1),"VSSTRESN"]=100.04
        vs.loc[vs.VSTESTCD.eq("WEIGHT") & vs.VISITNUM.eq(3),"VSSTRESN"]=30.05
        rebuilt,_=rebuild_adsl({**self.sources,"vs":vs},self.spec)
        self.assertTrue(rebuilt.HEIGHTBL.eq(100.).all())
        observed=rebuilt.WEIGHTBL.notna()
        self.assertGreater(observed.sum(),0)
        self.assertTrue(rebuilt.loc[observed,"WEIGHTBL"].eq(30.1).all())
        self.assertTrue(rebuilt.loc[observed,"BMIBL"].eq(30.1).all())
        self.assertTrue(rebuilt.loc[observed,"BMIBLGR1"].eq(">=30").all())
        self.assertTrue(rebuilt.loc[~observed,"BMIBL"].isna().all())
        self.assertTrue(rebuilt.loc[~observed,"BMIBLGR1"].eq("").all())
        vs.loc[vs.VSTESTCD.eq("WEIGHT") & vs.VISITNUM.eq(3),"VSSTRESN"]=30.
        boundary,_=rebuild_adsl({**self.sources,"vs":vs},self.spec)
        self.assertTrue(boundary.loc[observed,"BMIBL"].eq(30.).all())
        self.assertTrue(boundary.loc[observed,"BMIBLGR1"].eq(">=30").all())

    def test_approved_duration_and_disposition_conventions(self):
        sv=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        source={**self.sources,"sv":sv}
        before,_=rebuild_adsl(source,self.spec)
        ds=self.sources["ds"].copy(deep=True)
        ds.loc[ds.DSCAT.eq("DISPOSITION EVENT"),"VISITNUM"]=13
        ds.loc[ds.DSCAT.eq("DISPOSITION EVENT"),"DSTERM"]="ADVERSE EVENT"
        mh=self.sources["mh"].copy(deep=True)
        primary=mh.MHCAT.eq("PRIMARY DIAGNOSIS")
        mh.loc[primary,"MHSTDTC"]=(pd.to_datetime(mh.loc[primary,"MHSTDTC"])+pd.Timedelta(days=365)).dt.strftime("%Y-%m-%d")
        after,_=rebuild_adsl({**source,"ds":ds,"mh":mh},self.spec)
        self.assertTrue(after.VISNUMEN.eq(12).all())
        self.assertTrue((before.DURDIS-after.DURDIS-12).abs().lt(1e-8).all())

    def test_reference_compatibility_is_explicit_and_not_default(self):
        sv=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        source={**self.sources,"sv":sv}
        original,_=rebuild_adsl(source,self.spec)
        compatible,evidence=rebuild_adsl(source,self.spec,mode="reference-compatible")
        missing=compatible.BMIBL.isna()
        self.assertTrue(missing.any())
        self.assertTrue(original.loc[missing,"BMIBLGR1"].eq("").all())
        self.assertTrue(compatible.loc[missing,"BMIBLGR1"].eq("<25").all())
        self.assertTrue(compatible.loc[missing,"BMIBL"].isna().all())
        self.assertIn("Not a clinically justified classification",evidence["BMIBLGR1"])
        again,_=rebuild_adsl(source,self.spec)
        pd.testing.assert_frame_equal(original,again)

    def test_reference_duration_uses_inclusive_dates(self):
        from rebuild_adsl import normalize_precision
        sv=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        result,_=rebuild_adsl({**self.sources,"sv":sv},self.spec,mode="reference-compatible")
        expected=normalize_precision((result.VISIT1DT-result.DISONSDT+1)/(365.25/12),1)
        pd.testing.assert_series_equal(result.DURDIS,expected,check_names=False)

    def test_full_gate_requires_every_dataset(self):
        rows=[{"dataset":name.upper(),"status":"PASSED"} for name in TARGETS]
        self.assertTrue(all_targets_passed(rows))
        self.assertFalse(all_targets_passed(rows[:1]))
        self.assertFalse(all_targets_passed(rows[:-1]+[rows[0]]))
        self.assertFalse(all_targets_passed(rows[:-1]+[{"dataset":TARGETS[-1].upper(),"status":"NOT REBUILT"}]))
        self.assertFalse(all_targets_passed(rows+[rows[0]]))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            rebuild_adsl(self.sources,self.spec,mode="unknown")

if __name__=="__main__":
    unittest.main()
