"""
Unit Tests for Dependency Graph & Cycle Analysis Engine
Milestone M1.6 Verification
"""

import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dependency_engine.dependency_graph import DependencyGraph

class TestDependencyCycleAnalysis(unittest.TestCase):

    def setUp(self):
        # We instantiate with a dummy path and supply custom edges for unit testing
        self.engine = DependencyGraph(":memory:")

    def test_acyclic_graph_topological_sort(self):
        # Linear pipeline: DS -> ADSO -> CP -> QRY
        edges = [
            {"source": "DS_SALES", "target": "ADSO_SALES", "dependency_type": "EXTRACTS_INTO", "is_hard": True},
            {"source": "ADSO_SALES", "target": "CP_SALES", "dependency_type": "PART_PROVIDER", "is_hard": True},
            {"source": "CP_SALES", "target": "QRY_SALES", "dependency_type": "REPORTING_PROVIDER", "is_hard": True}
        ]
        result = self.engine.analyze_dependencies(custom_edges=edges)

        self.assertFalse(result["has_cycles"])
        self.assertEqual(result["cyclic_sccs_count"], 0)
        self.assertEqual(result["total_edges"], 3)
        self.assertEqual(len(result["preserved_edges"]), 3)

        # Topological order check
        seq = result["topological_sequence"]
        self.assertLess(seq.index("DS_SALES"), seq.index("ADSO_SALES"))
        self.assertLess(seq.index("ADSO_SALES"), seq.index("CP_SALES"))
        self.assertLess(seq.index("CP_SALES"), seq.index("QRY_SALES"))

    def test_type_1_self_loop_detection(self):
        edges = [
            {"source": "ADSO_A", "target": "ADSO_B", "dependency_type": "DATA_FLOW", "is_hard": True},
            {"source": "ADSO_A", "target": "ADSO_A", "dependency_type": "LOOKUP_ROUTINE", "is_hard": False}
        ]
        result = self.engine.analyze_dependencies(custom_edges=edges)

        self.assertTrue(result["has_cycles"])
        self.assertEqual(result["cyclic_sccs_count"], 1)
        cycle_report = result["cycle_reports"][0]
        self.assertEqual(cycle_report["cycle_type"], "TYPE_1_SELF_LOOP")
        self.assertFalse(cycle_report["manual_redesign_required"])
        # All edges preserved
        self.assertEqual(result["total_edges"], 2)

    def test_type_2_lookup_induced_cycle_decoupling(self):
        # ADSO_A feeds ADSO_B (hard ETL), but ADSO_B has a lookup routine reading from ADSO_A (soft lookup)
        edges = [
            {"source": "ADSO_A", "target": "ADSO_B", "dependency_type": "DATA_FLOW", "is_hard": True},
            {"source": "ADSO_B", "target": "ADSO_A", "dependency_type": "LOOKUP_ROUTINE", "is_hard": False}
        ]
        result = self.engine.analyze_dependencies(custom_edges=edges)

        self.assertTrue(result["has_cycles"])
        self.assertEqual(result["cyclic_sccs_count"], 1)

        cycle_report = result["cycle_reports"][0]
        self.assertEqual(cycle_report["cycle_type"], "TYPE_2_LOOKUP_INDUCED")
        self.assertFalse(cycle_report["manual_redesign_required"])
        self.assertFalse(result["has_unresolvable_cycles"])

        # All edges must be preserved (zero dropped edges)
        self.assertEqual(len(result["preserved_edges"]), 2)

        # Sequencing exception must be recorded with rationale
        self.assertEqual(len(result["sequencing_exceptions"]), 1)
        self.assertEqual(result["sequencing_exceptions"][0]["dependency_type"], "LOOKUP_ROUTINE")
        self.assertIn("decoupled", result["sequencing_exceptions"][0]["rationale"].lower())

        # ADSO_A must precede ADSO_B in hard dependency topological sequence
        seq = result["topological_sequence"]
        self.assertLess(seq.index("ADSO_A"), seq.index("ADSO_B"))

    def test_type_3_mutual_hard_etl_cycle_flags_redesign(self):
        # ADSO_A feeds ADSO_B (hard) and ADSO_B feeds ADSO_A (hard)
        edges = [
            {"source": "ADSO_A", "target": "ADSO_B", "dependency_type": "DATA_FLOW", "is_hard": True},
            {"source": "ADSO_B", "target": "ADSO_A", "dependency_type": "DATA_FLOW", "is_hard": True}
        ]
        result = self.engine.analyze_dependencies(custom_edges=edges)

        self.assertTrue(result["has_cycles"])
        self.assertTrue(result["has_unresolvable_cycles"])

        cycle_report = result["cycle_reports"][0]
        self.assertEqual(cycle_report["cycle_type"], "TYPE_3_MUTUAL_ETL")
        self.assertTrue(cycle_report["manual_redesign_required"])
        self.assertIn("RE-ENGINEERING REQUIRED", cycle_report["resolution_strategy"])

        # Invariant: Both edges remain preserved for audit
        self.assertEqual(len(result["preserved_edges"]), 2)

    def test_legacy_backward_compatibility(self):
        edges = [
            {"source": "NODE_1", "target": "NODE_2", "dependency_type": "DATA_FLOW", "is_hard": True}
        ]
        # Test backward-compatible method
        legacy_res = self.engine.get_topological_order()
        self.assertIn("sequence", legacy_res)
        self.assertIn("has_cycle", legacy_res)
        self.assertIn("cycles", legacy_res)

    def test_lineage_and_impact_analysis(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("CREATE TABLE bw_objects (technical_name TEXT PRIMARY KEY)")
        cur.execute("CREATE TABLE bw_object_dependencies (source_object TEXT, dependent_object TEXT, dependency_type TEXT, mapping_details TEXT)")
        cur.executemany("INSERT INTO bw_objects VALUES (?)", [("DS_01",), ("ADSO_01",), ("HCPR_01",), ("QUERY_01",)])
        cur.executemany("INSERT INTO bw_object_dependencies VALUES (?, ?, ?, ?)", [
            ("DS_01", "ADSO_01", "EXTRACTS_INTO", ""),
            ("ADSO_01", "HCPR_01", "PART_PROVIDER", ""),
            ("HCPR_01", "QUERY_01", "REPORTING_PROVIDER", ""),
            ("EXTERNAL_DS", "ADSO_01", "EXTRACTS_INTO", "")  # Missing node
        ])
        conn.commit()

        engine = DependencyGraph(":memory:")
        # Monkey patch load_edges_from_db to read from our in-memory connection
        engine.load_edges_from_db = lambda selected_objects=None: [
            {"source": "DS_01", "target": "ADSO_01", "dependency_type": "EXTRACTS_INTO", "is_hard": True},
            {"source": "ADSO_01", "target": "HCPR_01", "dependency_type": "PART_PROVIDER", "is_hard": True},
            {"source": "HCPR_01", "target": "QUERY_01", "dependency_type": "REPORTING_PROVIDER", "is_hard": True},
            {"source": "EXTERNAL_DS", "target": "ADSO_01", "dependency_type": "EXTRACTS_INTO", "is_hard": True}
        ]

        # Test Upstream Lineage of QUERY_01
        upstream = engine.get_upstream_lineage("QUERY_01")
        up_nodes = [item["node"] for item in upstream]
        self.assertIn("HCPR_01", up_nodes)
        self.assertIn("ADSO_01", up_nodes)
        self.assertIn("DS_01", up_nodes)

        # Test Downstream Lineage of ADSO_01
        downstream = engine.get_downstream_lineage("ADSO_01")
        down_nodes = [item["node"] for item in downstream]
        self.assertIn("HCPR_01", down_nodes)
        self.assertIn("QUERY_01", down_nodes)

        # Test Missing Dependencies
        known = {"DS_01", "ADSO_01", "HCPR_01", "QUERY_01"}
        missing = engine.get_missing_dependencies(known)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["missing_node"], "EXTERNAL_DS")

        # Test Impact Analysis for ADSO_01
        impact = engine.get_impact_analysis("ADSO_01")
        self.assertEqual(impact["target_object"], "ADSO_01")
        self.assertEqual(impact["blast_radius_tier"], "HIGH")
        self.assertIn("HCPR_01", impact["direct_consumers"])
        self.assertIn("QUERY_01", impact["transitive_consumers"])
        conn.close()

if __name__ == "__main__":
    unittest.main()
