from itertools import chain

from .parser import BKITVisitor
from .utils.ast import *


class ASTGeneration(BKITVisitor):
    def visitProgram(self, ctx):
        var_decl_part = self.visit(ctx.var_decl_part())
        func_decls = list(map(self.visit, ctx.func_decl()))
        return Program(var_decl_part + func_decls)

    def visitVar_decl_part(self, ctx):
        var_decl_stmts = map(self.visit, ctx.var_decl_stmt())
        var_decls = list(chain(*var_decl_stmts))
        return var_decls

    def visitVar_decl_stmt(self, ctx):
        return map(self.visit, ctx.var_decl())

    def visitVar_decl(self, ctx):
        variable, var_dim = self.visit(ctx.declarator())
        var_init = ctx.literal()
        if var_init is not None:
            var_init = self.visit(var_init)
        return VarDecl(variable, var_dim, var_init)

    def visitFunc_decl(self, ctx):
        name = self.visit(ctx.ident())
        func_params = ctx.func_params()
        if func_params is None:
            params = []
        else:
            params = list(self.visit(func_params))
        body = self.visit(ctx.func_body())
        return FuncDecl(name, params, body)

    def visitFunc_params(self, ctx):
        return map(self.visit, ctx.param())

    def visitFunc_body(self, ctx):
        return self.visit(ctx.stmt_list())

    def visitParam(self, ctx):
        variable, var_dim = self.visit(ctx.declarator())
        return VarDecl(variable, var_dim, None)

    def visitDeclarator(self, ctx):
        variable = self.visit(ctx.ident())
        var_dim = list(map(self.visit, ctx.integer()))
        return variable, var_dim

    def visitStmt_list(self, ctx):
        var_decl_part = self.visit(ctx.var_decl_part())
        other_stmts = list(map(self.visit, ctx.other_stmt()))
        return (var_decl_part, other_stmts)

    def visitReturn_stmt(self, ctx):
        return_expr = ctx.expr()
        if return_expr is None:
            expr = None
        else:
            expr = self.visit(return_expr)
        return Return(expr)

    def visitCall_expr(self, ctx):
        method, params = self.visit(ctx.func_call())
        return CallExpr(method, params)

    def visitFunc_call(self, ctx):
        name = self.visit(ctx.ident())
        func_args = ctx.arg_list()
        if func_args is None:
            arg_list = []
        else:
            arg_list = self.visit(func_args)
        return name, arg_list

    def visitArg_list(self, ctx):
        return list(map(self.visit, ctx.expr()))

    def visitAssign_stmt(self, ctx):
        lhs = self.visit(ctx.lhs())
        rhs = self.visit(ctx.expr())
        return Assign(lhs, rhs)

    def visitWhile_stmt(self, ctx):
        cond = self.visit(ctx.expr())
        body = self.visit(ctx.stmt_list())
        return While(cond, body)

    def visitDo_while_stmt(self, ctx):
        body = self.visit(ctx.stmt_list())
        cond = self.visit(ctx.expr())
        return Dowhile(body, cond)

    def visitFor_stmt(self, ctx):
        cond = self.visit(ctx.for_cond())
        loop = self.visit(ctx.stmt_list())
        return For(*cond, loop)

    def visitFor_cond(self, ctx):
        index = self.visit(ctx.ident())
        init_expr = self.visit(ctx.expr(0))
        cond_expr = self.visit(ctx.expr(1))
        update_expr = self.visit(ctx.expr(2))
        return (index, init_expr, cond_expr, update_expr)

    def visitIf_stmt(self, ctx):
        if_then_stmts = list(map(self.visit, ctx.if_then_stmt()))
        else_stmt = ctx.else_stmt()
        if else_stmt is not None:
            else_stmt = self.visit(else_stmt)
        else:
            else_stmt = ([], [])
        return If(if_then_stmts, else_stmt)

    def visitIf_then_stmt(self, ctx):
        cond = self.visit(ctx.expr())
        body = self.visit(ctx.stmt_list())
        return (cond, body[0], body[1])

    def visitElse_stmt(self, ctx):
        return self.visit(ctx.stmt_list())

    def visitCall_stmt(self, ctx):
        method, params = self.visit(ctx.func_call())
        return CallStmt(method, params)

    def visitBreak_stmt(self, ctx):
        return Break()

    def visitCont_stmt(self, ctx):
        return Continue()

    def visitRel_expr(self, ctx):
        return self.visitBinary_expr(ctx)

    def visitBinary_expr(self, ctx):
        left = self.visit(ctx.exprp(0))
        op = self.visit(ctx.getChild(1))
        right = self.visit(ctx.exprp(1))
        return BinaryOp(op, left, right)

    def visitPrefix_expr(self, ctx):
        op = self.visit(ctx.prefix_op())
        body = self.visit(ctx.exprp())
        return UnaryOp(op, body)

    def visitParen_expr(self, ctx):
        return self.visit(ctx.expr())

    def visitIdent(self, ctx):
        return Id(ctx.ID().getText())

    def visitElem_expr(self, ctx):
        arr = self.visit(ctx.primary_expr())
        indexes = list(map(self.visit, ctx.expr()))
        return ArrayCell(arr, indexes)

    def visitInteger_literal(self, ctx):
        return IntLiteral(self.visit(ctx.integer()))

    def visitOctal(self, ctx):
        text = ctx.OCT_INT().getText()
        value = int(text, 8)
        return value

    def visitHex(self, ctx):
        text = ctx.HEX_INT().getText()
        value = int(text, 16)
        return value

    def visitDecimal(self, ctx):
        text = ctx.DEC_INT().getText()
        value = int(text, 10)
        return value

    def visitFloat_literal(self, ctx):
        text = ctx.FLOAT().getText()
        value = float(text)
        return FloatLiteral(value)

    def visitTrue_literal(self, ctx):
        return BooleanLiteral(True)

    def visitFalse_literal(self, ctx):
        return BooleanLiteral(False)

    def visitArray_literal(self, ctx):
        literals = list(map(self.visit, ctx.literal()))
        return ArrayLiteral(literals)

    def visitString_literal(self, ctx):
        text = ctx.STRING().getText()
        return StringLiteral(text)

    def visitTerminal(self, ctx):
        return ctx.getText()
