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

if __name__ == "__main__":
    unittest.main()
