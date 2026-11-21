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

if __name__ == "__main__":
    unittest.main()
