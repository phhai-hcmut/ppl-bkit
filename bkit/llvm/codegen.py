from dataclasses import dataclass, replace
from typing import Iterable, Mapping, cast

from llvmlite import ir

from bkit.checker.exceptions import FunctionNotReturn
from bkit.checker.static_check import AnalysisResult, SymbolId
from bkit.utils import ast
from bkit.utils import type as bkit
from bkit.utils.visitor import BaseVisitor

from .utils import LLVM_BYTE_TYPE, get_llvm_type, is_block_reachable

LLVM_BINARY_ARITH_INSTR = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "\\": "sdiv",
    "+.": "fadd",
    "-.": "fsub",
    "*.": "fmul",
    "\\.": "fdiv",
    "%": "srem",
}

LLVM_UNARY_ARITH_INSTR = {
    "-.": "fneg",
    "-": "neg",
    "!": "not_",
}

TERMINATOR_STATEMENTS = (ast.Continue, ast.Break, ast.Return)


@dataclass
class SideTable:
    resolution_table: Mapping[int, SymbolId]
    type_table: Mapping[SymbolId, bkit.Type]
    value_table: dict[SymbolId, ir.Value]

    def use_symbol(self, ident: ast.Id) -> ir.Value:
        symbol_id = self.resolution_table[id(ident)]
        return self.value_table[symbol_id]


