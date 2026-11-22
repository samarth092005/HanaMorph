import os
import unittest
import tempfile
import sqlite3
from database.schema_manager import SchemaManager
from dependency_engine.dependency_graph import DependencyGraph
from assessment_engine.complexity_engine import ComplexityEngine
from assessment_engine.migration_risk_engine import MigrationRiskEngine
from assessment_engine.feasibility_engine import FeasibilityEngine
from assessment_engine.target_compatibility_engine import TargetCompatibilityEngine
from assessment_engine.effort_estimation_engine import EffortEstimationEngine
from assessment_engine.prioritization_engine import PrioritizationEngine
from assessment_engine.landscape_intelligence import LandscapeIntelligence
from assessment_engine.assessment_engine import AssessmentEngine

class TestM3ModernizationIntelligence(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Initialize schema with Migration 7
        schema_mgr = SchemaManager(self.db_path)
        schema_mgr.apply_migrations()
        
        # Populate test catalog objects & dependencies
        self._seed_test_data()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def _seed_test_data(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Insert test catalog objects into bw_objects
        objects = [
            ("obj-1", "S21", "ZTEST_ADSO1", "ADSO", "Test Standard ADSO", "ZBW", "$TMP", "LIVE_VERIFIED"),
            ("obj-2", "S21", "ZTEST_ADSO2", "ADSO", "Test Dependent ADSO", "ZBW", "$TMP", "LIVE_VERIFIED"),
            ("obj-3", "S21", "ZTEST_HCPR", "COMPOSITE_PROVIDER", "Test Union/Join CompositeProvider", "ZBW", "$TMP", "CACHED"),
            ("obj-4", "S21", "ZTEST_ABAP_ROUTINE", "ADSO", "Complex Routine ADSO", "ZBW", "$TMP", "CACHED"),
            ("obj-5", "S21", "ZTEST_ISFS", "INFOSOURCE", "Staging InfoSource", "ZBW", "$TMP", "LIVE_VERIFIED"),
        ]
        
        for oid, sys_id, name, otype, desc, ia, pkg, prov in objects:
            cur.execute("""
                INSERT INTO bw_objects (id, system_id, technical_name, type, description, infoarea, package, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (oid, sys_id, name, otype, desc, ia, pkg, prov))
            
            fcount = 14 if "1" in name else (20 if "2" in name else 10)
            # Seed fields into bw_object_fields
            for i in range(1, fcount + 1):
                cur.execute("""
                    INSERT INTO bw_object_fields (object_name, field_name, data_type, length, is_key, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, f"FIELD_{i}", "CHAR" if i % 2 == 0 else "NUMC", 10, 1 if i <= 2 else 0, f"Field {i} description"))
        
        # Seed lineage edges into bw_object_dependencies
        # ZTEST_ISFS -> ZTEST_ADSO1 -> ZTEST_ADSO2 -> ZTEST_HCPR
        edges = [
            ("ZTEST_ISFS", "ZTEST_ADSO1", "DATA_FLOW"),
            ("ZTEST_ADSO1", "ZTEST_ADSO2", "DATA_FLOW"),
            ("ZTEST_ADSO2", "ZTEST_HCPR", "UNION"),
            ("ZTEST_ABAP_ROUTINE", "ZTEST_HCPR", "JOIN")
        ]
        for src, tgt, rtype in edges:
            cur.execute("""
                INSERT INTO bw_object_dependencies (source_object, dependent_object, dependency_type)
                VALUES (?, ?, ?)
            """, (src, tgt, rtype))

        conn.commit()
        conn.close()

    def test_01_complexity_engine_7_dimensions(self):
        comp_engine = ComplexityEngine(self.db_path)
        res = comp_engine.evaluate_object_complexity("ZTEST_ADSO1")
        
        self.assertEqual(res["object_name"], "ZTEST_ADSO1")
        self.assertIn("dimensions", res)
        dims = res["dimensions"]
        
        # Verify all 7 required dimensions exist and have valid scores
        required_dims = ["structural", "dependency", "transformation", "data_model", "semantic", "customization", "operational"]
        for d in required_dims:
            self.assertIn(d, dims)
            score = dims[d]["score"]
            self.assertTrue(0 <= score <= 100, f"Dimension {d} score out of range: {score}")
            
        self.assertTrue(0 <= res["overall_complexity_score"] <= 100)
        self.assertIn(res["complexity_category"], ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
        self.assertIsInstance(res["primary_drivers"], list)

    def test_02_migration_risk_engine_7_factors(self):
        risk_engine = MigrationRiskEngine(self.db_path)
        risk_data = risk_engine.evaluate_object_risk("ZTEST_ABAP_ROUTINE")
        
        self.assertEqual(risk_data["object_name"], "ZTEST_ABAP_ROUTINE")
        self.assertIn("risk_dimensions", risk_data)
        factors = risk_data["risk_dimensions"]
        
        # Verify all 7 risk dimensions
        required_factors = ["technical", "dependency", "functional", "data_compatibility", "platform", "operational", "security"]
        for f in required_factors:
            self.assertIn(f, factors)
            score = factors[f]["score"]
            self.assertTrue(0 <= score <= 100)
            
        self.assertIn(risk_data["risk_level"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertIsInstance(risk_data["mitigation_suggestions"], list)
        self.assertGreaterEqual(len(risk_data["mitigation_suggestions"]), 1)

    def test_03_target_compatibility_4_routes(self):
        comp_engine = ComplexityEngine(self.db_path)
        risk_engine = MigrationRiskEngine(self.db_path)
        compat_engine = TargetCompatibilityEngine()
        
        # Standard ADSO -> Should recommend Native Datasphere
        comp1 = comp_engine.evaluate_object_complexity("ZTEST_ADSO1")
        risk1 = risk_engine.evaluate_object_risk("ZTEST_ADSO1")
        eval1 = compat_engine.evaluate_all_routes("ZTEST_ADSO1", comp1, risk1, {"type": "ADSO"})
        
        self.assertIn("Native Datasphere", eval1["recommended_target"])
        routes = eval1["routes"]
        self.assertEqual(len(routes), 4)
        self.assertIn("native_datasphere", routes)
        self.assertIn("bw_bridge", routes)
        self.assertIn("bdc", routes)
        self.assertIn("hybrid", routes)
        
        # ABAP Routine Object -> Should recommend BW Bridge or Hybrid
        comp_abap = comp_engine.evaluate_object_complexity("ZTEST_ABAP_ROUTINE")
        risk_abap = risk_engine.evaluate_object_risk("ZTEST_ABAP_ROUTINE")
        eval_abap = compat_engine.evaluate_all_routes("ZTEST_ABAP_ROUTINE", comp_abap, risk_abap, {"type": "ADSO"})
        self.assertIn(eval_abap["recommended_target"], ["SAP BW Bridge", "Hybrid Modernization"])

    def test_04_feasibility_engine_states(self):
        comp_engine = ComplexityEngine(self.db_path)
        risk_engine = MigrationRiskEngine(self.db_path)
        feas_engine = FeasibilityEngine()
        
        comp1 = comp_engine.evaluate_object_complexity("ZTEST_ADSO1")
        risk1 = risk_engine.evaluate_object_risk("ZTEST_ADSO1")
        
        # Ready for Modernization
        f1 = feas_engine.evaluate_feasibility("ZTEST_ADSO1", comp1, risk1, {"type": "ADSO", "provenance": "LIVE_VERIFIED"})
        self.assertEqual(f1["feasibility_status"], "READY_FOR_MODERNIZATION")
        
        # Blocked State for unsupported type
        f2 = feas_engine.evaluate_feasibility("ZODSV_TEST", comp1, risk1, {"type": "ODSV", "provenance": "LIVE_VERIFIED"})
        self.assertEqual(f2["feasibility_status"], "BLOCKED")

    def test_05_effort_estimation_engine(self):
        comp_engine = ComplexityEngine(self.db_path)
        risk_engine = MigrationRiskEngine(self.db_path)
        compat_engine = TargetCompatibilityEngine()
        feas_engine = FeasibilityEngine()
        effort_engine = EffortEstimationEngine()
        
        comp = comp_engine.evaluate_object_complexity("ZTEST_ADSO1")
        risk = risk_engine.evaluate_object_risk("ZTEST_ADSO1")
        eval_route = compat_engine.evaluate_all_routes("ZTEST_ADSO1", comp, risk, {"type": "ADSO"})
        feas = feas_engine.evaluate_feasibility("ZTEST_ADSO1", comp, risk, {"type": "ADSO", "provenance": "LIVE_VERIFIED"})
        
        effort = effort_engine.estimate_object_effort("ZTEST_ADSO1", comp, risk, feas, eval_route, {"type": "ADSO"})
        
        self.assertGreater(effort["expected_hours"], 0)
        self.assertLessEqual(effort["low_hours"], effort["expected_hours"])
        self.assertGreaterEqual(effort["high_hours"], effort["expected_hours"])
        self.assertIsInstance(effort["effort_drivers"], list)

    def test_06_prioritization_cohorts_and_waves(self):
        dep_graph = DependencyGraph(self.db_path)
        prio_engine = PrioritizationEngine(dep_graph)
        
        test_objects = [
            {"object_name": "ZTEST_ISFS", "type": "INFOSOURCE", "complexity_score": 15, "risk_score": 10, "feasibility_status": "READY_FOR_MODERNIZATION", "recommended_route": "Native Datasphere", "effort": {"expected_hours": 8}, "complexity_details": {"evidence": {"fan_out": 1}}},
            {"object_name": "ZTEST_ADSO1", "type": "ADSO", "complexity_score": 25, "risk_score": 20, "feasibility_status": "READY_FOR_MODERNIZATION", "recommended_route": "Native Datasphere", "effort": {"expected_hours": 16}, "complexity_details": {"evidence": {"fan_out": 2}}},
            {"object_name": "ZTEST_ADSO2", "type": "ADSO", "complexity_score": 35, "risk_score": 25, "feasibility_status": "READY_FOR_MODERNIZATION", "recommended_route": "Native Datasphere", "effort": {"expected_hours": 20}, "complexity_details": {"evidence": {"fan_out": 1}}},
            {"object_name": "ZTEST_HCPR", "type": "COMPOSITE_PROVIDER", "complexity_score": 55, "risk_score": 40, "feasibility_status": "READY_FOR_MODERNIZATION", "recommended_route": "Native Datasphere", "effort": {"expected_hours": 32}, "complexity_details": {"evidence": {"fan_out": 0}}},
        ]
        
        prio = prio_engine.prioritize_objects(test_objects)
        self.assertIn("cohorts", prio)
        cohorts = prio["cohorts"]
        self.assertIn("quick_wins", cohorts)
        self.assertIn("ZTEST_ISFS", cohorts["quick_wins"])
        
        # Verify wave sequence
        waves = prio["waves"]
        self.assertIn("wave_1", waves)
        wave1_names = [o["object_name"] for o in waves["wave_1"]]
        self.assertIn("ZTEST_ISFS", wave1_names)

    def test_07_landscape_intelligence_aggregation(self):
        dep_graph = DependencyGraph(self.db_path)
        coordinator = AssessmentEngine(self.db_path, dep_graph)
        
        # Run assessments for all objects
        res = coordinator.assess_all("S21")
        self.assertEqual(res["total_assessed"], 5)
        
        # Inspect landscape metrics
        landscape_engine = LandscapeIntelligence(self.db_path)
        metrics = landscape_engine.get_landscape_metrics()
        
        self.assertEqual(metrics["total_objects"], 5)
        self.assertGreater(metrics["mean_complexity"], 0)
        self.assertGreater(metrics["total_effort_expected"], 0)
        self.assertIn("ADSO", metrics["by_type"])
        self.assertIn("COMPOSITE_PROVIDER", metrics["by_type"])
        self.assertIn("Native Datasphere", metrics["by_route"])

    def test_08_database_persistence_migration_7(self):
        dep_graph = DependencyGraph(self.db_path)
        coordinator = AssessmentEngine(self.db_path, dep_graph)
        coordinator.assess_all("S21")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Check modernization_assessments
        cur.execute("SELECT object_name, complexity_score, recommended_route FROM modernization_assessments WHERE object_name = 'ZTEST_ADSO1'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "ZTEST_ADSO1")
        
        # Check route_evaluations
        cur.execute("SELECT count(*) FROM route_evaluations WHERE object_name = 'ZTEST_ADSO1'")
        route_count = cur.fetchone()[0]
        self.assertEqual(route_count, 4)
        
        # Check complexity_breakdowns
        cur.execute("SELECT count(*) FROM complexity_breakdowns WHERE object_name = 'ZTEST_ADSO1'")
        comp_count = cur.fetchone()[0]
        self.assertGreaterEqual(comp_count, 1)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
