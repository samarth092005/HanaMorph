"""
HANAMORPH BW Migration & Modernization Studio
ABAP Routine Abstract Syntax Tree (AST) Model
Milestone M4.2
"""

from typing import List, Optional, Any, Dict

class ASTNode:
    """Base class for all ABAP AST nodes."""
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


class Expression(ASTNode):
    """Base class for value-producing expressions."""
    pass


class Literal(Expression):
    def __init__(self, value: Any, data_type: str = "STRING"):
        self.value = value
        self.data_type = data_type

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": "Literal", "value": self.value, "data_type": self.data_type}


class Identifier(Expression):
    def __init__(self, name: str):
        self.name = name.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {"node_type": "Identifier", "name": self.name}


class BinaryOp(Expression):
    def __init__(self, left: Expression, op: str, right: Expression):
        self.left = left
        self.op = op.strip().upper()
        self.right = right

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "BinaryOp",
            "left": self.left.to_dict(),
            "op": self.op,
            "right": self.right.to_dict()
        }


class UnaryOp(Expression):
    def __init__(self, op: str, expr: Expression):
        self.op = op.strip().upper()
        self.expr = expr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "UnaryOp",
            "op": self.op,
            "expr": self.expr.to_dict()
        }


class FunctionCall(Expression):
    def __init__(self, func_name: str, args: List[Expression], separator: Optional[str] = None):
        self.func_name = func_name.strip().upper()
        self.args = args
        self.separator = separator

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "node_type": "FunctionCall",
            "func_name": self.func_name,
            "args": [a.to_dict() for a in self.args]
        }
        if self.separator is not None:
            d["separator"] = self.separator
        return d


class Statement(ASTNode):
    """Base class for procedural statements."""
    pass


class Assignment(Statement):
    def __init__(self, target: Identifier, value: Expression):
        self.target = target
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "Assignment",
            "target": self.target.to_dict(),
            "value": self.value.to_dict()
        }


class IfStatement(Statement):
    def __init__(
        self,
        condition: Expression,
        then_body: List[Statement],
        elseif_branches: Optional[List[tuple]] = None,
        else_body: Optional[List[Statement]] = None
    ):
        self.condition = condition
        self.then_body = then_body
        self.elseif_branches = elseif_branches or [] # List of (condition, body)
        self.else_body = else_body or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "IfStatement",
            "condition": self.condition.to_dict(),
            "then_body": [s.to_dict() for s in self.then_body],
            "elseif_branches": [
                {"condition": c.to_dict(), "body": [s.to_dict() for s in b]}
                for c, b in self.elseif_branches
            ],
            "else_body": [s.to_dict() for s in self.else_body]
        }


class CaseStatement(Statement):
    def __init__(
        self,
        case_expr: Expression,
        when_branches: List[tuple],
        when_others_body: Optional[List[Statement]] = None
    ):
        self.case_expr = case_expr
        self.when_branches = when_branches # List of (val_expr, body)
        self.when_others_body = when_others_body or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "CaseStatement",
            "case_expr": self.case_expr.to_dict(),
            "when_branches": [
                {"when_expr": w.to_dict(), "body": [s.to_dict() for s in b]}
                for w, b in self.when_branches
            ],
            "when_others_body": [s.to_dict() for s in self.when_others_body]
        }


class LookupStatement(Statement):
    """Represents a SELECT SINGLE or database lookup routine."""
    def __init__(
        self,
        target_var: Identifier,
        source_table: str,
        select_field: str,
        where_field: str = "",
        key_expr: Optional[Expression] = None,
        where_conditions: Optional[List[tuple]] = None
    ):
        self.target_var = target_var
        self.source_table = source_table.strip().upper()
        self.select_field = select_field.strip().upper()
        self.where_field = where_field.strip().upper() if where_field else ""
        self.key_expr = key_expr
        if where_conditions:
            self.where_conditions = where_conditions
            if not self.where_field and len(where_conditions) > 0:
                self.where_field = where_conditions[0][0]
                self.key_expr = where_conditions[0][1]
        elif self.where_field and self.key_expr:
            self.where_conditions = [(self.where_field, self.key_expr)]
        else:
            self.where_conditions = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "LookupStatement",
            "target_var": self.target_var.to_dict(),
            "source_table": self.source_table,
            "select_field": self.select_field,
            "where_field": self.where_field,
            "key_expr": self.key_expr.to_dict() if self.key_expr else None,
            "where_conditions": [
                {"field": f, "expr": e.to_dict()} for f, e in self.where_conditions
            ]
        }


class UnsupportedStatement(Statement):
    """Explicitly tracks constructs that cannot be automatically converted."""
    def __init__(
        self,
        raw_code: str,
        reason: str,
        line_number: int = 0,
        suggested_action: str = ""
    ):
        self.raw_code = raw_code.strip()
        self.reason = reason
        self.line_number = line_number
        self.suggested_action = suggested_action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": "UnsupportedStatement",
            "raw_code": self.raw_code,
            "reason": self.reason,
            "line_number": self.line_number,
            "suggested_action": self.suggested_action
        }


class RoutineAST(ASTNode):
    """Root node representing an analyzed ABAP transformation routine."""
    def __init__(
        self,
        routine_name: str,
        routine_type: str = "FIELD_ROUTINE",
        statements: Optional[List[Statement]] = None
    ):
        self.routine_name = routine_name
        self.routine_type = routine_type.strip().upper()
        self.statements = statements or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routine_name": self.routine_name,
            "routine_type": self.routine_type,
            "statement_count": len(self.statements),
            "statements": [s.to_dict() for s in self.statements]
        }
