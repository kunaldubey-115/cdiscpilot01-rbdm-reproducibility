"""Dual-track isolation and fail-closed intervention authorization."""
import copy
import json
import unittest
import pandas as pd
from dual_track import DATA, OUT, SDTM, TRACKS, specifications, rebuild_track, require_challenge_readiness

class DualTrackTests(unittest.TestCase):
    def test_reference_pass_does_not_authorize_unfinished_intervention(self):
        report=json.loads((OUT/"dual_track_validation.json").read_text())
        self.assertTrue(report["tracks"][TRACKS[0]]["passed"])
        with self.assertRaisesRegex(RuntimeError,"prerequisites"):
            require_challenge_readiness(report)

    def test_failed_reference_cannot_be_overridden_by_readiness(self):
        report=json.loads((OUT/"dual_track_validation.json").read_text())
        report["tracks"][TRACKS[0]]["passed"]=False
        report["interventionReady"]=True
        with self.assertRaisesRegex(RuntimeError,"gate"):
            require_challenge_readiness(report)

    def test_separate_rebuilds_preserve_source_and_spec_inputs(self):
        source={n:pd.read_sas(DATA/f"{n}.xpt",format="xport",encoding="utf8") for n in SDTM}
        source["sv"]=pd.read_sas(DATA/"supplemental/sv.xpt",format="xport",encoding="utf8")
        spec=specifications();original_spec=copy.deepcopy(spec)
        snapshots={n:pd.util.hash_pandas_object(frame).to_numpy() for n,frame in source.items()}
        built=[]
        for track in TRACKS:
            frames,_=rebuild_track(source,spec,track);built.append(frames)
            for name,frame in source.items():
                self.assertTrue((pd.util.hash_pandas_object(frame).to_numpy()==snapshots[name]).all())
            self.assertEqual(spec,original_spec)
        self.assertIsNot(built[0]["adsl"],built[1]["adsl"])
        for name in ("adsl","adae","adtte","adqscibc"):
            pd.testing.assert_frame_equal(built[0][name],built[1][name])
        self.assertNotEqual(len(built[0]["advs"]),len(built[1]["advs"]))

    def test_unknown_track_is_rejected(self):
        with self.assertRaises(ValueError):rebuild_track({},{},"combined")

if __name__=="__main__":unittest.main()
