"""
Unit Tests for Canonical Metadata Model & URN Identity Engine
Milestone M1.2 Verification
"""

import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.canonical_model import CanonicalURN, CanonicalField, CanonicalObject

class TestCanonicalModel(unittest.TestCase):

    def test_canonical_urn_formatting(self):
        urn = CanonicalURN(
            system_id="S21",
            client="200",
            object_type="ADSO",
            technical_name="ZSAM_SO01",
            version="A"
        )
        self.assertEqual(urn.system_id, "s21")
        self.assertEqual(urn.client, "200")
        self.assertEqual(urn.object_type, "adso")
        self.assertEqual(urn.version, "A")
        self.assertEqual(urn.stable_urn, "urn:sap:bw:s21:200:adso:ZSAM_SO01")
        self.assertEqual(urn.versioned_urn, "urn:sap:bw:s21:200:adso:ZSAM_SO01:A")
        self.assertEqual(str(urn), "urn:sap:bw:s21:200:adso:ZSAM_SO01:A")

    def test_canonical_urn_namespaced_escaping(self):
        # Partner/customer namespace with slashes
        urn = CanonicalURN(
            system_id="p01",
            client="100",
            object_type="HCPR",
            technical_name="/COMPANY/SALES_CP01",
            version="M"
        )
        self.assertEqual(urn.escaped_name, "%2FCOMPANY%2FSALES_CP01")
        self.assertEqual(urn.stable_urn, "urn:sap:bw:p01:100:hcpr:%2FCOMPANY%2FSALES_CP01")
        self.assertEqual(urn.versioned_urn, "urn:sap:bw:p01:100:hcpr:%2FCOMPANY%2FSALES_CP01:M")

    def test_canonical_urn_client_normalization(self):
        # 1-digit and 2-digit clients zero-padded
        urn1 = CanonicalURN("s21", "1", "adso", "TEST")
        self.assertEqual(urn1.client, "001")
        urn2 = CanonicalURN("s21", "20", "adso", "TEST")
        self.assertEqual(urn2.client, "020")
        urn3 = CanonicalURN("s21", "200", "adso", "TEST")
        self.assertEqual(urn3.client, "200")

    def test_canonical_urn_parsing(self):
        parsed = CanonicalURN.parse("urn:sap:bw:s21:200:adso:%2FCOMPANY%2FSALES_CP01:A")
        self.assertEqual(parsed.system_id, "s21")
        self.assertEqual(parsed.client, "200")
        self.assertEqual(parsed.object_type, "adso")
        self.assertEqual(parsed.raw_technical_name, "/COMPANY/SALES_CP01")
        self.assertEqual(parsed.version, "A")

        # Parsing stable URN (defaults to 'A' version)
        parsed_stable = CanonicalURN.parse("urn:sap:bw:s21:200:adso:ZSAM_SO01")
        self.assertEqual(parsed_stable.version, "A")
        self.assertEqual(parsed_stable.raw_technical_name, "ZSAM_SO01")

    def test_content_fingerprint_deterministic_and_timestamp_agnostic(self):
        # Two objects with identical fields but different timestamps must have identical fingerprints
        f1 = CanonicalField("ORDER_ID", "CHAR", position=1, length=10, is_key=True)
        f2 = CanonicalField("AMOUNT", "CURR", position=2, length=15, decimals=2, currency_unit_field="CURRENCY")

        obj1 = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            description="Sales Order ADSO",
            fields=[f1, f2],
            extracted_at="2026-11-21T10:00:00Z"
        )
        obj2 = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            description="Sales Order ADSO",
            fields=[f1, f2],
            extracted_at="2026-11-21T18:30:00Z"
        )
        self.assertEqual(obj1.content_fingerprint, obj2.content_fingerprint)
        self.assertTrue(len(obj1.content_fingerprint) == 64)  # SHA-256 hex string

    def test_content_fingerprint_detects_mutation_with_same_timestamp(self):
        # Two objects with identical timestamp but mutated field must have different fingerprints
        f1 = CanonicalField("ORDER_ID", "CHAR", position=1, length=10, is_key=True)
        f2_orig = CanonicalField("AMOUNT", "CURR", position=2, length=15, decimals=2)
        f2_mutated = CanonicalField("AMOUNT", "CURR", position=2, length=17, decimals=2)  # length changed

        obj_orig = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            fields=[f1, f2_orig],
            extracted_at="2026-11-21T12:00:00Z"
        )
        obj_mutated = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            fields=[f1, f2_mutated],
            extracted_at="2026-11-21T12:00:00Z"
        )
        self.assertNotEqual(obj_orig.content_fingerprint, obj_mutated.content_fingerprint)

    def test_provenance_and_confidence_bounds(self):
        obj = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZTEST:A",
            provenance="OFFLINE_FIXTURE",
            confidence_score=1.5,   # Should clamp to 1.0
            completeness_score=-0.2 # Should clamp to 0.0
        )
        self.assertEqual(obj.provenance, "OFFLINE_FIXTURE")
        self.assertEqual(obj.confidence_score, 1.0)
        self.assertEqual(obj.completeness_score, 0.0)

    def test_content_fingerprint_package_sensitivity(self):
        # Condition C-03: Package changes must alter fingerprint
        obj_tmp = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            description="Sales Order ADSO",
            package="$TMP"
        )
        obj_pkg = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            description="Sales Order ADSO",
            package="Z_BW_FINANCE"
        )
        self.assertNotEqual(obj_tmp.content_fingerprint, obj_pkg.content_fingerprint)
        
        # Deterministic identical package produces identical hash
        obj_pkg2 = CanonicalObject(
            urn="urn:sap:bw:s21:200:adso:ZSAM_SO01:A",
            description="Sales Order ADSO",
            package="Z_BW_FINANCE"
        )
        self.assertEqual(obj_pkg.content_fingerprint, obj_pkg2.content_fingerprint)

if __name__ == "__main__":
    unittest.main()
