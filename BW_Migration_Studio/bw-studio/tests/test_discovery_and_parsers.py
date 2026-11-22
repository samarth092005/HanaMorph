import unittest
import sqlite3
import os

class TestDiscoveryAndParsers(unittest.TestCase):
    def setUp(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "bw_studio.sqlite")
        self.assertTrue(os.path.exists(self.db_path), "Database must exist")

    def test_catalog_contains_s21_observed_objects(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name, type FROM source_catalog WHERE name IN ('ZSAM_SO01', 'ZSAM_SO_CP', 'ZSAM_MM_PR')")
        rows = dict(cur.fetchall())
        conn.close()

        self.assertIn("ZSAM_SO01", rows)
        self.assertEqual(rows["ZSAM_SO01"], "ADSO")
        self.assertIn("ZSAM_SO_CP", rows)
        self.assertEqual(rows["ZSAM_SO_CP"], "COMPOSITE_PROVIDER")
        self.assertIn("ZSAM_MM_PR", rows)

    def test_field_schema_extraction(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT field_name, is_key, data_type FROM object_fields WHERE object_name = 'ZSAM_SO01'")
        fields = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        conn.close()

        self.assertIn("SALES_DOC", fields)
        self.assertEqual(fields["SALES_DOC"][0], 1, "SALES_DOC must be a primary key")
        self.assertEqual(fields["SALES_DOC"][1], "CHAR")
        self.assertIn("NET_VALUE", fields)
        self.assertEqual(fields["NET_VALUE"][1], "CURR")

    def test_cache_adapter_adso_dynamic_key_detection(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from discovery.cache_discovery_adapter import CacheDiscoveryAdapter
        adapter = CacheDiscoveryAdapter()
        adso_path = os.path.join(adapter.cache_dir, "adso", "zsam_so01", "a", "model.adso")
        if os.path.exists(adso_path):
            res = adapter.parse_adso_file(adso_path)
            self.assertIsNotNone(res)
            keys = [f["name"] for f in res["fields"] if f["is_key"]]
            self.assertEqual(keys, ["ORDER_ID"])
            self.assertEqual(len(res["fields"]), 5)

    def test_cache_adapter_trcs_full_schema(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from discovery.cache_discovery_adapter import CacheDiscoveryAdapter
        adapter = CacheDiscoveryAdapter()
        trcs_path = os.path.join(adapter.cache_dir, "trcs", "zsam_pr_is01", "m", "model.trcs")
        if os.path.exists(trcs_path):
            res = adapter.parse_trcs_file(trcs_path)
            self.assertIsNotNone(res)
            self.assertEqual(len(res["fields"]), 11)
            self.assertIn("MENGE", [f["name"] for f in res["fields"]])
            self.assertIn("WERKS", [f["name"] for f in res["fields"]])

    def test_cache_adapter_query_partial_provenance(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from discovery.cache_discovery_adapter import CacheDiscoveryAdapter
        adapter = CacheDiscoveryAdapter()
        q_path = os.path.join(adapter.cache_dir, "query", "zsam_pr_q01", "a", "model.query")
        if os.path.exists(q_path):
            res = adapter.parse_query_file(q_path)
            self.assertIsNotNone(res)
            self.assertEqual(res["technical_name"], "ZSAM_PR_Q01")
            self.assertEqual(res["metadata_completeness"], "PARTIAL_NEEDS_BEX_RUNTIME")
            self.assertEqual(res["provenance"], "CACHED_PARTIAL")

    def test_import_metadata_bundle(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from discovery.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine(self.db_path)
        bundle = {
            "objects": [
                {
                    "technical_name": "ZIMPORTED_ADSO_01",
                    "type": "ADSO",
                    "description": "Imported Test ADSO",
                    "fields": [
                        {"name": "ID", "data_type": "CHAR", "is_key": 1, "length": 10},
                        {"name": "VAL", "data_type": "DEC", "is_key": 0, "length": 15, "decimals": 2}
                    ],
                    "dependencies": [("ZSRC_DS", "ZIMPORTED_ADSO_01", "EXTRACTS_INTO")]
                }
            ]
        }
        res = engine.import_metadata_bundle(bundle, system_id="EXT_BW")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["imported_count"], 1)
        self.assertEqual(res["provenance"], "IMPORTED")

        # Verify query
        details = engine.get_object_details("ZIMPORTED_ADSO_01")
        self.assertIsNotNone(details)
        self.assertEqual(details["provenance"], "IMPORTED")
        self.assertEqual(len(details["fields"]), 2)

if __name__ == "__main__":
    unittest.main()