class LLVMCodeGenerator(BaseVisitor):
    def __init__(self):
        self.builder = ir.IRBuilder()
        self.continue_blocks: list[ir.Block]
        self.break_blocks: list[ir.Block]

    def gen(self, program: ast.Program, side_table: AnalysisResult) -> ir.Module:
        self.continue_blocks = []
        self.break_blocks = []
        c = SideTable(
            resolution_table=side_table.resolution_table,
            type_table=side_table.symbol_table,
            value_table={},
        )
        return self.visitProgram(program, c)

    def visitProgram(self, program: ast.Program, c: SideTable) -> ir.Module:
        module = ir.Module()
        module.triple = ""

        # Generate declaration for external functions
        for symbol_id, bkit_type in c.type_table.items():
            llvm_type = get_llvm_type(bkit_type)
            if isinstance(symbol_id, str):
                c.value_table[symbol_id] = ir.Function(module, llvm_type, symbol_id)

        func_defs = []
        # Generate top-level symbols
        for decl in program.decl:
            self.visit(decl, (c, module))
            if isinstance(decl, ast.FuncDecl):
                func_defs.append(decl)

        for func_def in func_defs:
            self._gen_func_def(func_def, c)

        return module

    def visitVarDecl(
        self, var_decl: ast.VarDecl, o: tuple[SideTable, ir.Module]
    ) -> None:
        """Global variable"""
        c, module = o
        ident = var_decl.variable
        llvm_name = ident.name
        llvm_type = get_llvm_type(c.type_table[id(ident)])
        var = ir.GlobalVariable(module, llvm_type, llvm_name)
        var.linkage = "internal"
        if var_decl.varInit is not None:
            var.initializer = self.visit(var_decl.varInit, None)
        c.value_table[id(ident)] = var

    def visitFuncDecl(self, func_decl: ast.FuncDecl, o) -> None:
        side_table, module = o
        ident = func_decl.name
        # bkit_type = side_table[id(ident)]
        # llvm_type = get_llvm_type(bkit_type)
        llvm_type = get_llvm_type(side_table.type_table[id(ident)])
        func = ir.Function(module, llvm_type, ident.name)
        func.linkage = "external" if ident.name == "main" else "internal"
        side_table.value_table[id(ident)] = func

    def _gen_func_def(self, func_decl: ast.FuncDecl, c: SideTable) -> None:
        ident = func_decl.name
        func_sym: ir.Function = c.value_table[id(ident)]

        for param, param_sym in zip(func_decl.param, func_sym.args):
            ident = param.variable
            param_sym.name = "param." + ident.name
            c.value_table[id(ident)] = param_sym

        entry_block = func_sym.append_basic_block("var_decl")
        stmt_block = func_sym.append_basic_block("stmt")

        self.builder.position_at_end(entry_block)
        self.builder.branch(stmt_block)

        self.builder.position_at_end(stmt_block)
        self._visit_stmt_list(*func_decl.body, c)

        exit_block = self.builder.block
        if not exit_block.is_terminated:
            self.builder.ret_void()
            self._check_func_return(func_sym, self.builder.block)

    def _check_func_return(self, func_value: ir.Function, exit_block: ir.Block) -> None:
        if not isinstance(func_value.function_type.return_type, ir.VoidType):
            # Check if we can safely discard last block in case of early return
            if is_block_reachable(func_value, exit_block):
                raise FunctionNotReturn(func_value.name)
            else:
                func_value.blocks.remove(exit_block)

    #####################
    # Statement
    #####################

    def visitAssign(self, assign: ast.Assign, c: SideTable) -> None:
        rhs = self.visit(assign.rhs, c)
        match assign.lhs:
            case ast.Id():
                self.builder.store(rhs, c.use_symbol(assign.lhs))

    def visitCallStmt(self, call_stmt: ast.CallStmt, c: SideTable) -> None:
        self.visitCallExpr(cast(ast.CallExpr, call_stmt), c)

    def visitIf(self, if_stmt: ast.If, c: SideTable) -> None:
        first_if = if_stmt.ifthenStmt[0]
        cond, var_decls, stmts = first_if
        pred = self.visit(cond, c)
        with self.builder.if_else(pred) as (then, otherwise):
            with then:
                self._visit_stmt_list(var_decls, stmts, c)
            with otherwise:
                if len(if_stmt.ifthenStmt) == 1:
                    self._visit_stmt_list(*if_stmt.elseStmt, c)
                else:
                    new_if = replace(if_stmt, ifthenStmt=if_stmt.ifthenStmt[1:])
                    self.visitIf(new_if, c)

    def visitFor(self, for_stmt: ast.For, c: SideTable) -> None:
        loop_var = for_stmt.idx1
        self.visit(ast.Assign(loop_var, for_stmt.expr1), c)
        var_decls, for_body = for_stmt.loop
        update_stmt = ast.Assign(loop_var, ast.BinaryOp("+", loop_var, for_stmt.expr3))
        loop_body = for_body + [update_stmt]
        self._gen_loop(for_stmt.expr2, (var_decls, loop_body), c, True)

    def visitWhile(self, ast: ast.While, c: SideTable) -> None:
        self._gen_loop(ast.exp, ast.sl, c, True)

    def visitDowhile(self, ast: ast.Dowhile, c: SideTable) -> None:
        self._gen_loop(ast.exp, ast.sl, c, False)

    def _gen_loop(
        self,
        cond: ast.Expr,
        body: ast.StmtList,
        c: SideTable,
        check_cond_before: bool,
    ) -> None:
        cond_block = self.builder.append_basic_block()
        body_block = self.builder.append_basic_block()
        next_block = self.builder.append_basic_block()
        self.continue_blocks.append(cond_block)
        self.break_blocks.append(next_block)

        with self.builder.goto_block(cond_block):
            cond_value = self.visit(cond, c)
            self.builder.cbranch(cond_value, body_block, next_block)

        with self.builder.goto_block(body_block):
            self.continue_blocks.append(cond_block)
            self.break_blocks.append(next_block)

            self._visit_stmt_list(*body, c)
            if not self.builder.block.is_terminated:
                self.builder.branch(cond_block)

            self.continue_blocks.pop()
            self.break_blocks.pop()

        self.builder.branch(cond_block if check_cond_before else body_block)
        self.builder.position_at_end(next_block)

    def visitBreak(self, ast: ast.Break, c: SideTable) -> None:
        self.builder.branch(self.break_blocks[-1])

    def visitContinue(self, ast: ast.Continue, c: SideTable) -> None:
        self.builder.branch(self.continue_blocks[-1])

    def visitReturn(self, ast: ast.Return, c: SideTable) -> None:
        if ast.expr is not None:
            self.builder.ret(self.visit(ast.expr, c))
        else:
            self.builder.ret_void()

    def _visit_stmt_list(
        self,
        var_decls: Iterable[ast.VarDecl],
        stmts: Iterable[ast.Stmt],
        o: SideTable,
    ) -> None:
        with self.builder.goto_entry_block():
            for var_decl in var_decls:
                self._gen_local_var(var_decl, o)

        for stmt in stmts:
            self.visit(stmt, o)
            if isinstance(stmt, TERMINATOR_STATEMENTS):
                break

    def _gen_local_var(self, var_decl: ast.VarDecl, c: SideTable) -> None:
        ident = var_decl.variable
        llvm_type = get_llvm_type(c.type_table[id(ident)])
        llvm_value = self.builder.alloca(llvm_type, name=ident.name)
        c.value_table[id(ident)] = llvm_value
        if var_decl.varInit is not None:
            initializer = self.visit(var_decl.varInit, c)
            self.builder.store(initializer, llvm_value)

    ######################
    # Expression
    ######################

    def visitUnaryOp(self, unary_op: ast.UnaryOp, c: SideTable) -> ir.Value:
        return getattr(self.builder, LLVM_UNARY_ARITH_INSTR[unary_op.op])(unary_op.body)

    def visitBinaryOp(self, expr: ast.BinaryOp, symtab: SideTable) -> ir.Instruction:
        if expr.op in ["&&", "||"]:
            return self._gen_short_logic_op(expr, symtab)
        else:
            return self._gen_binary_expr(expr, symtab)

    def _gen_binary_expr(self, expr: ast.BinaryOp, symtab: SideTable) -> ir.Instruction:
        lhs = self.visit(expr.left, symtab)
        rhs = self.visit(expr.right, symtab)
        if expr.op[0] in ["+", "-", "*", "\\", "%"]:
            # Arithmetic
            return getattr(self.builder, LLVM_BINARY_ARITH_INSTR[expr.op])(lhs, rhs)
        else:
            # Relational
            if expr.op == "=/=":
                return self.builder.fcmp_ordered("!=", lhs, rhs)
            elif expr.op[-1] == ".":
                return self.builder.fcmp_ordered(expr.op[:-1], lhs, rhs)
            else:
                return self.builder.icmp_signed(expr.op, lhs, rhs)

    def _gen_short_logic_op(self, expr: ast.BinaryOp, o: SideTable) -> ir.Instruction:
        lhs = self.visit(expr.left, o)
        cur_block = self.builder.block
        rhs_block = self.builder.append_basic_block()
        new_block = self.builder.append_basic_block()
        if expr.op == "&&":
            self.builder.cbranch(lhs, rhs_block, new_block)
        else:
            self.builder.cbranch(lhs, new_block, rhs_block)

        with self.builder.goto_block(rhs_block):
            rhs = self.visit(expr.right, o)

        self.builder.position_at_end(new_block)
        ret_val = self.builder.phi(get_llvm_type(bkit.BOOL_TYPE))
        ret_val.add_incoming(lhs, cur_block)
        ret_val.add_incoming(rhs, rhs_block)
        return ret_val

    def visitArrayCell(self, ast: ast.ArrayCell, c: SideTable):
        return

    def visitCallExpr(self, call_expr: ast.CallExpr, c: SideTable) -> ir.Value:
        func_sym = c.use_symbol(call_expr.method)
        args = [self.visit(arg, c) for arg in call_expr.param]
        return self.builder.call(func_sym, args)

    def visitId(self, var: ast.Id, c: SideTable) -> ir.Value:
        return self.builder.load(c.use_symbol(var))

    def visitBooleanLiteral(
        self, literal: ast.BooleanLiteral, o: SideTable
    ) -> ir.Constant:
        return get_llvm_type(bkit.BOOL_TYPE)(int(literal.value))

    def visitIntLiteral(self, literal: ast.IntLiteral, o: SideTable) -> ir.Constant:
        return get_llvm_type(bkit.INT_TYPE)(literal.value)

    def visitFloatLiteral(self, literal: ast.FloatLiteral, o: SideTable) -> ir.Constant:
        return get_llvm_type(bkit.FLOAT_TYPE)(literal.value)

    def visitStringLiteral(self, literal: ast.StringLiteral, o: SideTable):
        string = bytearray(literal.value.encode())
        # Null-terminated string
        string.append(0)
        llvm_type = ir.ArrayType(LLVM_BYTE_TYPE, len(string))
        llvm_value = ir.GlobalVariable(self.builder.module, llvm_type, ".str")
        llvm_value.initializer = llvm_type(string)
        llvm_value.global_constant = True
        llvm_value.unnamed_addr = True
        llvm_value.linkage = "private"
        llvm_value.align = 1
        int_type = get_llvm_type(bkit.INT_TYPE)
        gep_indices = (int_type(0), int_type(0))
        addr = self.builder.gep(llvm_value, gep_indices, inbounds=True)
        return addr

    def visitArrayLiteral(self, literal: ast.ArrayLiteral, o: SideTable):
        return
