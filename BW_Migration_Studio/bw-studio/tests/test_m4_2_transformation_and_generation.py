"""
HANAMORPH BW Migration & Modernization Studio
M4.2 Transformation Engine & Target Generation Test Suite
"""

import unittest
import os
import sys
import json

# Ensure bw-studio root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transformation_engine.abap_ast import (
    Literal, Identifier, BinaryOp, UnaryOp, FunctionCall,
    Assignment, IfStatement, CaseStatement, LookupStatement,
    UnsupportedStatement, RoutineAST
)
from transformation_engine.abap_parser import ABAPParser
from transformation_engine.sql_translator import (
    ASTSQLTranslator, TranslationStatus
)
from transformation_engine.transformation_framework import (
    TransformationFramework, TransformationRule, RoutineType
)
from generation_engine.replication_flow_generator import DatasphereReplicationFlowGenerator
from generation_engine.sac_model_generator import SACAnalyticalModelGenerator
from generation_engine.csn_generator import DatasphereCSNGenerator


class TestM42TransformationAndGeneration(unittest.TestCase):

    def setUp(self):
        self.parser = ABAPParser()
        self.translator = ASTSQLTranslator(target_dialect="HANA_SQL")
        self.framework = TransformationFramework(target_dialect="HANA_SQL")
        self.repl_gen = DatasphereReplicationFlowGenerator()
        self.sac_gen = SACAnalyticalModelGenerator()
        self.csn_gen = DatasphereCSNGenerator()

    # -------------------------------------------------------------
    # 1. AST Model Unit Tests
    # -------------------------------------------------------------
    def test_01_ast_node_serialization(self):
        lit = Literal(100.5, "DECIMAL")
        self.assertEqual(lit.to_dict()["node_type"], "Literal")
        self.assertEqual(lit.to_dict()["value"], 100.5)

        ident = Identifier("SOURCE_FIELDS-NETWR")
        self.assertEqual(ident.to_dict()["name"], "SOURCE_FIELDS-NETWR")

        bin_op = BinaryOp(ident, "*", Literal(1.2, "DECIMAL"))
        b_dict = bin_op.to_dict()
        self.assertEqual(b_dict["node_type"], "BinaryOp")
        self.assertEqual(b_dict["op"], "*")

        func = FunctionCall("ROUND", [bin_op, Literal(2, "INTEGER")])
        self.assertEqual(func.to_dict()["func_name"], "ROUND")
        self.assertEqual(len(func.to_dict()["args"]), 2)

    # -------------------------------------------------------------
    # 2. ABAP Parser Unit Tests
    # -------------------------------------------------------------
    def test_02_parse_direct_assignment(self):
        code = "RESULT = SOURCE_FIELDS-NETWR."
        ast = self.parser.parse(code, routine_name="ROUT_NETWR")
        self.assertEqual(len(ast.statements), 1)
        self.assertIsInstance(ast.statements[0], Assignment)
        self.assertEqual(ast.statements[0].target.name, "RESULT")
        self.assertEqual(ast.statements[0].value.name, "SOURCE_FIELDS-NETWR")

    def test_03_parse_if_elseif_else(self):
        code = """
        IF SOURCE_FIELDS-CURRENCY = 'EUR'.
          RESULT = SOURCE_FIELDS-AMOUNT * 1.1.
        ELSEIF SOURCE_FIELDS-CURRENCY = 'GBP'.
          RESULT = SOURCE_FIELDS-AMOUNT * 1.3.
        ELSE.
          RESULT = SOURCE_FIELDS-AMOUNT.
        ENDIF.
        """
        ast = self.parser.parse(code, routine_name="ROUT_CURR_CONV")
        self.assertEqual(len(ast.statements), 1)
        stmt = ast.statements[0]
        self.assertIsInstance(stmt, IfStatement)
        self.assertEqual(len(stmt.elseif_branches), 1)
        self.assertEqual(len(stmt.else_body), 1)

    def test_04_parse_case_when(self):
        code = """
        CASE SOURCE_FIELDS-DOCTYPE.
          WHEN 'OR'.
            RESULT = 'STANDARD_ORDER'.
          WHEN 'RE'.
            RESULT = 'RETURN_ORDER'.
          WHEN OTHERS.
            RESULT = 'OTHER'.
        ENDCASE.
        """
        ast = self.parser.parse(code, routine_name="ROUT_DOCTYPE")
        self.assertEqual(len(ast.statements), 1)
        stmt = ast.statements[0]
        self.assertIsInstance(stmt, CaseStatement)
        self.assertEqual(len(stmt.when_branches), 2)
        self.assertEqual(len(stmt.when_others_body), 1)

    def test_05_parse_select_single_lookup(self):
        code = "SELECT SINGLE KTEXT FROM CSKT INTO L_TEXT WHERE KOSTL = SOURCE_FIELDS-KOSTL."
        ast = self.parser.parse(code, routine_name="ROUT_KOSTL_LOOKUP")
        self.assertEqual(len(ast.statements), 1)
        stmt = ast.statements[0]
        self.assertIsInstance(stmt, LookupStatement)
        self.assertEqual(stmt.source_table, "CSKT")
        self.assertEqual(stmt.select_field, "KTEXT")
        self.assertEqual(stmt.where_field, "KOSTL")

    def test_06_unsupported_abap_detection(self):
        code = """
        READ TABLE ITAB WITH KEY ID = '100'.
        CALL FUNCTION 'CONVERT_TO_LOCAL_CURRENCY'.
        """
        ast = self.parser.parse(code, routine_name="ROUT_UNSUPPORTED")
        self.assertGreaterEqual(len(ast.statements), 2)
        for s in ast.statements:
            self.assertIsInstance(s, UnsupportedStatement)
            self.assertTrue(s.reason)
            self.assertTrue(s.suggested_action)

    # -------------------------------------------------------------
    # 3. AST SQL Translator Unit Tests
    # -------------------------------------------------------------
    def test_07_translate_field_routine_to_column_expression(self):
        code = """
        IF SOURCE_FIELDS-STATUS = 'A'.
          RESULT = 'ACTIVE'.
        ELSE.
          RESULT = 'INACTIVE'.
        ENDIF.
        """
        ast = self.parser.parse(code, routine_name="ROUT_STATUS")
        res = self.translator.translate_routine(ast)
        self.assertEqual(res.status, TranslationStatus.AUTOMATICALLY_CONVERTED)
        self.assertIsNotNone(res.expression_sql)
        self.assertIn("CASE", res.expression_sql)
        self.assertIn("'ACTIVE'", res.expression_sql)
        self.assertIn("'INACTIVE'", res.expression_sql)

    def test_08_translate_partially_converted_routine(self):
        code = """
        RESULT = SOURCE_FIELDS-NETWR.
        LOOP AT ITAB INTO WA.
        ENDLOOP.
        """
        ast = self.parser.parse(code, routine_name="ROUT_PARTIAL")
        res = self.translator.translate_routine(ast)
        self.assertEqual(res.status, TranslationStatus.PARTIALLY_CONVERTED)
        self.assertEqual(len(res.unsupported_statements), 1)
        self.assertIn("MANUAL REVIEW REQUIRED", res.procedure_sql)

    # -------------------------------------------------------------
    # 4. Transformation Framework Unit Tests
    # -------------------------------------------------------------
    def test_09_transformation_framework_end_to_end(self):
        code = "RESULT = SOURCE_FIELDS-AMOUNT * 1.18."
        report = self.framework.process_routine(
            transformation_id="TR_001",
            routine_name="ROUT_VAT",
            code=code
        )
        self.assertEqual(report.conversion_status, TranslationStatus.AUTOMATICALLY_CONVERTED)
        self.assertEqual(report.complexity_score, 1)
        self.assertEqual(len(report.fingerprint), 64) # Valid SHA-256

        rep_dict = report.to_dict()
        self.assertIn("translation", rep_dict)
        self.assertIn("ast_summary", rep_dict)

    # -------------------------------------------------------------
    # 5. Dedicated Target Generators Unit Tests
    # -------------------------------------------------------------
    def test_10_datasphere_replication_flow_generator(self):
        fields = [
            {"field_name": "DOC_NUM", "data_type": "CHAR", "is_key": True},
            {"field_name": "NET_AMOUNT", "data_type": "CURR", "is_key": False}
        ]
        spec = self.repl_gen.generate_replication_flow(
            space="FIN_SPACE",
            source_object="ZSAM_SO01",
            target_name="LT_ZSAM_SO01",
            fields=fields
        )
        self.assertEqual(spec["flow_id"], "RF_ZSAM_SO01_TO_LT_ZSAM_SO01")
        self.assertEqual(spec["replication_settings"]["load_type"], "INITIAL_AND_DELTA")
        self.assertEqual(len(spec["mappings"]), 2)
        self.assertIn("provenance", spec)
        self.assertEqual(len(spec["provenance"]["content_sha256"]), 64)

    def test_11_sac_analytical_model_generator(self):
        fields = [
            {"field_name": "CALDAY", "data_type": "DATS", "is_key": True},
            {"field_name": "REGION", "data_type": "CHAR", "is_key": False},
            {"field_name": "REVENUE", "data_type": "CURR", "aggregation_type": "SUM", "decimals": 2}
        ]
        spec = self.sac_gen.generate_sac_model(
            model_name="SAC_AM_SALES",
            source_object="CV_SALES",
            base_view_id="SALES_SPACE.CV_SALES",
            fields=fields
        )
        self.assertEqual(spec["model_id"], "SAC_AM_SALES")
        self.assertEqual(len(spec["measures"]), 1)
        self.assertEqual(spec["measures"][0]["id"], "REVENUE")
        self.assertEqual(len(spec["dimensions"]), 2)
        self.assertEqual(len(spec["provenance"]["content_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
