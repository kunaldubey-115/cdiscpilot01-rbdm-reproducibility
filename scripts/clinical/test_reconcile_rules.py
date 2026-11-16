"""Run after reconcile_rules.py: python -m unittest discover -s scripts/clinical -p 'test_reconcile_rules.py'."""
import json
import unittest
from collections import Counter

import openpyxl
import pandas as pd

from extended_rules import extra_check
from fetch_data import ROOT, DATA, SDTM, ADAM
from rules import evaluate_rules, NON_XPT


class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((DATA.parent / "Rule_Reconciliation.json").read_text())
        data = {n: pd.read_sas(DATA / f"{n}.xpt", format="xport", encoding="cp1252")
                for n in SDTM + ADAM}
        cls.original = evaluate_rules(
            openpyxl.load_workbook(ROOT / "scripts/clinical/input/template.xlsx"), data)

    def test_all_rules_and_original_outcomes_preserved(self):
        self.assertEqual(len(self.audit["rules"]), 125)
        self.assertEqual(len({r["id"] for r in self.audit["rules"]}), 125)
        for actual, original in zip(self.audit["rules"], self.original):
            for key, value in original.items():
                self.assertEqual(actual[key], value, (original["id"], key))

    def test_blocks_and_external_rules_remain_unknown(self):
        self.assertEqual(Counter(r["status"] for r in self.audit["rules"]),
                         {"evaluated": 42, "blocked_missing_fields": 29,
                          "blocked_specification": 44, "non_xpt": 10})
        for r in self.audit["rules"]:
            if r["status"] != "evaluated":
                self.assertIsNone(r["discrepancies"])
                self.assertIsNone(r["evaluated"])
            self.assertEqual(r["status"] == "non_xpt", int(r["id"][-3:]) in NON_XPT)

    def test_production_mmse_boundary_not_rewritten(self):
        a = pd.DataFrame({"MMSETOT": [9, 10, 23, 24, 25, float("nan")]})
        data = {"dm": pd.DataFrame({"USUBJID": []}), "adsl": a}
        _, mask, _ = extra_check(57, a, data)
        self.assertEqual(mask.tolist(), [True, False, False, False, True, True])

    def test_population_and_nonoperative_sensitivity_are_separate(self):
        pop = self.audit["populations"]
        self.assertEqual(pop["dmSubjects"], 306)
        self.assertEqual(pop["dmArmCounts"]["Screen Failure"], 52)
        self.assertEqual(pop["adslSubjects"], 254)
        self.assertEqual(pop["adslFlags"]["EFFFL"]["Y"], 234)
        sensitivity = self.audit["mmseSensitivityNotEligibility"]
        self.assertEqual(sensitivity["equal24"], 2)
        self.assertEqual(sensitivity["current10to24Failures"], 0)
        self.assertEqual(sensitivity["documented10to23Failures"], 2)


if __name__ == "__main__":
    unittest.main()
