"""Jasmin code generator"""
from dataclasses import dataclass, replace
from itertools import chain, groupby
from typing import (
    ChainMap,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Union,
    Optional,
    cast,
)

from ..utils.ast import *
from ..utils.visitor import BaseVisitor
from . import emitter
from .emitter import (
    BOOL_TYPE,
    FLOAT_TYPE,
    INT_TYPE,
    STRING_TYPE,
    VOID_TYPE,
    ArrayType,
    MType,
    ClassType,
    Prim,
    Type,
    CName,
    Index,
    Symbol,
)
from .frame import Frame


__all__ = 'CodeGenerator'


@dataclass
class MethodEnv:
    frame: Frame
    symtab: ChainMap[str, Symbol]

    def enter_scope(self) -> None:
        self.frame.enterScope(False)
        self.symtab.maps.insert(0, {})

    def exit_scope(self) -> None:
        self.frame.exitScope()
        self.symtab.maps.pop(0)


@dataclass
class Access(MethodEnv):
    expected_type: Optional[Type] = None
    rvalue: bool = True

    @classmethod
    def from_method_env(cls, o: MethodEnv, **kwargs) -> 'Access':
        return cls(o.frame, o.symtab, **kwargs)


@dataclass(frozen=True)
class NeedRValue:
    """Signal the caller to generate code for right hand side

    When generating code for left hand side in assignment, sometimes we need
    instructions to push reference to the operand stack, then the value of
    right hand side and finally the store instruction. This require the
    generator of assign statement know when to generate instruction for right
    hand side, so an instance of this class will be yielded by the left hand
    side generator when needed.
    """

    left_type: Type


@dataclass(frozen=True)
class SkipToFunc:
    """Signal the caller to generate code for function `name`

    When read a function AST, we will generate code and infer callee type at
    the same time.  When we finish infering type for a function, an instance of
    this class will be yielded to caller to postpone current function and start
    generate code for function `name`.
    """

    name: str


class CodeGenerator:
    """Public class to generate Jasmin code"""

    STDLIB_NAME = CName('io')
    BUILTIN_FUNCS = {
        'int_of_float': Symbol(MType([FLOAT_TYPE], INT_TYPE), STDLIB_NAME),
        'float_to_int': Symbol(MType([INT_TYPE], FLOAT_TYPE), STDLIB_NAME),
        'int_of_string': Symbol(MType([STRING_TYPE], INT_TYPE), STDLIB_NAME),
        'string_of_int': Symbol(MType([INT_TYPE], STRING_TYPE), STDLIB_NAME),
        'float_of_string': Symbol(MType([STRING_TYPE], FLOAT_TYPE), STDLIB_NAME),
        'string_of_float': Symbol(MType([FLOAT_TYPE], STRING_TYPE), STDLIB_NAME),
        'bool_of_string': Symbol(MType([STRING_TYPE], BOOL_TYPE), STDLIB_NAME),
        'string_of_bool': Symbol(MType([BOOL_TYPE], STRING_TYPE), STDLIB_NAME),
        'read': Symbol(MType([], STRING_TYPE), STDLIB_NAME),
        'printLn': Symbol(MType([], VOID_TYPE), STDLIB_NAME),
        'print': Symbol(MType([STRING_TYPE], VOID_TYPE), STDLIB_NAME),
        'printStrLn': Symbol(MType([STRING_TYPE], VOID_TYPE), STDLIB_NAME),
    }

    def gen(self, program: Program, dir_: str) -> None:
        """Write Jasmin code for `program` to file <class_name>.j in `dir_`"""
        codegen = CodeGenVisitor(program, self.BUILTIN_FUNCS)
        code = ''.join(codegen)
        filepath = f'{dir_}/{CodeGenVisitor.CLASS_NAME}.j'
        with open(filepath, 'w') as f:
            f.write(code)


