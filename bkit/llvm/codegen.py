import os
from dataclasses import dataclass, replace
from math import prod
from typing import Iterable, Mapping, Optional, cast

from llvmlite import ir

from bkit.checker.exceptions import FunctionNotReturn
from bkit.checker.static_check import AnalysisResult, SymbolId
from bkit.utils import ast
from bkit.utils import type as bkit
from bkit.utils.visitor import BaseVisitor

from .utils import LLVM_BYTE_TYPE, LLVM_INT_TYPE, get_llvm_type, is_block_reachable

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

_c_libraries = {
    "malloc": ir.FunctionType(LLVM_BYTE_TYPE.as_pointer(), (ir.IntType(64),)),
}
_llvm_instrincs = {
    "llvm.dbg.declare": ir.FunctionType(ir.VoidType(), [ir.MetaDataType()] * 3),
    "llvm.dbg.value": ir.FunctionType(ir.VoidType(), [ir.MetaDataType()] * 3),
}


@dataclass
class SideTable:
    resolution_table: Mapping[int, SymbolId]
    type_table: Mapping[SymbolId, bkit.Type]
    value_table: dict[SymbolId, ir.Value]
    scope: ir.DIValue

    def use_symbol(self, ident: ast.Id) -> ir.Value:
        symbol_id = self.resolution_table[id(ident)]
        return self.value_table[symbol_id]


@dataclass
class LoopContext(SideTable):
    continue_block: ir.Block
    break_block: ir.Block

    @classmethod
    def from_parent(
        cls, parent: SideTable, continue_block: ir.Block, break_block: ir.Block
    ) -> "LoopContext":
        return cls(
            resolution_table=parent.resolution_table,
            type_table=parent.type_table,
            value_table=parent.value_table,
            scope=parent.scope,
            continue_block=continue_block,
            break_block=break_block,
        )


