"""
HANAMORPH BW Migration & Modernization Studio
ABAP AST to SQL Translator (HANA SQL & Datasphere View Expression)
Milestone M4.2
"""

from typing import Dict, Any, List, Optional, Tuple
from .abap_ast import (
    ASTNode, Expression, Literal, Identifier, BinaryOp, UnaryOp,
    FunctionCall, Statement, Assignment, IfStatement, CaseStatement,
    LookupStatement, UnsupportedStatement, RoutineAST
)

class TranslationStatus:
    AUTOMATICALLY_CONVERTED = "AUTOMATICALLY_CONVERTED"
    PARTIALLY_CONVERTED = "PARTIALLY_CONVERTED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class TranslationResult:
    def __init__(
        self,
        status: str,
        target_dialect: str,
        expression_sql: Optional[str] = None,
        procedure_sql: Optional[str] = None,
        converted_statements_count: int = 0,
        unsupported_statements: Optional[List[Dict[str, Any]]] = None,
        confidence_score: float = 0.0,
        notes: Optional[List[str]] = None
    ):
        self.status = status
        self.target_dialect = target_dialect
        self.expression_sql = expression_sql
        self.procedure_sql = procedure_sql
        self.converted_statements_count = converted_statements_count
        self.unsupported_statements = unsupported_statements or []
        self.confidence_score = round(confidence_score, 2)
        self.notes = notes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "target_dialect": self.target_dialect,
            "expression_sql": self.expression_sql,
            "procedure_sql": self.procedure_sql,
            "converted_statements_count": self.converted_statements_count,
            "unsupported_statements": self.unsupported_statements,
            "confidence_score": self.confidence_score,
            "notes": self.notes
        }


