"""
 * @author nhphung
"""
from collections import ChainMap
from typing import Dict, List, Optional, Union
import typing
from functools import reduce

# import logging

from ..utils.ast import *
from ..utils.type import *
from ..utils.visitor import BaseVisitor
from .exceptions import *


class Context(ChainMap):
    """A stack-like implementation of typing context"""

    def __setitem__(self, name: str, type: Type):
        # When update type of a parameter,
        # also update type of the current function
        for scope in self.maps:
            if name in scope:
                scope[name] = type  # type: ignore
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
    BUILTIN_FUNCS = {
        'int_of_float': FuncType([FLOAT_TYPE], INT_TYPE),
        'float_to_int': FuncType([INT_TYPE], FLOAT_TYPE),
        'int_of_string': FuncType([STRING_TYPE], INT_TYPE),
        'string_of_int': FuncType([INT_TYPE], STRING_TYPE),
        'float_of_string': FuncType([STRING_TYPE], FLOAT_TYPE),
        'string_of_float': FuncType([FLOAT_TYPE], STRING_TYPE),
        'bool_of_string': FuncType([STRING_TYPE], BOOL_TYPE),
        'string_of_bool': FuncType([BOOL_TYPE], STRING_TYPE),
        'read': FuncType([], STRING_TYPE),
        'printLn': FuncType([], VOID_TYPE),
        'print': FuncType([STRING_TYPE], VOID_TYPE),
        'printStrLn': FuncType([STRING_TYPE], VOID_TYPE),
    }

    BUILTIN_OPS = {
        ('+', '-', '*', '\\', '%'): OpType(INT_TYPE, INT_TYPE),
        ('+.', '-.', '*.', '\\.'): OpType(FLOAT_TYPE, FLOAT_TYPE),
        ('!', '&&', '||'): OpType(BOOL_TYPE, BOOL_TYPE),
        ('==', '!=', '<', '>', '<=', '>='): OpType(INT_TYPE, BOOL_TYPE),
        ('=/=', '<.', '>.', '<=.', '>=.'): OpType(FLOAT_TYPE, BOOL_TYPE),
    }

    def __init__(self, ast: AST):
        self.ast = ast
        self.undecl_funcs: Dict[str, Union[CallExpr, CallStmt]] = {}
        self.cur_stmt: Stmt
        # self.logger = logging.getLogger(__name__)

    def check(self):
        builtins = {
            op: op_type
            for op_list, op_type in self.BUILTIN_OPS.items()
            for op in op_list
        }
        builtins.update(self.BUILTIN_FUNCS)
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

    def unify_type(self, t1: Type, t2: Type, error_ast: Union[Expr, Stmt]) -> Type:
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
        expr: Union[Expr, LHS],
        expected_type: Type,
        c: Context,
        error_ast: Union[Expr, Stmt],
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
                c.locals[name] = ArrayType(Unknown(True), ast.varDimen)  # type: ignore
            else:
                c.locals[name] = Unknown(True)

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
            func_type = FuncType([Unknown()] * len(ast.param), None)  # type: ignore
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
        self.unify_expr_type(ast.lhs, rhs_type, c, ast)
        return c

    def visitIf(self, ast: If, c: Context) -> Context:
        self.cur_stmt = ast

        def visit_if_then_stmt(c, if_then_stmt):
            cond, var_decls, stmts = if_then_stmt
            self.unify_expr_type(cond, BOOL_TYPE, c, ast)
            return self.visit_stmt_list(var_decls, stmts, c)

        c = reduce(visit_if_then_stmt, ast.ifthenStmt, c)
        c = self.visit_stmt_list(*ast.elseStmt, c)
        return c

    def visitFor(self, ast: For, c: Context) -> Context:
        self.cur_stmt = ast
        self.unify_expr_type(ast.idx1, INT_TYPE, c, ast)
        self.unify_expr_type(ast.expr1, INT_TYPE, c, ast)
        self.unify_expr_type(ast.expr2, BOOL_TYPE, c, ast)
        self.unify_expr_type(ast.expr3, INT_TYPE, c, ast)
        return self.visit_stmt_list(*ast.loop, c)

    def visitWhile(self, ast: While, c: Context) -> Context:
        self.cur_stmt = ast
        self.unify_expr_type(ast.exp, BOOL_TYPE, c, ast)
        return self.visit_stmt_list(*ast.sl, c)

    def visitDowhile(self, ast: Dowhile, c: Context) -> Context:
        c = self.visit_stmt_list(*ast.sl, c)
        self.cur_stmt = ast
        self.unify_expr_type(ast.exp, BOOL_TYPE, c, ast)
        return c

    def visitCallStmt(self, ast: CallStmt, c: Context) -> Context:
        self.cur_stmt = ast
        ret_type = self.visit_func_call(ast, c, VOID_TYPE)
        self.unify_type(ret_type, VOID_TYPE, ast)
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
        c = reduce(self.visit_fold, var_decls + stmts, c)  # type: ignore
        return c.nonlocals

    def visitReturn(self, ast: Return, c: Context) -> Context:
        self.cur_stmt = ast
        func_type = c['Func_type']
        if ast.expr is None:
            expr_type = VOID_TYPE
        else:
            expr_type = self.visit(ast.expr, (c, func_type.restype))

        func_type.restype = self.unify_type(expr_type, func_type.restype, ast)
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

        if isinstance(arr_type.elem_type, Unknown) and isinstance(expected_type, Prim):
            # Infer type for element
            arr_type.elem_type = expected_type

        # Check type of index expressions
        for idx in ast.idx:
            self.unify_expr_type(idx, INT_TYPE, context, ast)

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
            func_type = FuncType([Unknown()] * len(ast.param), None)  # type: ignore
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
        if expected_type and (
            (isinstance(id_type, Unknown) and not isinstance(expected_type, ArrayType))
            or (
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
        return ArrayType(elem_type, dim)

    def visitIntLiteral(self, ast: IntLiteral, c) -> IntType:
        return INT_TYPE

    def visitFloatLiteral(self, ast: FloatLiteral, c) -> FloatType:
        return FLOAT_TYPE

    def visitStringLiteral(self, ast: StringLiteral, c) -> StringType:
        return STRING_TYPE

    def visitBooleanLiteral(self, ast: BooleanLiteral, c) -> BoolType:
        return BOOL_TYPE
