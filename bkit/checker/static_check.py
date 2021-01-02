"""
 * @author nhphung
"""
from abc import ABC
from collections import ChainMap
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import typing
from functools import reduce
import logging

from ..utils.ast import *
from ..utils.visitor import BaseVisitor
from .exceptions import *


class Type(ABC):
    pass


class Prim(Type):
    """Primitive type"""

    def __bool__(self):
        return True


@dataclass
class IntType(Prim):
    pass


@dataclass
class FloatType(Prim):
    pass


@dataclass
class StringType(Prim):
    pass


@dataclass
class BoolType(Prim):
    pass


@dataclass
class VoidType(Type):
    """Unit type"""

    def __bool__(self):
        return True

    pass


@dataclass(eq=False)
class Unknown(Type):
    """Unresolved type (monomorph)

    A monomorph is a type which may, through unification, morph into a
    different type later.
    """

    def __bool__(self):
        return False


@dataclass
class ArrayType(Type):
    dim: List[int]
    elem_type: Prim

    def __bool__(self):
        return bool(self.elem_type)


@dataclass
class FuncType:
    intype: List[Type]
    restype: Type

    def __bool__(self):
        return not isinstance(self.intype, Unknown) and bool(self.restype)


@dataclass
class OpType:
    """Operator type"""

    op_type: Prim  # operand type
    ret_type: Prim  # result type


@dataclass
class Symbol:
    kind: Kind
    type: Type


BUILTIN_FUNCS = {
    'int_of_float': FuncType([FloatType()], IntType()),
    'float_to_int': FuncType([IntType()], FloatType()),
    'int_of_string': FuncType([StringType()], IntType()),
    'string_of_int': FuncType([IntType()], StringType()),
    'float_of_string': FuncType([StringType()], FloatType()),
    'string_of_float': FuncType([FloatType()], StringType()),
    'bool_of_string': FuncType([StringType()], BoolType()),
    'string_of_bool': FuncType([BoolType()], StringType()),
    'read': FuncType([], StringType()),
    'printLn': FuncType([], VoidType()),
    'print': FuncType([StringType()], VoidType()),
    'printStrLn': FuncType([StringType()], VoidType()),
}

BUILTIN_OPS = {
    ('+', '-', '*', '\\', '%'): OpType(IntType(), IntType()),
    ('+.', '-.', '*.', '\\.'): OpType(FloatType(), FloatType()),
    ('!', '&&', '||'): OpType(BoolType(), BoolType()),
    ('==', '!=', '<', '>', '<=', '>='): OpType(IntType(), BoolType()),
    ('=/=', '<.', '>.', '<=.', '>=.'): OpType(FloatType(), BoolType()),
}


class Context(ChainMap):
    """A stack-like implementation of typing context"""

    def __setitem__(self, name, type):
        # When update type of a parameter,
        # also update type of the current function
        for scope in self.maps:
            if name in scope:
                scope[name] = type
                if name in scope.get('Func_params', []):
                    param_idx = scope['Func_params'].index(name)
                    scope['Func_type'].intype[param_idx] = type
                break
        else:
            self.locals[name] = type

    def new_scope(self):
        return self.new_child()

    @property
    def in_global(self) -> bool:
        return len(self.maps) == 1

    @property
    def locals(self):
        """Local scope"""
        return self.maps[0]

    @property
    def nonlocals(self):
        return self.parents

    @property
    def globals(self):
        return self.maps[-1]


ExprParam = Tuple[Context, Optional[Type]]


