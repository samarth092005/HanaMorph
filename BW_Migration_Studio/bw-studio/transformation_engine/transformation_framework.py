"""
HANAMORPH BW Migration & Modernization Studio
Transformation Engine Framework & Rule Registry
Milestone M4.2
"""

import hashlib
import json
from typing import Dict, Any, List, Optional
from .abap_parser import ABAPParser
from .sql_translator import ASTSQLTranslator, TranslationResult, TranslationStatus
from .abap_ast import RoutineAST

class RoutineType:
    START_ROUTINE = "START_ROUTINE"
    END_ROUTINE = "END_ROUTINE"
    FIELD_ROUTINE = "FIELD_ROUTINE"
    EXPERT_ROUTINE = "EXPERT_ROUTINE"
    FORMULA = "FORMULA"


class TransformationRule:
    """Represents a defined conversion rule or mapping rule."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: str,
        source_fields: List[str],
        target_field: str,
        abap_code: Optional[str] = None,
        formula_expr: Optional[str] = None
    ):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type.upper()
        self.source_fields = source_fields
        self.target_field = target_field
        self.abap_code = abap_code or ""
        self.formula_expr = formula_expr or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "source_fields": self.source_fields,
            "target_field": self.target_field,
            "abap_code_length": len(self.abap_code),
            "formula_expr": self.formula_expr
        }


class TransformationReport:
    """Detailed assessment and conversion report for a transformation or routine."""
    def __init__(
        self,
        transformation_id: str,
        routine_name: str,
        routine_type: str,
        complexity_score: int,
        conversion_status: str,
        translation_result: TranslationResult,
        ast_summary: Dict[str, Any],
        fingerprint: str
    ):
        self.transformation_id = transformation_id
        self.routine_name = routine_name
        self.routine_type = routine_type
        self.complexity_score = complexity_score
        self.conversion_status = conversion_status
        self.translation_result = translation_result
        self.ast_summary = ast_summary
        self.fingerprint = fingerprint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transformation_id": self.transformation_id,
            "routine_name": self.routine_name,
            "routine_type": self.routine_type,
            "complexity_score": self.complexity_score,
            "conversion_status": self.conversion_status,
            "fingerprint": self.fingerprint,
            "translation": self.translation_result.to_dict(),
            "ast_summary": self.ast_summary
        }


class TransformationFramework:
    """
    Core framework managing routine classification, rule registration,
    and end-to-end ABAP-to-SQL modernizations.
    """

    def __init__(self, target_dialect: str = "HANA_SQL"):
        self.target_dialect = target_dialect
        self.rules: Dict[str, TransformationRule] = {}
        self.parser = ABAPParser()
        self.translator = ASTSQLTranslator(target_dialect=target_dialect)

    def register_rule(self, rule: TransformationRule):
        self.rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[TransformationRule]:
        return self.rules.get(rule_id)

    def classify_routine(self, code: str, default_type: str = RoutineType.FIELD_ROUTINE) -> str:
        """Classifies routine type based on code keywords and structure."""
        upper = code.upper()
        if "SOURCE_PACKAGE" in upper or "DELETE SOURCE_PACKAGE" in upper:
            return RoutineType.START_ROUTINE
        if "RESULT_PACKAGE" in upper:
            return RoutineType.END_ROUTINE
        if "EXPERT" in upper:
            return RoutineType.EXPERT_ROUTINE
        if "RESULT =" in upper or "RESULT=" in upper:
            return RoutineType.FIELD_ROUTINE
        return default_type

    def calculate_complexity(self, ast: RoutineAST) -> int:
        """
        Calculates complexity score from 1 (trivial) to 5 (extreme):
        1: Direct assignment / literal / simple formula
        2: Basic IF/CASE with literals
        3: Nested IF/CASE or string/math functions
        4: Database lookups (SELECT SINGLE)
        5: Unsupported ABAP constructs (LOOP, READ TABLE, CALL FUNCTION)
        """
        has_unsupported = any(isinstance(s, type(s)) and s.__class__.__name__ == "UnsupportedStatement" for s in ast.statements)
        has_lookup = any(isinstance(s, type(s)) and s.__class__.__name__ == "LookupStatement" for s in ast.statements)
        
        if has_unsupported:
            return 5
        if has_lookup:
            return 4
        
        if len(ast.statements) > 5:
            return 3
        
        for s in ast.statements:
            s_name = s.__class__.__name__
            if s_name in ("IfStatement", "CaseStatement"):
                return 2

        return 1

    def process_routine(
        self,
        transformation_id: str,
        routine_name: str,
        code: str,
        declared_type: Optional[str] = None
    ) -> TransformationReport:
        """
        Parses, analyzes, and translates an ABAP routine into modernized SQL.
        Computes deterministic SHA-256 fingerprint for reproducibility.
        """
        routine_type = declared_type or self.classify_routine(code)
        
        # Parse into AST
        ast = self.parser.parse(code, routine_name=routine_name, routine_type=routine_type)
        
        # Calculate complexity
        complexity = self.calculate_complexity(ast)
        
        # Translate AST into SQL
        translation = self.translator.translate_routine(ast)
        
        # Compute deterministic fingerprint
        fingerprint_data = {
            "transformation_id": transformation_id,
            "routine_name": routine_name,
            "routine_type": routine_type,
            "raw_code": code.strip(),
            "status": translation.status,
            "ast_nodes": len(ast.statements)
        }
        raw_bytes = json.dumps(fingerprint_data, sort_keys=True).encode("utf-8")
        fingerprint = hashlib.sha256(raw_bytes).hexdigest()

        ast_summary = {
            "total_statements": len(ast.statements),
            "node_types": [type(s).__name__ for s in ast.statements],
            "unsupported_count": len(translation.unsupported_statements)
        }

        return TransformationReport(
            transformation_id=transformation_id,
            routine_name=routine_name,
            routine_type=routine_type,
            complexity_score=complexity,
            conversion_status=translation.status,
            translation_result=translation,
            ast_summary=ast_summary,
            fingerprint=fingerprint
        )
