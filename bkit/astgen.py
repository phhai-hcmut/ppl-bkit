from itertools import chain
from typing import Iterator, List, Tuple

from .parser import BKITParser as P
from .parser import BKITVisitor
from .utils import ast

__all__ = 'ASTGeneration'


class ASTGeneration(BKITVisitor):
    def visitProgram(self, ctx: P.ProgramContext) -> ast.Program:
        var_decl_part = self.visitVar_decl_part(ctx.var_decl_part())
        func_decls = map(self.visitFunc_decl, ctx.func_decl())
        decls = list(chain(var_decl_part, func_decls))
        return ast.Program(decls)

    def visitVar_decl_part(self, ctx: P.Var_decl_partContext) -> Iterator[ast.VarDecl]:
        var_decl_stmts = map(self.visitVar_decl_stmt, ctx.var_decl_stmt())
        var_decls = chain.from_iterable(var_decl_stmts)
        return var_decls

    def visitVar_decl_stmt(self, ctx: P.Var_decl_stmtContext) -> Iterator[ast.VarDecl]:
        return map(self.visitVar_decl, ctx.var_decl())

    def visitVar_decl(self, ctx: P.Var_declContext) -> ast.VarDecl:
        variable, var_dim = self.visitDeclarator(ctx.declarator())
        var_init = ctx.literal()
        if var_init is not None:
            var_init = self.visit(var_init)
        return ast.VarDecl(variable, var_dim, var_init)

    def visitFunc_decl(self, ctx: P.Func_declContext) -> ast.FuncDecl:
        name = self.visitIdent(ctx.ident())
        func_params = ctx.func_params()
        if func_params is None:
            params = []
        else:
            params = list(self.visitFunc_params(func_params))
        body = self.visitFunc_body(ctx.func_body())
        return ast.FuncDecl(name, params, body)

    def visitFunc_params(self, ctx: P.Func_paramsContext) -> Iterator[ast.VarDecl]:
        return map(self.visitParam, ctx.param())

    def visitFunc_body(
        self, ctx: P.Func_bodyContext
    ) -> Tuple[List[ast.VarDecl], List[ast.Stmt]]:
        return self.visitStmt_list(ctx.stmt_list())

    def visitParam(self, ctx: P.ParamContext) -> ast.VarDecl:
        variable, var_dim = self.visitDeclarator(ctx.declarator())
        return ast.VarDecl(variable, var_dim, None)

    def visitDeclarator(self, ctx: P.DeclaratorContext) -> Tuple[ast.Id, List[int]]:
        variable = self.visitIdent(ctx.ident())
        var_dim = map(self.visit, ctx.integer())
        return variable, list(var_dim)

    def visitStmt_list(
        self, ctx: P.Stmt_listContext
    ) -> Tuple[List[ast.VarDecl], List[ast.Stmt]]:
        var_decl_part = self.visitVar_decl_part(ctx.var_decl_part())
        other_stmts = map(self.visit, ctx.other_stmt())
        return list(var_decl_part), list(other_stmts)

    def visitReturn_stmt(self, ctx: P.Return_stmtContext) -> ast.Return:
        return_expr = ctx.expr()
        if return_expr is None:
            expr = None
        else:
            expr = self.visit(return_expr)
        return ast.Return(expr)

    def visitCall_expr(self, ctx: P.Call_exprContext) -> ast.CallExpr:
        method, params = self.visitFunc_call(ctx.func_call())
        return ast.CallExpr(method, params)

    def visitFunc_call(self, ctx: P.Func_callContext) -> Tuple[ast.Id, List[ast.Expr]]:
        name = self.visitIdent(ctx.ident())
        func_args = ctx.arg_list()
        if func_args is None:
            arg_list = []
        else:
            arg_list = list(self.visitArg_list(func_args))
        return name, arg_list

    def visitArg_list(self, ctx: P.Arg_listContext) -> Iterator[ast.Expr]:
        return map(self.visit, ctx.expr())

    def visitAssign_stmt(self, ctx: P.Assign_stmtContext) -> ast.Assign:
        lhs = self.visit(ctx.lhs())
        rhs = self.visit(ctx.expr())
        return ast.Assign(lhs, rhs)

    def visitWhile_stmt(self, ctx: P.While_stmtContext) -> ast.While:
        cond = self.visit(ctx.expr())
        body = self.visitStmt_list(ctx.stmt_list())
        return ast.While(cond, body)

    def visitDo_while_stmt(self, ctx: P.Do_while_stmtContext) -> ast.Dowhile:
        body = self.visitStmt_list(ctx.stmt_list())
        cond = self.visit(ctx.expr())
        return ast.Dowhile(body, cond)

    def visitFor_stmt(self, ctx: P.For_stmtContext) -> ast.For:
        index = self.visitIdent(ctx.ident())
        init_expr = self.visit(ctx.expr(0))
        cond_expr = self.visit(ctx.expr(1))
        update_expr = self.visit(ctx.expr(2))
        loop = self.visitStmt_list(ctx.stmt_list())
        return ast.For(index, init_expr, cond_expr, update_expr, loop)

    def visitIf_stmt(self, ctx: P.If_stmtContext) -> ast.If:
        if_then_stmts = map(self.visitIf_then_stmt, ctx.if_then_stmt())
        else_stmt = ctx.else_stmt()
        if else_stmt is not None:
            else_stmt = self.visitElse_stmt(else_stmt)
        else:
            else_stmt = ([], [])
        return ast.If(list(if_then_stmts), else_stmt)

    def visitIf_then_stmt(
        self, ctx: P.If_then_stmtContext
    ) -> Tuple[ast.Expr, List[ast.VarDecl], List[ast.Stmt]]:
        cond = self.visit(ctx.expr())
        body = self.visitStmt_list(ctx.stmt_list())
        return cond, body[0], body[1]

    def visitElse_stmt(
        self, ctx: P.Else_stmtContext
    ) -> Tuple[List[ast.VarDecl], List[ast.Stmt]]:
        return self.visitStmt_list(ctx.stmt_list())

    def visitCall_stmt(self, ctx: P.Call_stmtContext) -> ast.CallStmt:
        method, params = self.visitFunc_call(ctx.func_call())
        return ast.CallStmt(method, params)

    def visitBreak_stmt(self, ctx: P.Break_stmtContext) -> ast.Break:
        return ast.Break()

    def visitCont_stmt(self, ctx: P.Cont_stmtContext) -> ast.Continue:
        return ast.Continue()

    def visitRel_expr(self, ctx: P.Rel_exprContext) -> ast.BinaryOp:
        return self.visitBinary_expr(ctx)

    def visitBinary_expr(self, ctx: P.Binary_exprContext) -> ast.BinaryOp:
        left = self.visit(ctx.exprp(0))
        op = self.visit(ctx.getChild(1))
        right = self.visit(ctx.exprp(1))
        return ast.BinaryOp(op, left, right)

    def visitPrefix_expr(self, ctx: P.Prefix_exprContext) -> ast.UnaryOp:
        op = self.visit(ctx.prefix_op())
        body = self.visit(ctx.exprp())
        return ast.UnaryOp(op, body)

    def visitParen_expr(self, ctx: P.Paren_exprContext) -> ast.Expr:
        return self.visit(ctx.expr())

    def visitIdent(self, ctx: P.IdentContext) -> ast.Id:
        return ast.Id(ctx.ID().getText())

    def visitElem_expr(self, ctx: P.Elem_exprContext) -> ast.ArrayCell:
        arr = self.visit(ctx.primary_expr())
        indexes = map(self.visit, ctx.expr())
        return ast.ArrayCell(arr, list(indexes))

    def visitInteger_literal(self, ctx: P.Integer_literalContext) -> ast.IntLiteral:
        return ast.IntLiteral(self.visit(ctx.integer()))

    def visitOctal(self, ctx: P.OctalContext) -> int:
        text = ctx.OCT_INT().getText()
        value = int(text, 8)
        return value

    def visitHex(self, ctx: P.OctalContext) -> int:
        text = ctx.HEX_INT().getText()
        value = int(text, 16)
        return value

    def visitDecimal(self, ctx: P.DecimalContext) -> int:
        text = ctx.DEC_INT().getText()
        value = int(text, 10)
        return value

    def visitFloat_literal(self, ctx: P.Float_literalContext) -> ast.FloatLiteral:
        text = ctx.FLOAT().getText()
        value = float(text)
        return ast.FloatLiteral(value)

    def visitTrue_literal(self, ctx: P.True_literalContext) -> ast.BooleanLiteral:
        return ast.BooleanLiteral(True)

    def visitFalse_literal(self, ctx: P.False_literalContext) -> ast.BooleanLiteral:
        return ast.BooleanLiteral(False)

    def visitArray_literal(self, ctx: P.Array_literalContext) -> ast.ArrayLiteral:
        literals = list(map(self.visit, ctx.literal()))
        return ast.ArrayLiteral(literals)

    def visitString_literal(self, ctx: P.String_literalContext) -> ast.StringLiteral:
        text = ctx.STRING().getText()
        return ast.StringLiteral(text)

    def visitTerminal(self, ctx) -> str:
        return ctx.getText()