class CodeGenVisitor(BaseVisitor):
    """Iterable class for Jasmin code"""

    CLASS_NAME = CName('MCClass')

    LiteralCode = Generator[str, None, Union[Prim, ArrayType]]
    ExprCode = Generator[Union[str, SkipToFunc], None, Type]
    LHSCode = Iterator[Union[str, SkipToFunc, NeedRValue]]
    StmtCode = Iterator[Union[str, SkipToFunc]]

    def __init__(self, ast: Program, initial_symtab: Dict[str, Symbol] = {}):
        self.codegen = self.visitProgram(ast, initial_symtab.copy())

    def __iter__(self) -> Iterator[str]:
        return self.codegen

    def visitProgram(
        self, ast: Program, global_symtab: Dict[str, Symbol]
    ) -> Iterator[str]:
        yield from emitter.emit_header(self.CLASS_NAME)

        # Since VarDecl always appear before FuncDecl,
        # it's OK to use groupby without sorting
        decl_groups = groupby(ast.decl, type)

        decl_type, decls = next(decl_groups)
        if decl_type is VarDecl:
            var_decls = cast(Iterator[VarDecl], decls)
            yield from self.gen_clinit(var_decls, global_symtab)
            _, decls = next(decl_groups)

        yield from self.gen_init()

        global_symtab['main'] = Symbol(
            MType([ArrayType(STRING_TYPE, [0])], VOID_TYPE), self.CLASS_NAME
        )
        func_decls = cast(Iterator[FuncDecl], decls)
        func_gens = {
            func_decl.name.name: self.visitFuncDecl(func_decl, global_symtab)
            for func_decl in func_decls
        }
        entry_point = func_gens.pop('main')
        yield from self.gen_func_decls(entry_point, func_gens)

    def gen_clinit(
        self, var_decls: Iterable[VarDecl], symtab: Dict[str, Symbol]
    ) -> Iterator[str]:
        methodname = '<clinit>'
        methodtype = MType([], VOID_TYPE)

        frame = Frame(methodname, methodtype.rettype)
        frame.func_type = methodtype
        frame.enterScope(True)

        method_env = MethodEnv(frame, ChainMap(symtab))
        var_gens = [self.visitVarDecl(var_decl, method_env) for var_decl in var_decls]
        # Generate static field definitions for global variables
        yield from map(next, var_gens)  # type: ignore

        yield from emitter.emit_method(methodname, methodtype)
        # Generate variable initialization code
        yield from chain.from_iterable(var_gens)
        yield from emitter.emit_return(frame)
        yield from emitter.emit_end_method(frame)

    def gen_init(self) -> Iterator[str]:
        methodname = '<init>'
        methodtype = MType([], VOID_TYPE)
        yield from emitter.emit_method(methodname, methodtype, is_static=False)

        frame = Frame(methodname, methodtype.rettype)
        frame.func_type = methodtype
        frame.enterScope(True)

        varname = 'this'
        varsym = Symbol(ClassType(self.CLASS_NAME), frame.getNewIndex())

        yield from emitter.emit_var(varname, varsym, frame)
        yield from emitter.emit_label(frame.getStartLabel())
        yield from emitter.emit_read_var('this', varsym, frame)
        yield from emitter.emit_invoke_special(frame)
        yield from emitter.emit_label(frame.getEndLabel())
        yield from emitter.emit_return(frame)
        yield from emitter.emit_end_method(frame)

    def gen_func_decls(
        self, func_gen: StmtCode, wait_funcs: Dict[str, StmtCode]
    ) -> Iterator[str]:
        ret = next(func_gen)
        while isinstance(ret, SkipToFunc):
            new_func = wait_funcs.pop(ret.name, None)
            if new_func is not None:
                yield from self.gen_func_decls(new_func, wait_funcs)
            ret = next(func_gen)
        yield ret
        yield from cast(Iterator[str], func_gen)

    def visitVarDecl(self, ast: VarDecl, o: MethodEnv) -> Iterator[str]:
        name = ast.variable.name

        init_gen = self.visit(ast.varInit, o)
        var_type, init_code = self.capture_gen_return(init_gen)

        is_global = len(o.symtab.maps) == 1
        if is_global:
            var_sym = Symbol(var_type, self.CLASS_NAME)
            yield from emitter.emit_field(name, var_sym.type)
        else:
            var_sym = Symbol(var_type, Index(o.frame.getNewIndex()))
            yield from emitter.emit_var(name, var_sym, o.frame)
        o.symtab[name] = var_sym

        yield from iter(init_code)
        yield from emitter.emit_write_var(name, var_sym, o.frame)

    def visitFuncDecl(
        self, ast: FuncDecl, global_symtab: Dict[str, Symbol]
    ) -> StmtCode:
        name = ast.name.name
        func_sym = global_symtab[name]
        func_type = cast(MType, func_sym.type)

        frame = Frame(name, func_type.rettype)
        frame.func_type = func_type
        frame.enterScope(True)

        param_syms = {
            param.variable.name: Symbol(param_type, frame.getNewIndex())
            for param, param_type in zip(ast.param, func_type.partype)
        }
        symtab = ChainMap(param_syms, global_symtab)
        if name == 'main' and not ast.param:
            # Method `main` always has a parameter
            frame.getNewIndex()

        method_env = MethodEnv(frame, symtab)

        body_code = []
        body_gen = self.visit_stmt_list(*ast.body, method_env, new_scope=False)
        for ret in body_gen:
            if isinstance(ret, SkipToFunc):
                yield ret
            else:
                body_code.append(ret)

        yield from emitter.emit_method(name, func_type)
        # Generate .var directives for parameters
        for param in ast.param:
            name = param.variable.name
            param_sym = symtab[name]
            yield from emitter.emit_var(name, param_sym, frame)
        yield from iter(body_code)
        yield from emitter.emit_return(frame)
        yield from emitter.emit_end_method(frame)

    def visitAssign(self, ast: Assign, o: MethodEnv) -> StmtCode:
        lhs_gen = self.visit(ast.lhs, Access(o.frame, o.symtab, rvalue=False))
        ret = next(lhs_gen)
        while not isinstance(ret, NeedRValue):
            yield ret
            ret = next(lhs_gen)
        rhs_access = Access.from_method_env(o, expected_type=ret.left_type)
        yield from self.visit(ast.rhs, rhs_access)
        yield from lhs_gen

    def visitIf(self, ast: If, o: MethodEnv) -> StmtCode:
        cond_access = Access.from_method_env(o, expected_type=BOOL_TYPE)
        end_if_label = o.frame.getNewLabel()

        for if_then_stmt in ast.ifthenStmt:
            cond, var_decls, stmts = if_then_stmt
            yield from self.visit(cond, cond_access)
            false_label = o.frame.getNewLabel()
            yield from emitter.emit_if_false(false_label, o.frame)
            yield from self.visit_stmt_list(var_decls, stmts, o)
            yield from emitter.emit_goto(end_if_label)
            yield from emitter.emit_label(false_label)

        yield from self.visit_stmt_list(*ast.elseStmt, o)
        yield from emitter.emit_label(end_if_label)

    def visitFor(self, ast: For, o: MethodEnv) -> StmtCode:
        o.frame.enterLoop()
        # Assign initial value to index variable
        init_stmt = Assign(ast.idx1, ast.expr1)
        yield from self.visitAssign(init_stmt, o)
        # Start the loop
        start_loop = o.frame.getNewLabel()
        yield from emitter.emit_label(start_loop)
        # Loop condition
        cond_access = Access.from_method_env(o, expected_type=BOOL_TYPE)
        yield from self.visit(ast.expr2, cond_access)
        yield from emitter.emit_if_false(o.frame.getBreakLabel(), o.frame)
        # Loop body
        yield from self.visit_stmt_list(*ast.loop, o)
        # Continue label
        yield from emitter.emit_label(o.frame.getContinueLabel())
        # Update index
        update_stmt = Assign(ast.idx1, BinaryOp('+', ast.idx1, ast.expr3))
        yield from self.visit(update_stmt, o)
        # Return to beginning of the loop
        yield from emitter.emit_goto(start_loop)
        # Break label
        yield from emitter.emit_label(o.frame.getBreakLabel())
        o.frame.exitLoop()

    def visitWhile(self, ast: While, o) -> StmtCode:
        o.frame.enterLoop()
        # Continue label
        yield from emitter.emit_label(o.frame.getContinueLabel())
        # Loop condition
        cond_access = Access.from_method_env(o, expected_type=BOOL_TYPE)
        yield from self.visit(ast.exp, cond_access)
        yield from emitter.emit_if_false(o.frame.getBreakLabel(), o.frame)
        # Loop body
        yield from self.visit_stmt_list(*ast.sl, o)
        # Return to beginning of the loop
        yield from emitter.emit_goto(o.frame.getContinueLabel())
        # Break label
        yield from emitter.emit_label(o.frame.getBreakLabel())
        o.frame.exitLoop()

    def visitDowhile(self, ast: Dowhile, o) -> StmtCode:
        o.frame.enterLoop()
        # Start the loop
        start_loop = o.frame.getNewLabel()
        yield from emitter.emit_label(start_loop)
        # Loop body
        yield from self.visit_stmt_list(*ast.sl, o)
        # Continue label
        yield from emitter.emit_label(o.frame.getContinueLabel())
        # Loop condition
        cond_access = Access.from_method_env(o, expected_type=BOOL_TYPE)
        yield from self.visit(ast.exp, cond_access)
        yield from emitter.emit_if_false(o.frame.getBreakLabel(), o.frame)
        # Return to beginning of the loop
        yield from emitter.emit_goto(start_loop)
        # Break label
        yield from emitter.emit_label(o.frame.getBreakLabel())
        o.frame.exitLoop()

    def visitContinue(self, ast: Continue, o: MethodEnv) -> StmtCode:
        yield from emitter.emit_goto(o.frame.getContinueLabel())

    def visitBreak(self, ast: Break, o: MethodEnv) -> StmtCode:
        yield from emitter.emit_goto(o.frame.getBreakLabel())

    def visitCallStmt(self, ast: CallStmt, o: MethodEnv) -> StmtCode:
        access = Access.from_method_env(o, expected_type=VOID_TYPE)
        call_expr = cast(CallExpr, ast)
        yield from self.visitCallExpr(call_expr, access)

    def visit_stmt_list(
        self,
        var_decls: List[VarDecl],
        stmts: List[Stmt],
        o: MethodEnv,
        new_scope: bool = True,
    ) -> StmtCode:
        if new_scope:
            o.enter_scope()

        var_gens = [self.visitVarDecl(var_decl, o) for var_decl in var_decls]
        # Generate .var directives for local variables
        yield from map(next, var_gens)  # type: ignore

        yield from emitter.emit_label(o.frame.getStartLabel())

        # Generate variable initialization code
        yield from chain.from_iterable(var_gens)
        for stmt in stmts:
            yield from self.visit(stmt, o)

        yield from emitter.emit_label(o.frame.getEndLabel())

        if new_scope:
            o.exit_scope()

    def visitReturn(self, ast: Return, o: MethodEnv) -> StmtCode:
        func_type = o.frame.func_type
        if ast.expr is None:
            func_type.rettype = VOID_TYPE
        else:
            expr_access = Access.from_method_env(o, expected_type=func_type.rettype)
            func_type.rettype = yield from self.visit(ast.expr, expr_access)
        # Jump to the end of function to return value
        yield from emitter.emit_goto(o.frame.endLabel[0])

    def visitId(self, ast: Id, o: Access) -> Union[ExprCode, LHSCode]:
        sym = o.symtab[ast.name]
        if o.rvalue:
            yield from emitter.emit_read_var(ast.name, sym, o.frame)
            return sym.type
        else:
            yield NeedRValue(sym.type)
            yield from emitter.emit_write_var(ast.name, sym, o.frame)

    def visitArrayCell(self, ast: ArrayCell, o: Access) -> Union[ExprCode, LHSCode]:
        expr_access = Access.from_method_env(o)
        array_type = yield from self.visit(ast.arr, expr_access)

        idx_access = Access.from_method_env(o, expected_type=INT_TYPE)
        for idx_expr in ast.idx[:-1]:
            yield from self.visit(idx_expr, idx_access)
            yield from emitter.emit_aaload(o.frame)
        yield from self.visit(ast.idx[-1], idx_access)

        if o.rvalue:
            yield from emitter.emit_aload(array_type.elem_type, o.frame)
            return array_type.elem_type
        else:
            yield NeedRValue(array_type.elem_type)
            yield from emitter.emit_astore(array_type.elem_type, o.frame)

    def visitCallExpr(self, ast: CallExpr, o: Access) -> ExprCode:
        name = ast.method.name
        if name not in o.symtab:
            callee_type = MType([None] * len(ast.param), o.expected_type)  # type: ignore
            callee_sym = Symbol(callee_type, self.CLASS_NAME)
            global_symtab = o.symtab.maps[-1]
            global_symtab[name] = callee_sym  # type: ignore
        else:
            callee_sym = o.symtab[name]
            callee_type = cast(MType, callee_sym.type)
            if o.expected_type:
                callee_type.rettype = o.expected_type

        for i, arg in enumerate(ast.param):
            arg_access = replace(o, expected_type=callee_type.partype[i])
            arg_type = yield from self.visit(arg, arg_access)
            if not callee_type.partype[i] and arg_type:
                callee_type.partype[i] = arg_type

        yield SkipToFunc(name)
        yield from emitter.emit_invoke_static(name, callee_sym, o.frame)
        return callee_type.rettype

    def visitBinaryOp(self, ast: BinaryOp, o: MethodEnv) -> ExprCode:
        operand_type = self.get_operand_type(ast.op)
        operand_access = replace(o, expected_type=operand_type)
        yield from self.visit(ast.left, operand_access)
        right_gen = self.visit(ast.right, operand_access)
        if ast.op not in ['&&', '||']:
            # && and || are short-circuited, so we defer codegen for right operand
            yield from right_gen

        if ast.op[0] == '+':
            yield from emitter.emit_add(operand_type, o.frame)
        elif ast.op[0] == '-':
            yield from emitter.emit_sub(operand_type, o.frame)
        elif ast.op[0] == '*':
            yield from emitter.emit_mul(operand_type, o.frame)
        elif ast.op[0] == '\\':
            yield from emitter.emit_div(operand_type, o.frame)
        elif ast.op == '%':
            yield from emitter.emit_rem(o.frame)
        elif ast.op in ['&&', '||']:
            yield from self.gen_short_logic_op(ast.op == '&&', o.frame, right_gen)
        else:
            # Relational operator
            yield from emitter.emit_cmp(ast.op, operand_type, o.frame)

        if ast.op[0] in ['+', '-', '*', '\\', '%']:
            return operand_type
        else:
            return BOOL_TYPE

    @staticmethod
    def gen_short_logic_op(is_and: bool, frame: Frame, right_gen: ExprCode) -> StmtCode:
        """Generate short-circuit AND and OR operator"""
        yield from emitter.emit_dup(frame)
        skip_label = frame.getNewLabel()
        if is_and:
            yield from emitter.emit_if_false(skip_label, frame)
        else:
            yield from emitter.emit_if_true(skip_label, frame)
        yield from emitter.emit_pop(frame)
        yield from right_gen
        yield from emitter.emit_label(skip_label)

    def visitUnaryOp(self, ast: UnaryOp, o: MethodEnv) -> ExprCode:
        operand_type = self.get_operand_type(ast.op)
        operand_access = replace(o, expected_type=operand_type)
        yield from self.visit(ast.body, operand_access)
        if ast.op[0] == '-':
            yield from emitter.emit_neg(operand_type, o.frame)
            return operand_type
        else:
            yield from emitter.emit_not(o.frame)
            return BOOL_TYPE

    @staticmethod
    def get_operand_type(op: str) -> Prim:
        if op[-1] == '.' or op == '=/=':
            return FLOAT_TYPE
        elif op in ['!', '&&', '||']:
            return BOOL_TYPE
        else:
            return INT_TYPE

    def visitArrayLiteral(self, ast: ArrayLiteral, o: MethodEnv) -> LiteralCode:
        # Simulate an array reference on operand stack
        o.frame.push()
        init_gen = self.gen_init_array(ast, o)
        array_type, init_code = self.capture_gen_return(init_gen)
        o.frame.pop()
        yield from emitter.emit_new_array(array_type, o.frame)
        yield from iter(init_code)
        return array_type

    def gen_init_array(self, ast: ArrayLiteral, o: MethodEnv) -> LiteralCode:
        for i, subarray in enumerate(ast.value):
            yield from emitter.emit_dup(o.frame)
            yield from emitter.emit_integer(i, o.frame)
            if not isinstance(subarray, ArrayLiteral):
                # Last dimension
                subarray_type = yield from self.visit(subarray, o)
                yield from emitter.emit_astore(subarray_type, o.frame)
            else:
                yield from emitter.emit_aaload(o.frame)
                subarray_type = yield from self.gen_init_array(subarray, o)
                yield from emitter.emit_pop(o.frame)
        if not isinstance(subarray_type, ArrayType):
            subarray_type = ArrayType(subarray_type, [len(ast.value)])
        else:
            new_dim = [len(ast.value)] + subarray_type.dim
            subarray_type = replace(subarray_type, dim=new_dim)
        return subarray_type

    @staticmethod
    def capture_gen_return(gen):
        return_value = None

        def handle_gen():
            nonlocal return_value
            return_value = yield from gen

        yield_values = list(handle_gen())
        return return_value, yield_values

    def visitBooleanLiteral(self, ast: BooleanLiteral, o: MethodEnv) -> LiteralCode:
        yield from emitter.emit_integer(ast.value, o.frame)
        return BOOL_TYPE

    def visitIntLiteral(self, ast: IntLiteral, o: MethodEnv) -> LiteralCode:
        yield from emitter.emit_integer(ast.value, o.frame)
        return INT_TYPE

    def visitFloatLiteral(self, ast: FloatLiteral, o: MethodEnv) -> LiteralCode:
        yield from emitter.emit_float(ast.value, o.frame)
        return FLOAT_TYPE

    def visitStringLiteral(self, ast: StringLiteral, o: MethodEnv) -> LiteralCode:
        yield from emitter.emit_string(ast.value, o.frame)
        return STRING_TYPE