class StaticChecker(BaseVisitor):
    def __init__(self, ast: AST):
        self.ast = ast
        self.undecl_funcs: Dict[str, Union[CallExpr, CallStmt]] = {}
        self.cur_stmt: Optional[Stmt] = None
        self.logger = logging.getLogger(__name__)

    def check(self):
        builtins = {
            op: op_type for op_list, op_type in BUILTIN_OPS.items() for op in op_list
        }
        builtins.update(BUILTIN_FUNCS)
        if isinstance(self.ast, Expr):
            c = (Context(builtins), None)
        else:
            c = Context(builtins)
        return self.visit(self.ast, c)

    @staticmethod
    def raise_type_mismatch(ast: Union[Expr, Stmt]) -> None:
        if isinstance(ast, Stmt):
            raise TypeMismatchInStatement(ast)
        if isinstance(ast, Expr):
            raise TypeMismatchInExpression(ast)

    def unify_type(
        self, t1: Type, t2: Type, error_ast: Union[Expr, Stmt], prim: bool = True
    ) -> Type:
        """Unify 2 type t1 and t2

        Raise type mismatch if unification is impossible.
        Raise Type infer error if some monomoprhs are not resolved
        """
        self.logger.info("Unify %s and %s in context %s", t1, t2, error_ast)

        if isinstance(t1, FuncType) or isinstance(t2, FuncType):
            self.raise_type_mismatch(error_ast)

        if prim:
            if isinstance(t1, ArrayType) and isinstance(t2, ArrayType):
                if t1.dim != t2.dim:
                    self.raise_type_mismatch(error_ast)
            elif isinstance(t1, ArrayType) or isinstance(t2, ArrayType):
                self.raise_type_mismatch(error_ast)

        if not t1 and not t2 and self.cur_stmt is not None:
            # Both types are unresolved
            raise TypeCannotBeInferred(self.cur_stmt)
        if t1 and t2 and t1 != t2:
            # Both types are resolved but different
            self.raise_type_mismatch(error_ast)
        return t1 if t1 else t2

    def unify_expr_type(
        self, expr: Expr, expected_type: Type, c: Context, error_ast: Union[Expr, Stmt]
    ) -> Type:
        """Unify type of `expr` with `expected_type`

        Raise type mismatch error if unification is impossible.
        Raise type infer error if some unknown types are not unified
        """
        expr_type = self.visit(expr, (c, expected_type))
        return self.unify_type(expr_type, expected_type, error_ast)

    def visit_fold(self, c: Context, ast: AST) -> Context:
        """Fold over AST and return new context"""
        return ast.accept(self, c)

    def visitProgram(self, ast: Program, c: Context) -> Context:
        c = reduce(self.visit_fold, ast.decl, c)
        if 'main' not in c.globals or not isinstance(c.globals['main'], FuncType):
            # There is no function named `main`
            raise NoEntryPoint()
        if self.undecl_funcs:
            func_name = next(iter(self.undecl_funcs))
            raise Undeclared(Function(), func_name)
        return c

    def visitVarDecl(self, ast: VarDecl, c: Union[Context, ExprParam]) -> Context:
        IdKind: typing.Type[Kind]
        if isinstance(c, tuple):
            c, param_type = c
            IdKind = Parameter
        else:
            IdKind = Variable

        name = ast.variable.name
        if name in c.locals:
            raise Redeclared(IdKind(), name)

        if ast.varInit is not None:
            init_type = self.visit(ast.varInit, c)
            c.locals[name] = init_type
        else:
            if ast.varDimen:
                c.locals[name] = ArrayType(ast.varDimen, Unknown())
            else:
                c.locals[name] = Unknown()

        if IdKind is Parameter:
            if param_type:
                c.locals[name] = param_type
            else:
                param_idx = len(c.locals['Func_params'])
                c.locals['Func_type'].intype[param_idx] = c.locals[name]
            c.locals['Func_params'].append(name)
        return c

    def visitFuncDecl(self, ast: FuncDecl, c: Context) -> Context:
        name = ast.name.name
        if name in c:
            if name in self.undecl_funcs:
                # This function is called but not yet declared
                func_type = c[name]
                func_call = self.undecl_funcs.pop(name)
                if len(func_type.intype) != len(ast.param):
                    self.raise_type_mismatch(func_call)
            else:
                # This function has been declared
                raise Redeclared(Function(), name)
        else:
            # First declaration
            func_type = FuncType([Unknown()] * len(ast.param), None)
            c.globals[name] = func_type

        func_context = c.new_scope()
        func_context.locals['Func_type'] = func_type
        func_context.locals['Func_params'] = []

        def visit_param(func_context, elem):
            param, param_type = elem
            return self.visit(param, (func_context, param_type))

        func_context = reduce(
            visit_param, zip(ast.param, func_type.intype), func_context
        )
        c = self.visit_stmt_list(*ast.body, func_context, False)
        return c

    def visitAssign(self, ast: Assign, c: Context) -> Context:
        self.cur_stmt = ast
        lhs_type = self.visit(ast.lhs, (c, None))
        rhs_type = self.unify_expr_type(ast.rhs, lhs_type, c, ast)
        if isinstance(rhs_type, VoidType):
            self.raise_type_mismatch(ast)
        # if lhs_type or rhs_type:
        #     rhs_type = self.visit(ast.rhs, (c, lhs_type))
        #     if lhs_type != rhs_type:
        #         raise TypeMismatchInStatement(ast)
        # else:
        #     raise TypeCannotBeInferred(ast)
        self.unify_expr_type(ast.lhs, rhs_type, c, ast)
        return c

    def visitIf(self, ast: If, c: Context) -> Context:
        self.cur_stmt = ast

        def visit_if_then_stmt(c, if_then_stmt):
            cond, var_decls, stmts = if_then_stmt
            self.unify_expr_type(cond, BoolType(), c, ast)
            return self.visit_stmt_list(var_decls, stmts, c)

        c = reduce(visit_if_then_stmt, ast.ifthenStmt, c)
        c = self.visit_stmt_list(*ast.elseStmt, c)
        return c

    def visitFor(self, ast: For, c: Context) -> Context:
        self.cur_stmt = ast
        self.unify_expr_type(ast.idx1, IntType(), c, ast)
        self.unify_expr_type(ast.expr1, IntType(), c, ast)
        self.unify_expr_type(ast.expr2, BoolType(), c, ast)
        self.unify_expr_type(ast.expr3, IntType(), c, ast)
        return self.visit_stmt_list(*ast.loop, c)

    def visitWhile(self, ast: While, c: Context) -> Context:
        self.cur_stmt = ast
        self.unify_expr_type(ast.exp, BoolType(), c, ast)
        return self.visit_stmt_list(*ast.sl, c)

    def visitDowhile(self, ast: Dowhile, c: Context) -> Context:
        c = self.visit_stmt_list(*ast.sl, c)
        self.cur_stmt = ast
        self.unify_expr_type(ast.exp, BoolType(), c, ast)
        return c

    def visitCallStmt(self, ast: CallStmt, c: Context) -> Context:
        self.cur_stmt = ast
        ret_type = self.visit_func_call(ast, c, VoidType())
        self.unify_type(ret_type, VoidType(), ast, False)
        return c

    def visit_stmt_list(
        self,
        var_decls: List[VarDecl],
        stmts: List[Stmt],
        c: Context,
        new_scope: bool = True,
    ) -> Context:
        if new_scope:
            c = c.new_scope()
        c = reduce(self.visit_fold, var_decls + stmts, c)
        self.cur_stmt = None
        return c.nonlocals

    def visitReturn(self, ast: Return, c: Context) -> Context:
        self.cur_stmt = ast
        func_type = c['Func_type']
        if ast.expr is None:
            expr_type = VoidType()
        else:
            expr_type = self.visit(ast.expr, (c, func_type.restype))

        # if func_type.restype is None:
        #     func_type.restype = expr_type
        # else:
        func_type.restype = self.unify_type(expr_type, func_type.restype, ast, False)
        return c

    def visitContinue(self, ast: Continue, c: Context) -> Context:
        return c

    def visitBreak(self, ast: Break, c: Context) -> Context:
        return c

    def visitArrayCell(self, ast: ArrayCell, c: ExprParam) -> Prim:
        context, expected_type = c
        arr_type = self.visit(ast.arr, (context, None))
        if arr_type is None:
            # Array expression is function call
            raise TypeCannotBeInferred(self.cur_stmt)

        if not isinstance(arr_type, ArrayType) or len(arr_type.dim) != len(ast.idx):
            raise TypeMismatchInExpression(ast)

        if isinstance(arr_type.elem_type, Unknown) and expected_type is not None:
            # Infer type for element
            arr_type.elem_type = expected_type

        # Check type of index expressions
        for idx in ast.idx:
            self.unify_expr_type(idx, IntType(), context, ast)

        return arr_type.elem_type

    def visitCallExpr(self, ast: CallExpr, c: ExprParam) -> Type:
        context, expected_type = c
        func_type = self.visit_func_call(ast, context, expected_type)
        return func_type

    def visit_func_call(
        self, ast: Union[CallExpr, CallStmt], c: Context, expected_type: Optional[Type]
    ) -> Type:
        name = ast.method.name
        if name not in c:
            if name not in self.undecl_funcs:
                self.undecl_funcs[name] = ast
            func_type = FuncType([Unknown()] * len(ast.param), None)
            c[name] = func_type
        else:
            func_type = c[name]

        # Check if this function is the current function being defined
        is_recursive = func_type is c['Func_type']

        if not isinstance(func_type, FuncType):
            # http://e-learning.hcmut.edu.vn/mod/forum/discuss.php?d=130381#p427483
            raise Undeclared(Function(), name)

        # Infer return type
        if expected_type is not None and not func_type.restype:
            func_type.restype = expected_type

        # Check function arguments type
        if isinstance(func_type.intype, Unknown):
            func_type.intype = [Unknown()] * len(ast.param)
        elif len(ast.param) != len(func_type.intype):
            self.raise_type_mismatch(ast)

        def visit_arg(arg, param_idx):
            old_param_type = func_type.intype[param_idx]
            arg_type = self.visit(arg, (c, old_param_type))
            param_type = func_type.intype[param_idx]
            param_type = self.unify_type(arg_type, param_type, ast)
            if not old_param_type and param_type:
                self.visit(arg, (c, param_type))
            func_type.intype[param_idx] = param_type
            if is_recursive:
                param_name = c['Func_params'][param_idx]
                c[param_name] = param_type
            return param_type

        func_type.intype = list(
            map(
                visit_arg,
                ast.param,
                range(len(func_type.intype)),
            )
        )
        if name not in c.globals:
            c.globals[name] = func_type

        return func_type.restype

    def visitBinaryOp(self, ast: BinaryOp, c: ExprParam) -> Prim:
        env, _ = c
        op_type = env[ast.op]
        self.unify_expr_type(ast.left, op_type.op_type, env, ast)
        self.unify_expr_type(ast.right, op_type.op_type, env, ast)
        return op_type.ret_type

    def visitUnaryOp(self, ast: UnaryOp, c) -> Prim:
        context, _ = c
        op_type = context[ast.op]
        self.unify_expr_type(ast.body, op_type.op_type, context, ast)
        return op_type.ret_type

    def visitId(self, ast: Id, c: ExprParam) -> Type:
        context, expected_type = c

        if ast.name not in context or isinstance(context[ast.name], FuncType):
            raise Undeclared(Identifier(), ast.name)

        id_type = context[ast.name]
        if expected_type and ((
            isinstance(id_type, Unknown)
            and not isinstance(expected_type, ArrayType)
            ) or (
                isinstance(id_type, ArrayType)
                and not id_type
                and isinstance(expected_type, ArrayType)
                and id_type.dim == expected_type.dim
            )
        ):
            context[ast.name] = expected_type
        return context[ast.name]

    def visitArrayLiteral(self, ast: ArrayLiteral, c) -> ArrayType:
        dim = [len(ast.value)]
        elem_type = self.visit(ast.value[0], c)
        if isinstance(elem_type, ArrayType):
            dim += elem_type.dim
            elem_type = elem_type.elem_type
        return ArrayType(dim, elem_type)

    def visitIntLiteral(self, ast: IntLiteral, c) -> IntType:
        return IntType()

    def visitFloatLiteral(self, ast: FloatLiteral, c) -> FloatType:
        return FloatType()

    def visitStringLiteral(self, ast: StringLiteral, c) -> StringType:
        return StringType()

    def visitBooleanLiteral(self, ast: BooleanLiteral, c) -> BoolType:
        return BoolType()