class ASTSQLTranslator:
    """
    Translates ABAP Routine AST into SAP HANA SQL or SAP Datasphere SQL/Expressions.
    Supports Field Routines, Start/End Routines, and Lookups.
    """

    OPERATOR_MAP = {
        "=": "=",
        "EQ": "=",
        "<>": "<>",
        "NE": "<>",
        "<": "<",
        "LT": "<",
        "<=": "<=",
        "LE": "<=",
        ">": ">",
        "GT": ">",
        ">=": ">=",
        "GE": ">=",
        "AND": "AND",
        "OR": "OR",
        "+": "+",
        "-": "-",
        "*": "*",
        "/": "/",
        "CONCAT": "||",
        "LIKE": "LIKE",
        "IN": "IN"
    }

    FUNCTION_MAP = {
        "STRLEN": "LENGTH",
        "SUBSTRING": "SUBSTRING",
        "TO_UPPER": "UPPER",
        "TO_LOWER": "LOWER",
        "TRIM": "TRIM",
        "ABS": "ABS",
        "ROUND": "ROUND",
        "FLOOR": "FLOOR",
        "CEIL": "CEIL",
        "COALESCE": "COALESCE",
        "CONCAT": "CONCAT"
    }

    def __init__(self, target_dialect: str = "HANA_SQL"):
        self.target_dialect = target_dialect.upper()
        self.unsupported_items: List[Dict[str, Any]] = []
        self.notes: List[str] = []

    def translate_routine(self, routine: RoutineAST) -> TranslationResult:
        """Translates a full routine AST into SQL."""
        self.unsupported_items = []
        self.notes = []

        total_statements = len(routine.statements)
        if total_statements == 0:
            return TranslationResult(
                status=TranslationStatus.AUTOMATICALLY_CONVERTED,
                target_dialect=self.target_dialect,
                expression_sql="NULL",
                confidence_score=1.0,
                notes=["Empty routine converted to NULL expression."]
            )

        # Inspect all statements for unsupported constructs
        unsupported_count = 0
        converted_count = 0

        for stmt in routine.statements:
            if isinstance(stmt, UnsupportedStatement):
                unsupported_count += 1
                self.unsupported_items.append(stmt.to_dict())

        # If it's a simple field routine with single return or case
        if routine.routine_type == "FIELD_ROUTINE" and unsupported_count == 0:
            # Check if we can generate a single clean SQL expression (for Datasphere or HANA column)
            single_expr = self._try_translate_field_routine_expression(routine.statements)
            if single_expr:
                return TranslationResult(
                    status=TranslationStatus.AUTOMATICALLY_CONVERTED,
                    target_dialect=self.target_dialect,
                    expression_sql=single_expr,
                    converted_statements_count=total_statements,
                    confidence_score=0.98,
                    notes=["Translated into declarative SQL column expression."]
                )

        # Multi-statement or procedural routine (e.g. Start/End routine, lookups)
        proc_sql, converted_stmts = self._translate_procedural_body(routine.statements)
        converted_count = converted_stmts

        if unsupported_count > 0:
            if converted_count > 0:
                status = TranslationStatus.PARTIALLY_CONVERTED
                confidence = max(0.2, (converted_count / (converted_count + unsupported_count)) * 0.7)
            else:
                status = TranslationStatus.UNSUPPORTED
                confidence = 0.0
        else:
            status = TranslationStatus.AUTOMATICALLY_CONVERTED
            confidence = 0.95

        return TranslationResult(
            status=status,
            target_dialect=self.target_dialect,
            expression_sql=None,
            procedure_sql=proc_sql,
            converted_statements_count=converted_count,
            unsupported_statements=self.unsupported_items,
            confidence_score=confidence,
            notes=self.notes
        )

    def _try_translate_field_routine_expression(self, statements: List[Statement]) -> Optional[str]:
        """Tries to collapse statements into a single SELECT column expression."""
        if len(statements) == 1:
            stmt = statements[0]
            if isinstance(stmt, Assignment):
                return self.translate_expression(stmt.value)
            if isinstance(stmt, (IfStatement, CaseStatement)):
                return self.translate_statement(stmt)
        elif len(statements) == 2 and isinstance(statements[0], Assignment) and isinstance(statements[1], (IfStatement, CaseStatement)):
            # Common pattern: RESULT = SOURCE_FIELDS-FIELD. IF ... RESULT = ...
            return self.translate_statement(statements[1])
        return None

    def _translate_procedural_body(self, statements: List[Statement]) -> Tuple[str, int]:
        """Translates a block of statements into SQL / SQLScript lines."""
        lines = []
        converted_count = 0

        for stmt in statements:
            if isinstance(stmt, UnsupportedStatement):
                lines.append(f"-- [MANUAL REVIEW REQUIRED] Line {stmt.line_number}: {stmt.raw_code}")
                lines.append(f"-- Reason: {stmt.reason}")
                if stmt.suggested_action:
                    lines.append(f"-- Action: {stmt.suggested_action}")
                continue

            sql_part = self.translate_statement(stmt)
            if sql_part:
                lines.append(sql_part)
                converted_count += 1

        body = "\n".join(lines)
        return body, converted_count

    def translate_statement(self, stmt: Statement) -> str:
        """Translates a single statement node."""
        if isinstance(stmt, Assignment):
            target_col = self._clean_identifier(stmt.target.name)
            val_expr = self.translate_expression(stmt.value)
            return f"{target_col} = {val_expr};"

        elif isinstance(stmt, IfStatement):
            cond_sql = self.translate_expression(stmt.condition)
            then_expr = self._statement_list_to_expr_or_block(stmt.then_body)
            
            sql = f"CASE\n  WHEN {cond_sql} THEN {then_expr}"
            for cond, body in stmt.elseif_branches:
                elif_cond = self.translate_expression(cond)
                elif_expr = self._statement_list_to_expr_or_block(body)
                sql += f"\n  WHEN {elif_cond} THEN {elif_expr}"

            if stmt.else_body:
                else_expr = self._statement_list_to_expr_or_block(stmt.else_body)
                sql += f"\n  ELSE {else_expr}"
            else:
                sql += "\n  ELSE NULL"
            sql += "\nEND"
            return sql

        elif isinstance(stmt, CaseStatement):
            case_val = self.translate_expression(stmt.case_expr)
            sql = f"CASE {case_val}"
            for val_expr, body in stmt.when_branches:
                w_sql = self.translate_expression(val_expr)
                b_sql = self._statement_list_to_expr_or_block(body)
                sql += f"\n  WHEN {w_sql} THEN {b_sql}"

            if stmt.when_others_body:
                o_sql = self._statement_list_to_expr_or_block(stmt.when_others_body)
                sql += f"\n  ELSE {o_sql}"
            else:
                sql += "\n  ELSE NULL"
            sql += "\nEND"
            return sql

        elif isinstance(stmt, LookupStatement):
            target_var = self._clean_identifier(stmt.target_var.name)
            conditions = stmt.where_conditions if hasattr(stmt, "where_conditions") and stmt.where_conditions else [(stmt.where_field, stmt.key_expr)]
            cond_clauses = []
            for wf, kexpr in conditions:
                if isinstance(kexpr, Identifier) and ("-" in kexpr.name or kexpr.name.upper().startswith("SOURCE_FIELDS")):
                    col_name = kexpr.name.split("-", 1)[1] if "-" in kexpr.name else kexpr.name
                    rhs = f":SOURCE.{col_name}"
                else:
                    rhs = self.translate_expression(kexpr, context="PROCEDURAL")
                cond_clauses.append(f"{wf} = {rhs}")
            where_sql = " AND ".join(cond_clauses)
            return (
                f"-- Database Lookup for {target_var}\n"
                f"SELECT {stmt.select_field} INTO {target_var} FROM {stmt.source_table} "
                f"WHERE {where_sql};"
            )

        elif isinstance(stmt, UnsupportedStatement):
            return f"-- [MANUAL_REVIEW] {stmt.reason}: {stmt.raw_code}"

        return f"-- Unrecognized statement: {type(stmt).__name__}"

    def _statement_list_to_expr_or_block(self, stmts: List[Statement]) -> str:
        if not stmts:
            return "NULL"
        if len(stmts) == 1 and isinstance(stmts[0], Assignment):
            return self.translate_expression(stmts[0].value)
        # Multiple statements in a branch
        converted = []
        for s in stmts:
            converted.append(self.translate_statement(s))
        return " ".join(converted)

    def translate_expression(self, expr: Expression, context: str = "EXPRESSION") -> str:
        """Translates an expression node into SQL syntax."""
        if isinstance(expr, Literal):
            if expr.data_type == "STRING":
                # Escape single quotes
                safe_val = str(expr.value).replace("'", "''")
                return f"'{safe_val}'"
            return str(expr.value)

        elif isinstance(expr, Identifier):
            if context == "PROCEDURAL" and ("-" in expr.name or expr.name.upper().startswith("SOURCE_FIELDS")):
                col_name = expr.name.split("-", 1)[1] if "-" in expr.name else expr.name
                return f":SOURCE.{col_name}"
            return self._clean_identifier(expr.name)

        elif isinstance(expr, BinaryOp):
            left_sql = self.translate_expression(expr.left, context)
            right_sql = self.translate_expression(expr.right, context)
            op_sql = self.OPERATOR_MAP.get(expr.op, expr.op)
            if op_sql == "||":
                return f"{left_sql} || {right_sql}"
            return f"({left_sql} {op_sql} {right_sql})"

        elif isinstance(expr, UnaryOp):
            sub_sql = self.translate_expression(expr.expr, context)
            op = expr.op
            if op == "NOT":
                return f"NOT ({sub_sql})"
            return f"{op}({sub_sql})"

        elif isinstance(expr, FunctionCall):
            if expr.func_name == "CONCATENATE":
                args_sql = [self.translate_expression(a, context) for a in expr.args]
                sep = getattr(expr, "separator", None)
                if sep is not None:
                    safe_sep = sep.replace("'", "''")
                    joiner = f" || '{safe_sep}' || "
                    return joiner.join(args_sql)
                else:
                    return " || ".join(args_sql)

            fname = self.FUNCTION_MAP.get(expr.func_name, expr.func_name)
            args_sql = [self.translate_expression(a, context) for a in expr.args]
            return f"{fname}({', '.join(args_sql)})"

        return "NULL"

    def _clean_identifier(self, name: str) -> str:
        """Cleans ABAP structure prefixes like SOURCE_FIELDS-FIELD or RESULT."""
        clean = name.strip()
        if "-" in clean:
            # e.g. SOURCE_FIELDS-NETWR -> NETWR or in SQL "SOURCE_FIELDS"."NETWR"
            parts = clean.split("-", 1)
            return parts[1]
        if clean.upper() == "RESULT":
            return "RESULT"
        return clean
