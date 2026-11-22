"""
HANAMORPH BW Migration & Modernization Studio
ABAP Routine AST Lexer and Parser
Milestone M4.2
"""

import re
from typing import List, Optional, Tuple
from .abap_ast import (
    RoutineAST, Statement, Expression, Literal, Identifier, BinaryOp,
    UnaryOp, FunctionCall, Assignment, IfStatement, CaseStatement,
    LookupStatement, UnsupportedStatement
)

class ABAPParser:
    """
    Parser for SAP BW Transformation ABAP Routines.
    Converts ABAP statements into a structured Intermediate Representation (AST).
    Accurately classifies supported constructs vs. unsupported constructs.
    """
    def __init__(self):
        pass

    def parse_routine(self, routine_name: str, code: str, routine_type: str = "FIELD_ROUTINE") -> RoutineAST:
        """Parses routine source code into a RoutineAST."""
        lines = code.splitlines()
        statements: List[Statement] = []
        clean_tokens = self._tokenize(lines)
        
        idx = 0
        while idx < len(clean_tokens):
            stmt, next_idx = self._parse_statement(clean_tokens, idx)
            if stmt:
                statements.append(stmt)
            idx = next_idx

        return RoutineAST(routine_name=routine_name, routine_type=routine_type, statements=statements)

    def parse(self, code: str, routine_name: str = "ANONYMOUS", routine_type: str = "FIELD_ROUTINE") -> RoutineAST:
        """Convenience method parsing code with optional routine name and type."""
        return self.parse_routine(routine_name=routine_name, code=code, routine_type=routine_type)

    def _tokenize(self, lines: List[str]) -> List[Tuple[str, int]]:
        """Cleans comments and splits text into period-terminated ABAP statements with line numbers."""
        tokens: List[Tuple[str, int]] = []
        current_stmt = []
        start_line = 1

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Ignore full line comments (* or ")
            if not stripped or stripped.startswith("*") or stripped.startswith('"'):
                continue
            
            # Strip inline comments (only outside single quotes)
            cleaned_line = ""
            in_single_quote = False
            for ch in stripped:
                if ch == "'":
                    in_single_quote = not in_single_quote
                    cleaned_line += ch
                elif ch == '"' and not in_single_quote:
                    break
                else:
                    cleaned_line += ch

            cleaned_line = cleaned_line.strip()
            if not cleaned_line:
                continue

            if not current_stmt:
                start_line = line_num

            # Statement terminator: dot followed by whitespace or end of line (does not split 1.18)
            parts = re.split(r'\.(?:\s+|$)', cleaned_line)
            for i, part in enumerate(parts):
                p = part.strip()
                if p:
                    current_stmt.append(p)
                if i < len(parts) - 1:
                    # Statement completed by period
                    full_text = " ".join(current_stmt).strip()
                    if full_text:
                        tokens.append((full_text, start_line))
                    current_stmt = []
                    start_line = line_num

        if current_stmt:
            full_text = " ".join(current_stmt).strip()
            if full_text:
                tokens.append((full_text, start_line))

        return tokens

    def _parse_statement(self, tokens: List[Tuple[str, int]], idx: int) -> Tuple[Optional[Statement], int]:
        if idx >= len(tokens):
            return None, idx + 1

        raw_stmt, line_num = tokens[idx]
        upper_stmt = raw_stmt.upper().strip()

        # Handle LOOP AT ... ENDLOOP block consumption
        if upper_stmt.startswith("LOOP AT"):
            loop_parts = [raw_stmt]
            cur_idx = idx + 1
            has_endloop = False
            while cur_idx < len(tokens):
                tok_raw, _ = tokens[cur_idx]
                loop_parts.append(tok_raw)
                cur_idx += 1
                if tok_raw.upper().strip() == "ENDLOOP":
                    has_endloop = True
                    break
            if not has_endloop:
                return UnsupportedStatement(
                    raw_code="; ".join(loop_parts),
                    reason=f"Syntax error: Unclosed LOOP block starting at line {line_num}; missing ENDLOOP.",
                    line_number=line_num,
                    suggested_action="Ensure each LOOP AT statement is terminated with an ENDLOOP statement."
                ), cur_idx
            return UnsupportedStatement(
                raw_code="; ".join(loop_parts),
                reason="Table iterations (LOOP AT) must be refactored into SQL joins or window functions.",
                line_number=line_num,
                suggested_action="Refactor 'LOOP AT' into a declarative SQL join, calculated column, or Datasphere DAC."
            ), cur_idx

        # Check for orphan block closing or intermediate statements outside their blocks
        if upper_stmt in ("ENDIF", "ENDCASE", "ENDLOOP", "ELSE", "WHEN OTHERS") or upper_stmt.startswith("ELSEIF ") or upper_stmt.startswith("WHEN "):
            return UnsupportedStatement(
                raw_code=raw_stmt,
                reason=f"Syntax error: Unexpected '{upper_stmt}' encountered outside matching block.",
                line_number=line_num,
                suggested_action=f"Ensure '{upper_stmt}' is enclosed within an appropriate block construct."
            ), idx + 1

        # 1. Unsupported dangerous/complex constructs check
        unsupported_keywords = [
            ("CALL FUNCTION", "External Function Module invocations require custom API integration or HANA User-Defined Function (UDF)."),
            ("SUBMIT", "Calling external ABAP reports is prohibited in database modernization."),
            ("READ TABLE", "Internal table lookups must be converted to SQL joins."),
            ("AUTHORITY-CHECK", "Authorization checks must be modeled via SAP Datasphere Data Access Controls (DAC)."),
            ("PERFORM", "Form subroutines must be decomposed or inlined."),
            ("UPDATE ", "Database mutations are forbidden inside transformation views."),
            ("INSERT ", "Direct database inserts are forbidden inside transformation views."),
            ("DELETE ", "Direct database deletes are forbidden inside transformation views."),
            ("COMMIT WORK", "Explicit transactional controls cannot be embedded in virtual SQL views.")
        ]
        for kw, reason in unsupported_keywords:
            if upper_stmt.startswith(kw) or f" {kw}" in upper_stmt:
                return UnsupportedStatement(
                    raw_code=raw_stmt,
                    reason=reason,
                    line_number=line_num,
                    suggested_action=f"Refactor '{kw}' into a declarative SQL join, calculated column, or Datasphere DAC."
                ), idx + 1

        # 2. IF / ELSEIF / ELSE / ENDIF Block
        if upper_stmt.startswith("IF "):
            return self._parse_if_block(tokens, idx)

        # 3. CASE / WHEN / WHEN OTHERS / ENDCASE Block
        if upper_stmt.startswith("CASE "):
            return self._parse_case_block(tokens, idx)

        # 4. CONCATENATE statement
        if upper_stmt.startswith("CONCATENATE "):
            return self._parse_concatenate(raw_stmt, line_num), idx + 1

        # 5. SELECT SINGLE statement (Lookup)
        if upper_stmt.startswith("SELECT SINGLE "):
            return self._parse_select_single(raw_stmt, line_num), idx + 1

        # 6. Assignment: TARGET = EXPR
        if "=" in raw_stmt and not upper_stmt.startswith("IF"):
            return self._parse_assignment(raw_stmt, line_num), idx + 1

        # Default fallback: mark unsupported
        return UnsupportedStatement(
            raw_code=raw_stmt,
            reason="Unrecognized or complex ABAP procedural construct.",
            line_number=line_num,
            suggested_action="Manually review and re-implement as SQL expression or Datasphere calculated column."
        ), idx + 1

    def _parse_if_block(self, tokens: List[Tuple[str, int]], start_idx: int) -> Tuple[Statement, int]:
        raw_if, line_num = tokens[start_idx]
        cond_str = raw_if[3:].strip()
        condition = self._parse_expression(cond_str)

        then_body: List[Statement] = []
        elseif_branches: List[Tuple[Expression, List[Statement]]] = []
        else_body: List[Statement] = []

        current_target = then_body
        idx = start_idx + 1

        while idx < len(tokens):
            raw_s, l_num = tokens[idx]
            u_s = raw_s.upper().strip()

            if u_s == "ENDIF":
                return IfStatement(
                    condition=condition,
                    then_body=then_body,
                    elseif_branches=elseif_branches,
                    else_body=else_body
                ), idx + 1

            if u_s.startswith("ELSEIF "):
                elif_cond_str = raw_s[7:].strip()
                elif_cond = self._parse_expression(elif_cond_str)
                current_target = []
                elseif_branches.append((elif_cond, current_target))
                idx += 1
                continue

            if u_s == "ELSE":
                current_target = else_body
                idx += 1
                continue

            stmt, next_idx = self._parse_statement(tokens, idx)
            if stmt:
                current_target.append(stmt)
            idx = next_idx

        # If ENDIF was missing or unclosed
        return UnsupportedStatement(
            raw_code=raw_if,
            reason=f"Syntax error: Unclosed IF block starting at line {line_num}; missing ENDIF.",
            line_number=line_num,
            suggested_action="Ensure each IF statement is terminated with an ENDIF statement."
        ), idx

    def _parse_case_block(self, tokens: List[Tuple[str, int]], start_idx: int) -> Tuple[Statement, int]:
        raw_case, line_num = tokens[start_idx]
        case_var_str = raw_case[5:].strip()
        case_expr = self._parse_expression(case_var_str)

        when_branches: List[Tuple[Expression, List[Statement]]] = []
        when_others_body: List[Statement] = []
        current_target = None
        idx = start_idx + 1

        while idx < len(tokens):
            raw_s, l_num = tokens[idx]
            u_s = raw_s.upper().strip()

            if u_s == "ENDCASE":
                return CaseStatement(
                    case_expr=case_expr,
                    when_branches=when_branches,
                    when_others_body=when_others_body
                ), idx + 1

            if u_s.startswith("WHEN ") and not u_s.startswith("WHEN OTHERS"):
                when_val_str = raw_s[5:].strip()
                when_val = self._parse_expression(when_val_str)
                current_target = []
                when_branches.append((when_val, current_target))
                idx += 1
                continue

            if u_s == "WHEN OTHERS":
                current_target = when_others_body
                idx += 1
                continue

            if current_target is not None:
                stmt, next_idx = self._parse_statement(tokens, idx)
                if stmt:
                    current_target.append(stmt)
                idx = next_idx
            else:
                idx += 1

        # If ENDCASE was missing or unclosed
        return UnsupportedStatement(
            raw_code=raw_case,
            reason=f"Syntax error: Unclosed CASE block starting at line {line_num}; missing ENDCASE.",
            line_number=line_num,
            suggested_action="Ensure each CASE statement is terminated with an ENDCASE statement."
        ), idx

    def _parse_concatenate(self, raw_stmt: str, line_num: int) -> Statement:
        """
        Parses: CONCATENATE f1 f2 [f3 ...] INTO target [SEPARATED BY sep]
        """
        match = re.search(r"CONCATENATE\s+(.+?)\s+INTO\s+(\S+)(?:\s+SEPARATED\s+BY\s+(.+))?", raw_stmt, re.IGNORECASE)
        if match:
            source_parts = match.group(1).strip().split()
            target_var = match.group(2).strip()
            sep_raw = match.group(3).strip() if match.group(3) else None
            sep = None
            if sep_raw:
                sep = sep_raw.strip("'\"")

            args: List[Expression] = [self._parse_expression(p) for p in source_parts]
            call = FunctionCall("CONCATENATE", args, separator=sep)
            return Assignment(target=Identifier(target_var), value=call)

        return UnsupportedStatement(
            raw_code=raw_stmt,
            reason="Syntax error: Malformed CONCATENATE syntax.",
            line_number=line_num,
            suggested_action="Use: CONCATENATE <f1> <f2> ... INTO <target> [SEPARATED BY <sep>]."
        )

    def _parse_select_single(self, raw_stmt: str, line_num: int) -> Statement:
        """
        Parses: SELECT SINGLE field FROM table INTO target WHERE key_field = expr [AND key_field2 = expr2 ...]
        """
        pattern = r"SELECT\s+SINGLE\s+(\S+)\s+FROM\s+(\S+)\s+INTO\s+(\S+)\s+WHERE\s+(.+)"
        match = re.search(pattern, raw_stmt, re.IGNORECASE)
        if match:
            select_field = match.group(1).strip()
            table_name = match.group(2).strip()
            target_var = match.group(3).strip()
            where_clause = match.group(4).strip()

            cond_parts = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)
            where_conditions: List[Tuple[str, Expression]] = []
            for cond in cond_parts:
                cond_clean = cond.strip()
                if "=" in cond_clean:
                    eq_parts = cond_clean.split("=", 1)
                    wf = eq_parts[0].strip()
                    val = self._parse_expression(eq_parts[1].strip())
                    where_conditions.append((wf, val))
                else:
                    return UnsupportedStatement(
                        raw_code=raw_stmt,
                        reason="Complex or non-equi condition in SELECT statement.",
                        line_number=line_num,
                        suggested_action="Use simple equality predicates: WHERE field = expr [AND field2 = expr2]."
                    )

            if not where_conditions:
                return UnsupportedStatement(
                    raw_code=raw_stmt,
                    reason="Incomplete SELECT statement: missing WHERE conditions.",
                    line_number=line_num,
                    suggested_action="Provide at least one equality condition in WHERE clause."
                )

            primary_where = where_conditions[0][0]
            primary_expr = where_conditions[0][1]

            return LookupStatement(
                target_var=Identifier(target_var),
                source_table=table_name,
                select_field=select_field,
                where_field=primary_where,
                key_expr=primary_expr,
                where_conditions=where_conditions
            )

        return UnsupportedStatement(
            raw_code=raw_stmt,
            reason="Syntax error: Malformed or incomplete SELECT statement.",
            line_number=line_num,
            suggested_action="Use: SELECT SINGLE <field> FROM <table> INTO <var> WHERE <field> = <expr>."
        )

    def _parse_assignment(self, raw_stmt: str, line_num: int) -> Statement:
        parts = raw_stmt.split("=", 1)
        target = Identifier(parts[0].strip())
        val_expr = self._parse_expression(parts[1].strip())
        return Assignment(target=target, value=val_expr)

    def _parse_expression(self, expr_str: str) -> Expression:
        expr_str = expr_str.strip()

        # Check for string literal ('val' or "val")
        if (expr_str.startswith("'") and expr_str.endswith("'")) or (expr_str.startswith('"') and expr_str.endswith('"')):
            inner = expr_str[1:-1]
            if expr_str.startswith("'"):
                inner = inner.replace("''", "'")
            return Literal(inner, "STRING")

        # Check for numeric literal
        if expr_str.replace(".", "", 1).isdigit():
            val = float(expr_str) if "." in expr_str else int(expr_str)
            return Literal(val, "NUMBER")

        # Check binary logical / comparison operators (AND, OR, =, <>, <, >, <=, >=)
        for op in [" AND ", " OR ", " <> ", " <= ", " >= ", " < ", " > ", " = "]:
            if op in expr_str:
                parts = expr_str.split(op, 1)
                clean_op = op.strip().upper()
                left = self._parse_expression(parts[0].strip())
                right = self._parse_expression(parts[1].strip())
                return BinaryOp(left=left, op=clean_op, right=right)

        # Check arithmetic operators (+, -, *, /)
        for op in [" + ", " - ", " * ", " / "]:
            if op in expr_str:
                parts = expr_str.split(op, 1)
                clean_op = op.strip()
                left = self._parse_expression(parts[0].strip())
                right = self._parse_expression(parts[1].strip())
                return BinaryOp(left=left, op=clean_op, right=right)

        # Default: Identifier
        return Identifier(expr_str)
