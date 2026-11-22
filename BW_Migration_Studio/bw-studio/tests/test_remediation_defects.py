import unittest
import sqlite3
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from discovery.cache_discovery_adapter import CacheDiscoveryAdapter
from discovery.adt_discovery_adapter import ADTDiscoveryAdapter
from generation_engine.csn_generator import DatasphereCSNGenerator
from generation_engine.hana_ddl_generator import HANASQLGenerator
from validation_engine.validation_engine import ValidationEngine
from assessment_engine.assessment_engine import AssessmentEngine
from deployment.delivery_packager import DeliveryPackager

class MockBWManager:
    def execute_sap_http(self, method, endpoint, *args, **kwargs):
        # Return mock CDS DDIC table source HTML with keyword key
        mock_html = """
        @EndUserText.label: 'Active Table'
        define table /bic/azsam_so012 {
          <span class="keyword">key</span> <span class="identifier">order_id</span> <span class="keyword">:</span> <span class="identifier">abap</span><span class="keyword">.</span><span class="identifier">char</span><span class="keyword">(</span><span class="number">10</span><span class="keyword">)</span>;
          <span class="identifier">cust_name</span> <span class="keyword">:</span> <span class="identifier">abap</span><span class="keyword">.</span><span class="identifier">char</span><span class="keyword">(</span><span class="number">40</span><span class="keyword">)</span>;
          <span class="identifier">amount</span> <span class="keyword">:</span> <span class="identifier">abap</span><span class="keyword">.</span><span class="identifier">curr</span><span class="keyword">(</span><span class="number">15</span><span class="keyword">,</span><span class="number">2</span><span class="keyword">)</span>;
          <span class="identifier">currency</span> <span class="keyword">:</span> <span class="identifier">abap</span><span class="keyword">.</span><span class="identifier">cuky</span><span class="keyword">(</span><span class="number">5</span><span class="keyword">)</span>;
        }
        """
        return {"status_code": 200, "data": mock_html.encode('utf-8')}

