from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

from .visitor import Visitor

# __all__ = [
#     'Id',
#     'Program',
#     'VarDecl',
#     'FuncDecl',
#     'ArrayCell',
#     'BinaryOp',
#     'UnaryOp',
#     'CallExpr',
#     'IntLiteral',
#     'FloatLiteral',
#     'StringLiteral',
#     'BooleanLiteral',
#     'ArrayLiteral',
#     'Assign',
#     'If',
#     'For',
#     'Break',
#     'Continue',
#     'Return',
#     'Dowhile',
#     'While',
#     'CallStmt',
# ]


@dataclass(frozen=True, kw_only=True)
class AST(ABC):
    # Line and column number start at 1
    line: int = 0
    column: int = 0

    @staticmethod
    def print_list(
        lst: List[AST],
        f: Callable[[AST], str] = str,
        start: str = "[",
        sep: str = ",",
        ending: str = "]",
    ) -> str:
        return start + sep.join(f(i) for i in lst) + ending

    @abstractmethod
    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visit(self, param)


class Decl(AST):
    pass


class Expr(AST):
    pass


class Literal(Expr):
    pass


class LHS(AST):
    pass


@dataclass(frozen=True)
class Id(Expr, LHS):
    name: str

    def __str__(self):
        return f"Id({self.name})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitId(self, param)


@dataclass(frozen=True)
class Program(AST):
    decl: List[Decl]

    def __str__(self):
        decls = self.print_list(self.decl)
        return f"Program({decls})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitProgram(self, param)


@dataclass(frozen=True)
class VarDecl(Decl):
    variable: Id
    varDimen: List[int]  # empty list for scalar variable
    varInit: Optional[Literal]  # null if no initial

    def __str__(self):
        initial = f",{self.varInit}" if self.varInit else ""
        dimen = ("," + self.print_list(self.varDimen)) if self.varDimen else ""
        return f"VarDecl({self.variable}{dimen}{initial})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitVarDecl(self, param)


class Stmt(AST):
    def print_stmt_list(self, var_decls: List[VarDecl], stmts: List[Stmt]) -> str:
        # Must make a copy of list as List type is invariant
        return self.print_list(list(var_decls)) + "," + self.print_list(list(stmts))


StmtList = tuple[list[VarDecl], list[Stmt]]


@dataclass(frozen=True)
class FuncDecl(Decl):
    name: Id
    param: List[VarDecl]
    body: StmtList

    def __str__(self):
        params = self.print_list(self.param)
        var_decls, stmts = self.body
        var_decls = self.print_list(var_decls)
        stmts = self.print_list(stmts)
        return f"FuncDecl({self.name}{params},({var_decls}{stmts}))"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitFuncDecl(self, param)


@dataclass(frozen=True)
class ArrayCell(Expr, LHS):
    arr: Expr
    idx: List[Expr]

    def __str__(self):
        return f"ArrayCell({self.arr},{self.print_list(self.idx)})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitArrayCell(self, param)


@dataclass(frozen=True)
class BinaryOp(Expr):
    op: str
    left: Expr
    right: Expr

    def __str__(self):
        return f"BinaryOp({self.op},{self.left},{self.right})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitBinaryOp(self, param)


@dataclass(frozen=True)
class UnaryOp(Expr):
    op: str
    body: Expr

    def __str__(self):
        return f"UnaryOp({self.op},{self.body})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitUnaryOp(self, param)


@dataclass(frozen=True)
class CallExpr(Expr):
    method: Id
    param: List[Expr]

    def __str__(self):
        return f"CallExpr({self.method},{self.print_list(self.param)})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitCallExpr(self, param)


@dataclass(frozen=True)
class IntLiteral(Literal):
    value: int

    def __str__(self):
        return f"IntLiteral({self.value})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitIntLiteral(self, param)


@dataclass(frozen=True)
class FloatLiteral(Literal):
    value: float

    def __str__(self):
        return f"FloatLiteral({self.value})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitFloatLiteral(self, param)


@dataclass(frozen=True)
class StringLiteral(Literal):
    value: str

    def __str__(self):
        return f"StringLiteral({self.value})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitStringLiteral(self, param)


@dataclass(frozen=True)
class BooleanLiteral(Literal):
    value: bool

    def __str__(self):
        return "BooleanLiteral(" + str(self.value).lower() + ")"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitBooleanLiteral(self, param)


@dataclass(frozen=True)
class ArrayLiteral(Literal):
    value: List[Literal]

    def __str__(self):
        return self.print_list(self.value, start="ArrayLiteral(", ending=")")

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitArrayLiteral(self, param)


@dataclass(frozen=True)
class Assign(Stmt):
    lhs: LHS
    rhs: Expr

    def __str__(self):
        return f"Assign({self.lhs},{self.rhs})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitAssign(self, param)


@dataclass(frozen=True)
class If(Stmt):
    # Expr is the condition,
    # List[VarDecl] is the list of declaration in the beginning of Then branch,
    #   empty list if no declaration
    # List[Stmt] is the list of statement after the declaration in Then branch,
    #   empty list if no statement
    ifthenStmt: List[Tuple[Expr, List[VarDecl], List[Stmt]]]
    # Else branch, empty list if no Else
    elseStmt: StmtList

    def __str__(self):
        def print_if_then_stmt(if_then_stmt):
            cond, var_decls, stmts = if_then_stmt
            return str(cond) + "," + self.print_stmt_list(var_decls, stmts)

        ifstmt = self.print_list(
            self.ifthenStmt, print_if_then_stmt, "If(", ")ElseIf(", ")"
        )
        elsestmt = (
            ("Else(" + self.print_stmt_list(*self.elseStmt) + ")")
            if self.elseStmt
            else ""
        )
        return ifstmt + elsestmt

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitIf(self, param)


@dataclass(frozen=True)
class For(Stmt):
    idx1: Id
    expr1: Expr
    expr2: Expr
    expr3: Expr
    loop: StmtList

    def __str__(self):
        stmt_list = self.print_stmt_list(*self.loop)
        return f"For({self.idx1},{self.expr1},{self.expr2},{self.expr3},{stmt_list})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitFor(self, param)


class Break(Stmt):
    def __str__(self):
        return "Break()"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitBreak(self, param)


class Continue(Stmt):
    def __str__(self):
        return "Continue()"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitContinue(self, param)


@dataclass(frozen=True)
class Return(Stmt):
    expr: Optional[Expr]  # None if no expression

    def __str__(self):
        return "Return({})".format("" if self.expr is None else self.expr)

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitReturn(self, param)


@dataclass(frozen=True)
class Dowhile(Stmt):
    sl: StmtList
    exp: Expr

    def __str__(self):
        stmt_list = self.print_stmt_list(*self.sl)
        return f"Dowhile({stmt_list},{self.exp})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitDowhile(self, param)


@dataclass(frozen=True)
class While(Stmt):
    exp: Expr
    sl: StmtList

    def __str__(self):
        stmt_list = self.print_stmt_list(*self.sl)
        return f"While({self.exp},{stmt_list})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitWhile(self, param)


@dataclass(frozen=True)
class CallStmt(Stmt):
    method: Id
    param: List[Expr]

    def __str__(self):
        param_list = self.print_list(self.param)
        return f"CallStmt({self.method},{param_list})"

    def accept(self, v: Visitor, param: Any) -> Any:
        return v.visitCallStmt(self, param)
