import unittest

def calculate_migration_scores(has_abap, obj_type):
    if has_abap:
        return {"route": "SAP BW Bridge", "native": 45, "bridge": 90, "bdc": 50, "hybrid": 70}
    elif obj_type == "COMPOSITE_PROVIDER":
        return {"route": "Native Datasphere (Analytic Model)", "native": 92, "bridge": 65, "bdc": 75, "hybrid": 60}
    else:
        return {"route": "Native Datasphere", "native": 88, "bridge": 60, "bdc": 80, "hybrid": 55}

class TestAssessmentEngine(unittest.TestCase):
    def test_standard_adso_recommends_native(self):
        res = calculate_migration_scores(has_abap=False, obj_type="ADSO")
        self.assertEqual(res["route"], "Native Datasphere")
        self.assertGreaterEqual(res["native"], 80)

    def test_adso_with_abap_recommends_bridge(self):
        res = calculate_migration_scores(has_abap=True, obj_type="ADSO")
        self.assertEqual(res["route"], "SAP BW Bridge")
        self.assertGreaterEqual(res["bridge"], 85)

    def test_composite_provider_recommends_analytic_model(self):
        res = calculate_migration_scores(has_abap=False, obj_type="COMPOSITE_PROVIDER")
        self.assertIn("Analytic Model", res["route"])
        self.assertGreaterEqual(res["native"], 90)

if __name__ == "__main__":
    unittest.main()