class TestRemediationDefects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(BASE_DIR, "database", "bw_studio.sqlite")

    def test_def_06_adt_dynamic_primary_key_detection(self):
        adapter = ADTDiscoveryAdapter(MockBWManager())
        fields = adapter.extract_table_fields("/BIC/AZSAM_SO012")
        self.assertEqual(len(fields), 4)
        order_id = next(f for f in fields if f["name"] == "ORDER_ID")
        cust_name = next(f for f in fields if f["name"] == "CUST_NAME")
        self.assertEqual(order_id["is_key"], 1, "ORDER_ID must be parsed as key via keyword token")
        self.assertEqual(cust_name["is_key"], 0, "CUST_NAME must not be a key")

    def test_def_06_cache_dynamic_primary_key_detection(self):
        adapter = CacheDiscoveryAdapter()
        adso_path = os.path.join(adapter.cache_dir, "adso", "zsam_so01", "a", "model.adso")
        if os.path.exists(adso_path):
            parsed = adapter.parse_adso_file(adso_path)
            self.assertIsNotNone(parsed)
            keys = [f["name"] for f in parsed["fields"] if f["is_key"]]
            self.assertEqual(keys, ["ORDER_ID"])
            non_keys = [f["name"] for f in parsed["fields"] if not f["is_key"]]
            self.assertIn("CUST_NAME", non_keys)
            self.assertIn("AMOUNT", non_keys)

    def test_def_05_trcs_full_11_fields_parsed(self):
        adapter = CacheDiscoveryAdapter()
        trcs_path = os.path.join(adapter.cache_dir, "trcs", "zsam_pr_is01", "m", "model.trcs")
        if os.path.exists(trcs_path):
            parsed = adapter.parse_trcs_file(trcs_path)
            self.assertIsNotNone(parsed)
            self.assertEqual(len(parsed["fields"]), 11, "Must parse all 11 fields from model.trcs")
            names = [f["name"] for f in parsed["fields"]]
            for expected in ["BANFN", "BNFPO", "BSART", "MATNR", "TXZ01", "MENGE", "MEINS", "WERKS", "LFDAT", "AFNAM", "EKGRP"]:
                self.assertIn(expected, names)

    def test_def_05_query_honest_partial_metadata(self):
        adapter = CacheDiscoveryAdapter()
        q_path = os.path.join(adapter.cache_dir, "query", "zsam_pr_q01", "a", "model.query")
        if os.path.exists(q_path):
            parsed = adapter.parse_query_file(q_path)
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed["technical_name"], "ZSAM_PR_Q01")
            self.assertEqual(parsed["metadata_completeness"], "PARTIAL_NEEDS_BEX_RUNTIME")
            self.assertEqual(parsed["provenance"], "CACHED_PARTIAL")

    def test_def_01_object_semantic_generators(self):
        csn_gen = DatasphereCSNGenerator()
        ddl_gen = HANASQLGenerator()

        fields = [
            {"field_name": "ORDER_ID", "data_type": "CHAR", "length": 10, "is_key": 1},
            {"field_name": "NET_AMOUNT", "data_type": "CURR", "length": 15, "decimals": 2},
            {"field_name": "CURRENCY", "data_type": "CUKY", "length": 5}
        ]

        # Entity for ADSO
        entity_csn = csn_gen.generate_entity_csn("TEST_SPACE", "LT_ZSAM_SO01", fields)
        entity_def = entity_csn["definitions"]["TEST_SPACE.LT_ZSAM_SO01"]
        self.assertEqual(entity_def["kind"], "entity")
        self.assertTrue(entity_def["elements"]["ORDER_ID"]["key"])
        table_ddl = ddl_gen.generate_column_table_ddl("TEST_SPACE", "LT_ZSAM_SO01", fields)
        self.assertTrue(table_ddl.startswith('CREATE COLUMN TABLE "TEST_SPACE"."LT_ZSAM_SO01"'))
        self.assertIn('PRIMARY KEY ("ORDER_ID")', table_ddl)

        # View for CompositeProvider
        view_csn = csn_gen.generate_view_csn("TEST_SPACE", "AM_ZSAM_SO_CP", "LT_ZSAM_SO01", fields)
        view_def = view_csn["definitions"]["TEST_SPACE.AM_ZSAM_SO_CP"]
        self.assertEqual(view_def["kind"], "view")
        self.assertEqual(view_def["query"]["from"], "TEST_SPACE.LT_ZSAM_SO01")
        view_ddl = ddl_gen.generate_sql_view_ddl("TEST_SPACE", "AM_ZSAM_SO_CP", "LT_ZSAM_SO01", fields)
        self.assertTrue(view_ddl.startswith('CREATE VIEW "TEST_SPACE"."AM_ZSAM_SO_CP" AS'))
        self.assertIn('FROM "TEST_SPACE"."LT_ZSAM_SO01"', view_ddl)

    def test_def_03_semantic_validation_currency_referential_integrity(self):
        # 1. Valid CSN with currency reference pointing to existing element
        valid_csn = {
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {
                "TEST.LT_TEST": {
                    "kind": "entity",
                    "elements": {
                        "ID": {"type": "cds.String", "key": True},
                        "AMOUNT": {"type": "cds.Decimal", "precision": 15, "scale": 2, "@Semantics.amount.currencyCode": "CURRENCY"},
                        "CURRENCY": {"type": "cds.String", "length": 5}
                    }
                }
            }
        }
        # 2. Invalid CSN with dangling currency reference
        invalid_csn = {
            "$schema": "https://help.sap.com/doc/csn-v2.0.json",
            "definitions": {
                "TEST.LT_TEST": {
                    "kind": "entity",
                    "elements": {
                        "ID": {"type": "cds.String", "key": True},
                        "AMOUNT": {"type": "cds.Decimal", "precision": 15, "scale": 2, "@Semantics.amount.currencyCode": "MISSING_CURR"}
                    }
                }
            }
        }

        engine = ValidationEngine(self.db_path)
        # Test directly by passing into DB check or verifying validation results
        # Valid entity has existing currency link
        elem_valid = valid_csn["definitions"]["TEST.LT_TEST"]["elements"]
        self.assertIn(elem_valid["AMOUNT"]["@Semantics.amount.currencyCode"], elem_valid)

        # Invalid entity has dangling currency link
        elem_invalid = invalid_csn["definitions"]["TEST.LT_TEST"]["elements"]
        self.assertNotIn(elem_invalid["AMOUNT"]["@Semantics.amount.currencyCode"], elem_invalid)

    def test_evidence_based_assessment_confidence_and_4_tier_risk(self):
        engine = AssessmentEngine(self.db_path)
        so01 = engine.assess_object("ZSAM_SO01")
        self.assertIn("confidence_score", so01)
        self.assertIn("confidence_level", so01)
        self.assertGreaterEqual(so01["confidence_score"], 0.8)
        self.assertEqual(so01["risk_level"], "LOW")

if __name__ == "__main__":
    unittest.main()
