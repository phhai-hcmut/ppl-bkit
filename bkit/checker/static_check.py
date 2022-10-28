from collections import ChainMap
from dataclasses import dataclass, field, replace
from typing import NamedTuple, Optional, Union, cast

from ..utils import ast
from ..utils import type as bkit
from ..utils.builtins import BUILTIN_FUNCS, get_operator_type
from ..utils.type import (
    BOOL_TYPE,
    FLOAT_TYPE,
    INT_TYPE,
    STRING_TYPE,
    VOID_TYPE,
    ArrayType,
    BoolType,
    FloatType,
    FuncType,
    IntType,
    Prim,
    StringType,
    Type,
    Unknown,
    VoidType,
)
from ..utils.visitor import BaseVisitor
from .exceptions import (
    Function,
    FunctionNotReturn,
    Identifier,
    Kind,
    NoEntryPoint,
    NotInLoop,
    Parameter,
    Redeclared,
    TypeCannotBeInferred,
    TypeMismatchInExpression,
    TypeMismatchInStatement,
    Undeclared,
    Variable,
)

SymbolId = Union[int, str]


class AnalysisResult(NamedTuple):
    resolution_table: dict[int, SymbolId]
    symbol_table: dict[SymbolId, Type]


@dataclass(kw_only=True)
class Context:
    """Context of current statement

    Internal symbols are identified by integer,
    external symbols are identified by string (its name).
    """

    # Mapping identifier to symbol in scope
    scopes: ChainMap[str, SymbolId] = field(default_factory=ChainMap)
    # Mapping identifier to symbol
    resolution_table: dict[int, SymbolId] = field(default_factory=dict)
    symbol_table: dict[SymbolId, Type] = field(default_factory=dict)

    @property
    def current_scope(self):
        return self.scopes.maps[0]

    @property
    def globals(self):
        return self.scopes.maps[-1]

    def declare_symbol(self, symbol: ast.Id, typ: bkit.Type, kind: Kind) -> None:
        if symbol.name in self.current_scope:
            raise Redeclared(kind, symbol.name)
        self.scopes[symbol.name] = id(symbol)
        self.symbol_table[id(symbol)] = typ

    def get_type(self, ident: str) -> bkit.Type:
        ident_id = self.scopes[ident]
        return self.symbol_table[ident_id]  # type: ignore

    def set_type(self, ident: str, type: bkit.Type) -> None:
        ident_id = self.scopes[ident]
        self.symbol_table[ident_id] = type


@dataclass(kw_only=True)
class FunctionContext(Context):
    current_function: ast.FuncDecl
    loop_level: int = 0
    _params_id: list[int] = field(init=False)

    def __post_init__(self):
        self._params_id = [id(param.variable) for param in self.current_function.param]

    @property
    def current_function_type(self) -> bkit.FuncType:
        return cast(FuncType, self.symbol_table[id(self.current_function.name)])

    @property
    def is_in_loop(self) -> bool:
        return self.loop_level > 0

    def new_scope(self) -> "FunctionContext":
        return replace(self, scopes=self.scopes.new_child())

    def enter_loop(self) -> "FunctionContext":
        return replace(self, loop_level=self.loop_level + 1)

    def set_type(self, ident: str, type: bkit.Type) -> None:
        ident_id = self.scopes[ident]
        if isinstance(ident_id, str):
            raise ValueError("Cannot change type of external symbol")
        self.symbol_table[ident_id] = type
        if ident_id in self._params_id:
            param_idx = self._params_id.index(ident_id)
            self.current_function_type.intype[param_idx] = type

    def use_symbol(self, symbol: ast.Id, kind: Kind):
        if symbol.name not in self.scopes:
            raise Undeclared(kind, symbol.name)
        decl_id = self.scopes[symbol.name]
        self.resolution_table[id(symbol)] = decl_id
        return self.symbol_table[decl_id]

    def is_current_function(self, ident: str):
        """Check if identifier resolve to current function"""
        return self.scopes[ident] == id(self.current_function.name)

    def set_param_type(self, param_idx: int, typ: bkit.Type) -> None:
        param = self.current_function.param[param_idx].variable
        self.symbol_table[id(param)] = typ