class LLVMCodeGenerator(BaseVisitor):
    def __init__(
        self,
        program: ast.Program,
        side_table: AnalysisResult,
        source_filename: Optional[str] = None,
        debug=False,
    ):
        if debug and source_filename is None:
            raise ValueError("Must specify source filename for debug build")
        self.program = program
        self._module: ir.Module
        self.side_table = side_table
        self.source_filename = source_filename
        self.debug = debug
        self.builder = ir.IRBuilder()
        self._string_counter: int
        self._compile_unit: ir.DIValue
        self._file: ir.DIValue

    def gen(self) -> ir.Module:
        self._string_counter = 0
        return self.visitProgram(self.program, self.side_table)

    def visit(self, ast: ast.AST, param):
        inst = ast.accept(self, param)
        if isinstance(inst, ir.Instruction) and not isinstance(inst, ir.PhiInstr):
            di_loc = self._add_di_location(ast, param)
            inst.set_metadata("dbg", di_loc)
        return inst

    def visitProgram(
        self, program: ast.Program, side_table: AnalysisResult
    ) -> ir.Module:
        module = ir.Module()
        module.triple = ""
        self._module = module

        self._di_types = {
            bkit.BoolType: module.add_debug_info(
                "DIBasicType",
                {
                    "name": "bool",
                    "size": 1,
                    "encoding": ir.DIToken("DW_ATE_boolean"),
                },
            ),
            bkit.IntType: module.add_debug_info(
                "DIBasicType",
                {
                    "name": "int",
                    "size": 32,
                    "encoding": ir.DIToken("DW_ATE_signed"),
                },
            ),
            bkit.FloatType: module.add_debug_info(
                "DIBasicType",
                {
                    "name": "float",
                    "size": 32,
                    "encoding": ir.DIToken("DW_ATE_float"),
                },
            ),
            # const char *
            bkit.StringType: module.add_debug_info(
                "DIDerivedType",
                {
                    "tag": ir.DIToken("DW_TAG_pointer_type"),
                    "size": 64,
                    "baseType": module.add_debug_info(
                        "DIDerivedType",
                        {
                            "tag": ir.DIToken("DW_TAG_const_type"),
                            "baseType": module.add_debug_info(
                                "DIBasicType",
                                {
                                    "name": "char",
                                    "size": 8,
                                    "encoding": ir.DIToken("DW_ATE_unsigned_char"),
                                },
                            ),
                        },
                    ),
                },
            ),
        }

        self._file = di_file = module.add_debug_info(
            "DIFile", {"directory": os.getcwd(), "filename": self.source_filename}
        )

        c = SideTable(
            resolution_table=side_table.resolution_table,
            type_table=side_table.symbol_table,
            value_table={},
            scope=di_file,
        )
        # Generate declaration for external functions
        for symbol_id, bkit_type in c.type_table.items():
            llvm_type = get_llvm_type(bkit_type)
            if isinstance(symbol_id, str):
                c.value_table[symbol_id] = ir.Function(module, llvm_type, symbol_id)
        for func_name, llvm_type in (_c_libraries | _llvm_instrincs).items():
            c.value_table[func_name] = ir.Function(module, llvm_type, func_name)
        for bkit_type in [
            bkit.BOOL_TYPE,
            bkit.INT_TYPE,
            bkit.FLOAT_TYPE,
            bkit.STRING_TYPE,
        ]:
            llvm_type = ir.FunctionType(
                get_llvm_type(bkit_type).as_pointer(), (LLVM_INT_TYPE,)
            )
            func_name = f"alloc_{type(bkit_type).__name__}_array"
            c.value_table[func_name] = ir.Function(module, llvm_type, func_name)

        func_defs = []
        global_vars = []
        # Generate top-level symbols
        for decl in program.decl:
            ret = self.visit(decl, (c, module))
            if isinstance(decl, ast.FuncDecl):
                func_defs.append(decl)
            else:
                global_vars.append(ret)

        self._compile_unit = module.add_debug_info(
            "DICompileUnit",
            {
                "file": di_file,
                "language": ir.DIToken("DW_LANG_C99"),
                "emissionKind": ir.DIToken("FullDebug"),
                "globals": global_vars,
            },
            is_distinct=True,
        )
        module.add_named_metadata("llvm.dbg.cu", self._compile_unit)
        module.add_named_metadata(
            "llvm.module.flags",
            module.add_metadata((LLVM_INT_TYPE(7), "Dwarf Version", LLVM_INT_TYPE(4))),
        )
        module.add_named_metadata(
            "llvm.module.flags",
            module.add_metadata(
                (LLVM_INT_TYPE(2), "Debug Info Version", LLVM_INT_TYPE(3))
            ),
        )

        for func_def in func_defs:
            self._gen_func_def(func_def, c)

        return module

    def visitVarDecl(self, var_decl: ast.VarDecl, o: tuple[SideTable, ir.Module]):
        """Global variable"""
        c, module = o
        ident = var_decl.variable
        llvm_name = ident.name
        bkit_type = c.type_table[id(ident)]
        llvm_type = get_llvm_type(bkit_type)
        var = ir.GlobalVariable(module, llvm_type, llvm_name)
        var.linkage = "internal"
        if var_decl.varInit is not None:
            if isinstance(bkit_type, bkit.ArrayType):
                llvm_type = llvm_type.pointee
            var.initializer = self.visit(var_decl.varInit, llvm_type)
        c.value_table[id(ident)] = var

        di_global_var = self._add_debug_info(
            "DIGlobalVariable",
            {
                "name": ident.name,
                "scope": c.scope,
                "line": ident.line,
                "file": self._file,
                "type": self._get_di_type(bkit_type),
                "isLocal": True,
            },
            is_distinct=True,
        )
        debug_info = self._add_debug_info(
            "DIGlobalVariableExpression",
            {
                "var": di_global_var,
                "expr": self._add_debug_info("DIExpression", {}),
            },
        )
        var.set_metadata("dbg", debug_info)
        return debug_info

    def visitFuncDecl(
        self, func_decl: ast.FuncDecl, o: tuple[SideTable, ir.Module]
    ) -> None:
        side_table, module = o
        ident = func_decl.name
        llvm_type = get_llvm_type(side_table.type_table[id(ident)])
        func = ir.Function(module, llvm_type, ident.name)
        func.linkage = "external" if ident.name == "main" else "internal"
        side_table.value_table[id(ident)] = func

    def _gen_func_def(self, func_decl: ast.FuncDecl, c: SideTable) -> None:
        ident = func_decl.name
        func_sym: ir.Function = c.value_table[id(ident)]

        di_subprogram = self._module.add_debug_info(
            "DISubprogram",
            {
                "name": ident.name,
                "scope": c.scope,
                "unit": self._compile_unit,
                "file": self._file,
                "line": ident.line,
                "type": self._get_di_type(c.type_table[id(ident)]),
                "linkageName": ident.name,
                "isDefinition": True,
            },
            is_distinct=True,
        )
        func_sym.set_metadata("dbg", di_subprogram)
        c = replace(c, scope=di_subprogram)

        entry_block = func_sym.append_basic_block("var_decl")
        stmt_block = func_sym.append_basic_block("stmt")

        self.builder.position_at_end(entry_block)
        for param, param_sym in zip(func_decl.param, func_sym.args):
            ident = param.variable
            param_sym.name = "param." + ident.name
            c.value_table[id(ident)] = param_sym
            bkit_type = c.type_table[id(ident)]

            di_local_var = self._add_debug_info(
                "DILocalVariable",
                {
                    "name": ident.name,
                    "scope": c.scope,
                    "line": ident.line,
                    "file": self._file,
                    "type": self._get_di_type(bkit_type),
                },
            )
            self.builder.call(
                c.value_table["llvm.dbg.value"],
                (param_sym, di_local_var, self._add_debug_info("DIExpression", {})),
            ).set_metadata("dbg", self._add_di_location(ident, c))
        self.builder.branch(stmt_block)

        self.builder.position_at_end(stmt_block)
        self._visit_stmt_list(*func_decl.body, c, new_scope=False)

        last_block = self.builder.block
        if not last_block.is_terminated:
            self.builder.ret_void()
            self._check_func_return(func_sym, last_block)

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

    def visitAssign(self, assign: ast.Assign, c: SideTable):
        rhs = self.visit(assign.rhs, c)
        match assign.lhs:
            case ast.Id():
                addr = c.use_symbol(assign.lhs)
            case ast.ArrayCell():
                addr = self._get_array_elem_addr(assign.lhs, c)
        return self.builder.store(rhs, addr)

    def visitCallStmt(self, call_stmt: ast.CallStmt, c: SideTable) -> ir.Instruction:
        return self.visitCallExpr(cast(ast.CallExpr, call_stmt), c)

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

        cond_block, body_block, next_block = self._gen_loop(
            for_stmt.expr2, for_stmt.loop, c
        )
        self.builder.branch(cond_block)
        with self.builder.goto_block(body_block):
            self.visit(
                ast.Assign(loop_var, ast.BinaryOp("+", loop_var, for_stmt.expr3)), c
            )
        self.builder.position_at_end(next_block)

    def visitWhile(self, ast: ast.While, c: SideTable) -> None:
        cond_block, body_block, next_block = self._gen_loop(ast.exp, ast.sl, c)
        self.builder.branch(cond_block)
        self.builder.position_at_end(next_block)

    def visitDowhile(self, ast: ast.Dowhile, c: SideTable) -> None:
        cond_block, body_block, next_block = self._gen_loop(ast.exp, ast.sl, c)
        self.builder.branch(body_block)
        self.builder.position_at_end(next_block)

    def _gen_loop(
        self,
        cond: ast.Expr,
        body: ast.StmtList,
        c: SideTable,
    ) -> tuple[ir.Block, ir.Block, ir.Block]:
        cond_block = self.builder.append_basic_block()
        body_block = self.builder.append_basic_block()
        next_block = self.builder.append_basic_block()

        with self.builder.goto_block(cond_block):
            cond_value = self.visit(cond, c)
            self.builder.cbranch(cond_value, body_block, next_block)

        with self.builder.goto_block(body_block):
            loop_context = LoopContext.from_parent(c, cond_block, next_block)
            self._visit_stmt_list(*body, loop_context)
            if not self.builder.block.is_terminated:
                self.builder.branch(cond_block)

        return cond_block, body_block, next_block

    def visitBreak(self, ast: ast.Break, c: LoopContext) -> ir.Instruction:
        return self.builder.branch(c.break_block)

    def visitContinue(self, ast: ast.Continue, c: LoopContext) -> ir.Instruction:
        return self.builder.branch(c.continue_block)

    def visitReturn(self, ast: ast.Return, c: SideTable) -> ir.Instruction:
        if ast.expr is not None:
            return self.builder.ret(self.visit(ast.expr, c))
        else:
            return self.builder.ret_void()

    def _visit_stmt_list(
        self,
        var_decls: Iterable[ast.VarDecl],
        stmts: Iterable[ast.Stmt],
        o: SideTable,
        new_scope: bool = True,
    ) -> None:
        if new_scope:
            di_scope = self._add_debug_info('DILexicalBlock', {
                'scope': o.scope,
                'file': self._file,
                }, is_distinct=True)
            o = replace(o, scope=di_scope)
        with self.builder.goto_entry_block():
            for var_decl in var_decls:
                self._gen_local_var(var_decl, o)

        for stmt in stmts:
            self.visit(stmt, o)
            if isinstance(stmt, TERMINATOR_STATEMENTS):
                break

    def _gen_local_var(self, var_decl: ast.VarDecl, c: SideTable) -> None:
        ident = var_decl.variable
        di_loc = self._add_di_location(ident, c)
        bkit_type = c.type_table[id(ident)]
        llvm_type = get_llvm_type(bkit_type)
        if isinstance(bkit_type, bkit.ArrayType):
            malloc = c.value_table[f"alloc_{type(bkit_type.elem_type).__name__}_array"]
            array_size = LLVM_INT_TYPE(prod(bkit_type.dim))
            addr = self.builder.call(malloc, (array_size,))
            llvm_value = self.builder.bitcast(addr, llvm_type)
        else:
            llvm_value = self.builder.alloca(llvm_type, name=ident.name)
        c.value_table[id(ident)] = llvm_value

        di_local_var = self._add_debug_info(
            "DILocalVariable",
            {
                "name": ident.name,
                "scope": c.scope,
                "line": ident.line,
                "file": self._file,
                "type": self._get_di_type(bkit_type),
            },
        )
        dbg_declare = self.builder.call(
            c.value_table["llvm.dbg.declare"],
            (llvm_value, di_local_var, self._add_debug_info("DIExpression", {})),
        )
        dbg_declare.metadata["dbg"] = self._add_debug_info(
            "DILocation", {"line": ident.line, "column": ident.column, "scope": c.scope}
        )

        if var_decl.varInit is not None:
            if isinstance(bkit_type, bkit.ArrayType):
                llvm_type = llvm_type.pointee
            initializer = self.visit(var_decl.varInit, llvm_type)
            self.builder.store(initializer, llvm_value).set_metadata("dbg", di_loc)

    def _get_type_size(self, llvm_type: ir.Type) -> ir.Value:
        x = self.builder.gep(llvm_type.as_pointer()(None), (ir.IntType(32)(1),))
        return self.builder.ptrtoint(x, ir.IntType(64))

    ######################
    # Expression
    ######################

    def visitUnaryOp(self, unary_op: ast.UnaryOp, c: SideTable) -> ir.Value:
        inst = getattr(self.builder, LLVM_UNARY_ARITH_INSTR[unary_op.op])(unary_op.body)
        inst.metadata["dbg"] = self._add_debug_info(
            "DILocation",
            {"line": unary_op.line, "column": unary_op.column, "scope": c.scope},
        )
        return inst

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
        di_loc = self._add_di_location(expr, o)
        lhs = self.visit(expr.left, o)
        cur_block = self.builder.block
        rhs_block = self.builder.append_basic_block()
        new_block = self.builder.append_basic_block()
        if expr.op == "&&":
            lhs_inst = self.builder.cbranch(lhs, rhs_block, new_block)
        else:
            lhs_inst = self.builder.cbranch(lhs, new_block, rhs_block)
        lhs_inst.set_metadata("dbg", di_loc)

        with self.builder.goto_block(rhs_block):
            rhs = self.visit(expr.right, o)
            self.builder.branch(new_block).set_metadata("dbg", di_loc)

        self.builder.position_at_end(new_block)
        ret_val = self.builder.phi(get_llvm_type(bkit.BOOL_TYPE))
        ret_val.add_incoming(lhs, cur_block)
        ret_val.add_incoming(rhs, rhs_block)
        return ret_val

    def visitCallExpr(self, call_expr: ast.CallExpr, c: SideTable) -> ir.Value:
        func_sym = c.use_symbol(call_expr.method)
        args = [self.visit(arg, c) for arg in call_expr.param]
        return self.builder.call(func_sym, args)

    def visitId(self, var: ast.Id, c: SideTable) -> ir.Value:
        di_loc = self._add_di_location(var, c)
        addr = c.use_symbol(var)
        bkit_type = c.type_table[c.resolution_table[id(var)]]
        if isinstance(bkit_type, bkit.ArrayType):
            return addr
        else:
            inst = self.builder.load(addr)
            inst.set_metadata("dbg", di_loc)
            return inst

    def visitArrayCell(self, ast: ast.ArrayCell, c: SideTable) -> ir.Value:
        addr = self._get_array_elem_addr(ast, c)
        return self.builder.load(addr)

    def _get_array_elem_addr(self, ast: ast.ArrayCell, c: SideTable) -> ir.Value:
        di_loc = self._add_di_location(ast, c)
        arr = self.visit(ast.arr, c)
        indices = [get_llvm_type(bkit.INT_TYPE)(0)]
        indices += [self.visit(idx, c) for idx in ast.idx]
        inst = self.builder.gep(arr, indices, inbounds=True)
        inst.set_metadata("dbg", di_loc)
        return inst

    def visitBooleanLiteral(
        self, literal: ast.BooleanLiteral, o: SideTable
    ) -> ir.Constant:
        return get_llvm_type(bkit.BOOL_TYPE)(literal.value)

    def visitIntLiteral(self, literal: ast.IntLiteral, o: SideTable) -> ir.Constant:
        return get_llvm_type(bkit.INT_TYPE)(literal.value)

    def visitFloatLiteral(self, literal: ast.FloatLiteral, o: SideTable) -> ir.Constant:
        return get_llvm_type(bkit.FLOAT_TYPE)(literal.value)

    def visitStringLiteral(self, literal: ast.StringLiteral, o: SideTable):
        string = bytearray(literal.value.encode())
        # Null-terminated string
        string.append(0)
        llvm_type = ir.ArrayType(LLVM_BYTE_TYPE, len(string))
        llvm_name = ".str." + str(self._string_counter)
        self._string_counter += 1
        llvm_value = ir.GlobalVariable(self.builder.module, llvm_type, llvm_name)
        llvm_value.initializer = llvm_type(string)
        llvm_value.global_constant = True
        llvm_value.unnamed_addr = True
        llvm_value.linkage = "private"
        llvm_value.align = 1
        int_type = get_llvm_type(bkit.INT_TYPE)
        gep_indices = (int_type(0), int_type(0))
        addr = self.builder.gep(llvm_value, gep_indices, inbounds=True)
        return addr

    def visitArrayLiteral(
        self, literal: ast.ArrayLiteral, t: ir.ArrayType
    ) -> ir.Constant:
        return t(self.visit(literal, t.element) for literal in literal.value)

    def _add_debug_info(
        self, kind: str, operands: dict, is_distinct: bool = False
    ) -> ir.DIValue:
        return self._module.add_debug_info(kind, operands, is_distinct)

    def _add_di_location(self, ast: ast.AST, side_table: SideTable) -> ir.DIValue:
        return self._add_debug_info(
            "DILocation",
            {"line": ast.line, "column": ast.column, "scope": side_table.scope},
        )

    def _get_di_type(self, bkit_type: bkit.Type) -> ir.DIValue:
        match bkit_type:
            case bkit.VoidType():
                return None
            case bkit.ArrayType(elem_type=elem_type, dim=dims):
                base_type = self._get_di_type(elem_type)
                elements = [
                    self._module.add_debug_info("DISubrange", {"count": dim})
                    for dim in dims
                ]
                return self._module.add_debug_info(
                    "DICompositeType",
                    {
                        "tag": ir.DIToken("DW_TAG_array_type"),
                        "baseType": base_type,
                        "elements": elements,
                    },
                )
            case bkit.FuncType(intype=intype, restype=restype):
                types = [self._get_di_type(restype)] + list(
                    map(self._get_di_type, intype)
                )
                return self._module.add_debug_info("DISubroutineType", {"types": types})
            case _:
                bkit_type = cast(bkit.Prim, bkit_type)
                return self._di_types[type(bkit_type)]
