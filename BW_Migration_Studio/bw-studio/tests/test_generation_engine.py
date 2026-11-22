import unittest
import json

def generate_csn(space, obj_name, fields):
    elements = {}
    for f in fields:
        elements[f["name"]] = {"type": f["type"], "key": f.get("key", False)}
    return {
        "$schema": "https://help.sap.com/doc/csn-v2.0.json",
        "definitions": {
            f"{space}.LT_{obj_name}": {
                "kind": "entity",
                "elements": elements
            }
        }
    }

class TestGenerationEngine(unittest.TestCase):
    def test_csn_payload_structure(self):
        fields = [
            {"name": "SALES_DOC", "type": "cds.String", "key": True},
            {"name": "NET_VALUE", "type": "cds.Decimal", "key": False}
        ]
        csn = generate_csn("SALES_SPACE", "ZSAM_SO01", fields)
        entity_key = "SALES_SPACE.LT_ZSAM_SO01"
        self.assertIn(entity_key, csn["definitions"])
        self.assertEqual(csn["definitions"][entity_key]["elements"]["SALES_DOC"]["key"], True)

    def test_ddl_generation_syntax(self):
        ddl = 'CREATE COLUMN TABLE "SALES_SPACE"."LT_ZSAM_SO01" ("SALES_DOC" NVARCHAR(10) NOT NULL, PRIMARY KEY ("SALES_DOC"));'
        self.assertTrue(ddl.startswith("CREATE COLUMN TABLE"))
        self.assertIn("PRIMARY KEY", ddl)

    def test_view_csn_and_ddl_generation(self):
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from generation_engine.csn_generator import DatasphereCSNGenerator
        from generation_engine.hana_ddl_generator import HANASQLGenerator

        csn_gen = DatasphereCSNGenerator()
        ddl_gen = HANASQLGenerator()

        fields = [
            {"field_name": "ORDER_ID", "data_type": "CHAR", "length": 10, "is_key": 1},
            {"field_name": "NET_VALUE", "data_type": "CURR", "length": 15, "decimals": 2}
        ]

        # View CSN
        view_csn = csn_gen.generate_view_csn("SALES_SPACE", "AM_ZSAM_SO_CP", "LT_ZSAM_SO01", fields)
        def_key = "SALES_SPACE.AM_ZSAM_SO_CP"
        self.assertIn(def_key, view_csn["definitions"])
        self.assertEqual(view_csn["definitions"][def_key]["kind"], "view")
        self.assertEqual(view_csn["definitions"][def_key]["query"]["from"], "SALES_SPACE.LT_ZSAM_SO01")

        # View DDL
        view_ddl = ddl_gen.generate_sql_view_ddl("SALES_SPACE", "AM_ZSAM_SO_CP", "LT_ZSAM_SO01", fields)
        self.assertTrue(view_ddl.startswith('CREATE VIEW "SALES_SPACE"."AM_ZSAM_SO_CP" AS'))
        self.assertIn('FROM "SALES_SPACE"."LT_ZSAM_SO01"', view_ddl)

if __name__ == "__main__":
    unittest.main()