class StaticChecker(BaseVisitor):

    ExprParam = tuple[FunctionContext, Optional[bkit.Type]]

    def __init__(self, program: ast.Program):
        self.ast = program
        self.cur_stmt: ast.Stmt
        self._cur_func_has_return: bool

    def check(self) -> AnalysisResult:
        global_scope = {name: name for name in BUILTIN_FUNCS}
        scopes = ChainMap(global_scope)
        symbol_table = BUILTIN_FUNCS.copy()
        c = Context(scopes=scopes, symbol_table=symbol_table)  # type: ignore
        self.visit(self.ast, c)
        return AnalysisResult(
            resolution_table=c.resolution_table, symbol_table=c.symbol_table
        )

    @staticmethod
    def raise_type_mismatch(ast_: Union[ast.Expr, ast.Stmt]) -> None:
        if isinstance(ast_, ast.Stmt):
            raise TypeMismatchInStatement(ast_)
        if isinstance(ast_, ast.Expr):
            raise TypeMismatchInExpression(ast_)

    def unify_type(
        self, t1: Type, t2: Type, error_ast: Union[ast.Expr, ast.Stmt]
    ) -> Type:
        """Unify 2 type t1 and t2

        Raise type mismatch if unification is impossible.
        Raise Type infer error if some monomoprhs are not resolved
        """
        # self.logger.info("Unify %s and %s in context %s", t1, t2, error_ast)
        if isinstance(t1, FuncType) or isinstance(t2, FuncType):
            self.raise_type_mismatch(error_ast)

        if isinstance(t1, ArrayType) and isinstance(t2, ArrayType) and t1.dim != t2.dim:
            self.raise_type_mismatch(error_ast)

        if (isinstance(t1, Prim) and isinstance(t2, ArrayType)) or (
            isinstance(t1, ArrayType) and isinstance(t2, Prim)
        ):
            # Cannot unify scalar type and composite type
            self.raise_type_mismatch(error_ast)

        if (isinstance(t1, ArrayType) and isinstance(t2, Unknown) and t2.prim) or (
            isinstance(t2, ArrayType) and isinstance(t1, Unknown) and t1.prim
        ):
            # Cannot unify scalar type and composite type
            self.raise_type_mismatch(error_ast)

        if not t1 and not t2 and self.cur_stmt is not None:
            # Both types are unresolved
            raise TypeCannotBeInferred(self.cur_stmt)
        if t1 and t2 and t1 != t2:
            # Both types are resolved but different
            self.raise_type_mismatch(error_ast)
        return t1 if t1 else t2

    def unify_expr_type(
        self,
        expr: Union[ast.Expr, ast.LHS],
        expected_type: Type,
        c: Context,
        error_ast: Union[ast.Expr, ast.Stmt],
    ) -> Type:
        """Unify type of `expr` with `expected_type`

        Raise type mismatch error if unification is impossible.
        Raise type infer error if some unknown types are not unified
        """
        expr_type = self.visit(expr, (c, expected_type))
        return self.unify_type(expr_type, expected_type, error_ast)

    def visitProgram(self, program: ast.Program, c: Context) -> None:
        func_defs = []
        for decl in program.decl:
            self.visit(decl, c)
            if isinstance(decl, ast.FuncDecl):
                func_defs.append(decl)

        if not ("main" in c.scopes and isinstance(c.get_type("main"), FuncType)):
            # There is no function named `main`
            raise NoEntryPoint()

        for decl in func_defs:
            self._check_function_definition(decl, c)

        for decl in program.decl:
            match decl:
                case ast.VarDecl(variable=ast.Id(name)):
                    name = name
                case ast.FuncDecl(name=ast.Id(name)):
                    name = name
            if not c.get_type(name):
                raise TypeCannotBeInferred(decl)  # type: ignore

    def visitVarDecl(self, ast: ast.VarDecl, c: Context) -> None:
        c.declare_symbol(ast.variable, self._get_decl_type(ast), Variable())

    def visitFuncDecl(self, ast: ast.FuncDecl, c: Context) -> None:
        param_types = []
        for param in ast.param:
            typ: bkit.Type
            if param.varDimen:
                typ = bkit.ArrayType(Unknown(True), param.varDimen)  # type: ignore
            else:
                typ = bkit.Unknown(True)
            param_types.append(typ)
        func_type = bkit.FuncType(param_types, None)  # type: ignore
        c.declare_symbol(ast.name, func_type, Function())

    def _get_decl_type(self, ast: ast.VarDecl) -> bkit.Type:
        if ast.varInit is not None:
            typ = self.visit(ast.varInit, None)
        else:
            if ast.varDimen:
                typ = ArrayType(Unknown(True), ast.varDimen)  # type: ignore
            else:
                typ = Unknown(True)
        return typ

    def _check_function_definition(self, ast: ast.FuncDecl, c: Context) -> None:
        self._cur_func_has_return = False
        symbol = ast.name
        func_type = cast(bkit.FuncType, c.get_type(symbol.name))

        c = FunctionContext(
            scopes=c.scopes.new_child(),
            resolution_table=c.resolution_table,
            symbol_table=c.symbol_table,
            current_function=ast,
        )
        for param, param_type in zip(ast.param, func_type.intype):
            symbol = param.variable
            c.declare_symbol(symbol, param_type, Parameter())

        self.visit_stmt_list(*ast.body, c, False)

        if not self._cur_func_has_return:
            if not func_type.restype:
                func_type.restype = VOID_TYPE
            elif not isinstance(func_type.restype, VoidType):
                raise FunctionNotReturn(ast.name.name)

    def visitAssign(self, ast: ast.Assign, c: FunctionContext) -> None:
        lhs_type = self.visit(ast.lhs, (c, None))
        rhs_type = self.unify_expr_type(ast.rhs, lhs_type, c, ast)
        if isinstance(rhs_type, VoidType):
            self.raise_type_mismatch(ast)
        lhs_type = self.unify_expr_type(ast.lhs, rhs_type, c, ast)

    def visitIf(self, ast: ast.If, c: FunctionContext) -> None:
        for cond, var_decls, stmts in ast.ifthenStmt:
            self.unify_expr_type(cond, BOOL_TYPE, c, ast)
            self.visit_stmt_list(var_decls, stmts, c)

        self.visit_stmt_list(*ast.elseStmt, c)

    def visitFor(self, ast: ast.For, c: FunctionContext) -> None:
        self.unify_expr_type(ast.idx1, INT_TYPE, c, ast)
        self.unify_expr_type(ast.expr1, INT_TYPE, c, ast)
        self.unify_expr_type(ast.expr2, BOOL_TYPE, c, ast)
        self.unify_expr_type(ast.expr3, INT_TYPE, c, ast)
        self.visit_stmt_list(*ast.loop, c.enter_loop())

    def visitWhile(self, ast: ast.While, c: FunctionContext) -> None:
        self.unify_expr_type(ast.exp, BOOL_TYPE, c, ast)
        self.visit_stmt_list(*ast.sl, c.enter_loop())

    def visitDowhile(self, ast: ast.Dowhile, c: FunctionContext) -> None:
        self.visit_stmt_list(*ast.sl, c.enter_loop())
        self.unify_expr_type(ast.exp, BOOL_TYPE, c, ast)

    def visitCallStmt(self, ast: ast.CallStmt, c: FunctionContext) -> None:
        ret_type = self.visit_func_call(ast, c, VOID_TYPE)
        self.unify_type(ret_type, VOID_TYPE, ast)

    def visit_stmt_list(
        self,
        var_decls: list[ast.VarDecl],
        stmts: list[ast.Stmt],
        c: FunctionContext,
        new_scope: bool = True,
    ) -> None:
        if new_scope:
            c = c.new_scope()
        for var_decl in var_decls:
            self.visitVarDecl(var_decl, c)
        for stmt in stmts:
            self.cur_stmt = stmt
            self.visit(stmt, c)

    def visitReturn(self, ast: ast.Return, c: FunctionContext) -> None:
        self._cur_func_has_return = True
        func_type = c.current_function_type
        if ast.expr is None:
            expr_type = VOID_TYPE
        else:
            expr_type = self.visit(ast.expr, (c, func_type.restype))

        func_type.restype = self.unify_type(expr_type, func_type.restype, ast)

    def visitContinue(self, ast: ast.Continue, c: FunctionContext) -> None:
        if not c.is_in_loop:
            raise NotInLoop(ast)

    def visitBreak(self, ast: ast.Break, c: FunctionContext) -> None:
        if not c.is_in_loop:
            raise NotInLoop(ast)

    def visitArrayCell(self, ast: ast.ArrayCell, c: ExprParam) -> Prim:
        context, expected_type = c
        arr_type = self.visit(ast.arr, (context, None))
        if arr_type is None:
            # Array expression is function call
            raise TypeCannotBeInferred(self.cur_stmt)

        if not isinstance(arr_type, ArrayType) or len(arr_type.dim) != len(ast.idx):
            raise TypeMismatchInExpression(ast)

        if isinstance(arr_type.elem_type, Unknown) and isinstance(expected_type, Prim):
            # Infer type for element
            arr_type.elem_type = expected_type

        # Check type of index expressions
        for idx in ast.idx:
            self.unify_expr_type(idx, INT_TYPE, context, ast)

        return arr_type.elem_type

    def visitCallExpr(self, ast: ast.CallExpr, c: ExprParam) -> Type:
        context, expected_type = c
        func_type = self.visit_func_call(ast, context, expected_type)
        return func_type

    def visit_func_call(
        self,
        ast: Union[ast.CallExpr, ast.CallStmt],
        c: FunctionContext,
        expected_type: Optional[Type],
    ) -> Type:
        symbol = ast.method
        func_type = c.use_symbol(symbol, Function())
        if not isinstance(func_type, FuncType):
            # Function symbol is shadowed by another symbol
            # http://e-learning.hcmut.edu.vn/mod/forum/discuss.php?d=130381#p427483
            raise Undeclared(Function(), symbol.name)

        # Infer return type
        if expected_type is not None and not func_type.restype:
            func_type.restype = expected_type

        # Check function arguments type
        if len(ast.param) != len(func_type.intype):
            self.raise_type_mismatch(ast)

        # Check if this function is the current function being defined
        is_recursive = c.is_current_function(symbol.name)
        for param_idx, arg in enumerate(ast.param):
            old_param_type = func_type.intype[param_idx]
            arg_type = self.visit(arg, (c, old_param_type))
            param_type = func_type.intype[param_idx]
            param_type = self.unify_type(arg_type, param_type, ast)
            if not old_param_type and param_type:
                self.visit(arg, (c, param_type))
            func_type.intype[param_idx] = param_type
            if is_recursive:
                c.set_param_type(param_idx, param_type)

        return func_type.restype

    def visitBinaryOp(self, ast: ast.BinaryOp, c: ExprParam) -> Prim:
        env, _ = c
        operand_type, return_type = get_operator_type(ast.op)
        self.unify_expr_type(ast.left, operand_type, env, ast)
        self.unify_expr_type(ast.right, operand_type, env, ast)
        return return_type

    def visitUnaryOp(self, ast: ast.UnaryOp, c: ExprParam) -> Prim:
        context, _ = c
        operand_type, return_type = get_operator_type(ast.op)
        self.unify_expr_type(ast.body, operand_type, context, ast)
        return return_type

    def visitId(self, ast: ast.Id, c: ExprParam) -> Type:
        context, expected_type = c

        id_type = context.use_symbol(ast, Identifier())
        if isinstance(id_type, FuncType):
            raise Undeclared(Identifier(), ast.name)

        if expected_type and (
            (isinstance(id_type, Unknown) and not isinstance(expected_type, ArrayType))
            or (
                isinstance(id_type, ArrayType)
                and not id_type
                and isinstance(expected_type, ArrayType)
                and id_type.dim == expected_type.dim
            )
        ):
            context.set_type(ast.name, expected_type)
            id_type = expected_type
        return id_type

    def visitArrayLiteral(self, ast: ast.ArrayLiteral, c) -> ArrayType:
        dim = [len(ast.value)]
        elem_type = self.visit(ast.value[0], c)
        if isinstance(elem_type, ArrayType):
            dim += elem_type.dim
            elem_type = elem_type.elem_type
        return ArrayType(elem_type, dim)

    def visitIntLiteral(self, ast: ast.IntLiteral, c) -> IntType:
        return INT_TYPE

    def visitFloatLiteral(self, ast: ast.FloatLiteral, c) -> FloatType:
        return FLOAT_TYPE

    def visitStringLiteral(self, ast: ast.StringLiteral, c) -> StringType:
        return STRING_TYPE

    def visitBooleanLiteral(self, ast: ast.BooleanLiteral, c) -> BoolType:
        return BOOL_TYPE
