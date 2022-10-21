import unittest
from dataclasses import asdict
from pprint import pformat

from antlr4 import CommonTokenStream, InputStream

from bkit.astgen import ASTGeneration
from bkit.parser import BKITLexer, BKITParser
from bkit.utils.ast import *


class TestAST(unittest.TestCase):
    def check_astgen(self, input, expect):
        lexer = BKITLexer(InputStream(input))
        tokens = CommonTokenStream(lexer)
        parser = BKITParser(tokens)
        # parser.setTrace(True)
        tree = parser.program()
        asttree = ASTGeneration().visit(tree)
        self.assertEqual(
            str(asttree), str(expect), "\n" + pformat(asdict(asttree))
        )  # +"\n"+pformat(asdict(expect)))


class TestLong(TestAST):
    def test_number_94(self):
        """full program structure"""
        input = """
Var: a[6][5];
Var: b=5;
Function: main
    Parameter: a, b, c[6][7]
    Body:
        Var: g[7] = {1, 2, 3};
        If g != null Then
            print_list(g);
            Return;
        EndIf.
        print("Null list");
        EndBody.
Function: print_list
    Parameter: g[100]
    Body:
        elem = g[0];
        i=0;
        While elem != null Do
            print(elem);
            i = i+1;
            elem = g[i];
        EndWhile.
    EndBody.
"""
        expect = "Program([VarDecl(Id(a),[6,5]),VarDecl(Id(b),IntLiteral(5)),FuncDecl(Id(main)[VarDecl(Id(a)),VarDecl(Id(b)),VarDecl(Id(c),[6,7])],([VarDecl(Id(g),[7],ArrayLiteral(IntLiteral(1),IntLiteral(2),IntLiteral(3)))][If(BinaryOp(!=,Id(g),Id(null)),[],[CallStmt(Id(print_list),[Id(g)]),Return()])Else([],[]),CallStmt(Id(print),[StringLiteral('Null list')])])),FuncDecl(Id(print_list)[VarDecl(Id(g),[100])],([][Assign(Id(elem),ArrayCell(Id(g),[IntLiteral(0)])),Assign(Id(i),IntLiteral(0)),While(BinaryOp(!=,Id(elem),Id(null)),[],[CallStmt(Id(print),[Id(elem)]),Assign(Id(i),BinaryOp(+,Id(i),IntLiteral(1))),Assign(Id(elem),ArrayCell(Id(g),[Id(i)]))])]))])"
        self.check_astgen(input, expect)

    def test_number_95(self):
        """full program structure"""
        input = """
Var: a,b;
Function: main
    Body:
    Var: x,y[1],y={1}, g[2][3]= "String";
    f(g)[1] = {1,2,3};
    For (i=0, i<len(g), 1%2) Do
        For (j=0,j<len(g[i]),3-2) Do
            If g[i][j] \\5 %(2+2*2) <= f(g[0])[0] Then
                print(g[i][j]);
            Else
                Continue;
            EndIf.
        EndFor.
    EndFor.
EndBody.
Function: f
    Parameter: any
    Body:
        Return any;
    EndBody.
"""
        expect = "Program([VarDecl(Id(a)),VarDecl(Id(b)),FuncDecl(Id(main)[],([VarDecl(Id(x)),VarDecl(Id(y),[1]),VarDecl(Id(y),ArrayLiteral(IntLiteral(1))),VarDecl(Id(g),[2,3],StringLiteral('String'))][Assign(ArrayCell(CallExpr(Id(f),[Id(g)]),[IntLiteral(1)]),ArrayLiteral(IntLiteral(1),IntLiteral(2),IntLiteral(3))),For(Id(i),IntLiteral(0),BinaryOp(<,Id(i),CallExpr(Id(len),[Id(g)])),BinaryOp(%,IntLiteral(1),IntLiteral(2)),[],[For(Id(j),IntLiteral(0),BinaryOp(<,Id(j),CallExpr(Id(len),[ArrayCell(Id(g),[Id(i)])])),BinaryOp(-,IntLiteral(3),IntLiteral(2)),[],[If(BinaryOp(<=,BinaryOp(%,BinaryOp(\\,ArrayCell(Id(g),[Id(i),Id(j)]),IntLiteral(5)),BinaryOp(+,IntLiteral(2),BinaryOp(*,IntLiteral(2),IntLiteral(2)))),ArrayCell(CallExpr(Id(f),[ArrayCell(Id(g),[IntLiteral(0)])]),[IntLiteral(0)])),[],[CallStmt(Id(print),[ArrayCell(Id(g),[Id(i),Id(j)])])])Else([],[Continue()])])])])),FuncDecl(Id(f)[VarDecl(Id(any))],([][Return(Id(any))]))])"
        self.check_astgen(input, expect)

    def test_number_96(self):
        """full program structure"""
        input = 'Var: a,b=2e-13,d[2]=0x12; Function: main Body: a=1+2%3 \\ (5>6) == -True || !"False" --3 +-3 -!3 && {1}; If a%2 == 0 Then b= True ||2.3 * 5 == 3 && 1 + -6 ; Else b= False; EndIf. print(f()[5],a,print(b),c[2]); EndBody.'
        expect = "Program([VarDecl(Id(a)),VarDecl(Id(b),FloatLiteral(2e-13)),VarDecl(Id(d),[2],IntLiteral(18)),FuncDecl(Id(main)[],([][Assign(Id(a),BinaryOp(==,BinaryOp(+,IntLiteral(1),BinaryOp(\\,BinaryOp(%,IntLiteral(2),IntLiteral(3)),BinaryOp(>,IntLiteral(5),IntLiteral(6)))),BinaryOp(&&,BinaryOp(||,UnaryOp(-,BooleanLiteral(true)),BinaryOp(-,BinaryOp(+,BinaryOp(-,UnaryOp(!,StringLiteral('False')),UnaryOp(-,IntLiteral(3))),UnaryOp(-,IntLiteral(3))),UnaryOp(!,IntLiteral(3)))),ArrayLiteral(IntLiteral(1))))),If(BinaryOp(==,BinaryOp(%,Id(a),IntLiteral(2)),IntLiteral(0)),[],[Assign(Id(b),BinaryOp(==,BinaryOp(||,BooleanLiteral(true),BinaryOp(*,FloatLiteral(2.3),IntLiteral(5))),BinaryOp(&&,IntLiteral(3),BinaryOp(+,IntLiteral(1),UnaryOp(-,IntLiteral(6))))))])Else([],[Assign(Id(b),BooleanLiteral(false))]),CallStmt(Id(print),[ArrayCell(CallExpr(Id(f),[]),[IntLiteral(5)]),Id(a),CallExpr(Id(print),[Id(b)]),ArrayCell(Id(c),[IntLiteral(2)])])]))])"
        self.check_astgen(input, expect)

    def test_number_97(self):
        """full program structure"""
        input = 'Var: n; Function: switch Parameter: n Body: If n == 1 Then print("+"); ElseIf n==2 Then print(n,"Even"); ElseIf n ==3 Then Return False; ElseIf n ==4 Then Return switch(5); ElseIf n==5 Then Return {1,2,3,{4,5,{6}}, 7, {8}};  ElseIf n==6 Then Return switch(5)[3]; Else print("Cant think of anything :)), brain dead!");  EndIf. EndBody.'
        expect = "Program([VarDecl(Id(n)),FuncDecl(Id(switch)[VarDecl(Id(n))],([][If(BinaryOp(==,Id(n),IntLiteral(1)),[],[CallStmt(Id(print),[StringLiteral('+')])])ElseIf(BinaryOp(==,Id(n),IntLiteral(2)),[],[CallStmt(Id(print),[Id(n),StringLiteral('Even')])])ElseIf(BinaryOp(==,Id(n),IntLiteral(3)),[],[Return(BooleanLiteral(false))])ElseIf(BinaryOp(==,Id(n),IntLiteral(4)),[],[Return(CallExpr(Id(switch),[IntLiteral(5)]))])ElseIf(BinaryOp(==,Id(n),IntLiteral(5)),[],[Return(ArrayLiteral(IntLiteral(1),IntLiteral(2),IntLiteral(3),ArrayLiteral(IntLiteral(4),IntLiteral(5),ArrayLiteral(IntLiteral(6))),IntLiteral(7),ArrayLiteral(IntLiteral(8))))])ElseIf(BinaryOp(==,Id(n),IntLiteral(6)),[],[Return(ArrayCell(CallExpr(Id(switch),[IntLiteral(5)]),[IntLiteral(3)]))])Else([],[CallStmt(Id(print),[StringLiteral('Cant think of anything :)), brain dead!')])])]))])"
        self.check_astgen(input, expect)

    def test_number_98(self):
        """full program structure"""
        input = 'Var: plus="+"; Function: print_pattern Parameter: line_number, char Body: For (i=0, i<line_number, 1) Do Var: j; j= i+1; While j>0 Do print(char); EndWhile. print("\\n"); EndFor. EndBody. Function: main Body: print_pattern(10,plus); EndBody.'
        expect = """Program([VarDecl(Id(plus),StringLiteral('+')),FuncDecl(Id(print_pattern)[VarDecl(Id(line_number)),VarDecl(Id(char))],([][For(Id(i),IntLiteral(0),BinaryOp(<,Id(i),Id(line_number)),IntLiteral(1),[VarDecl(Id(j))],[Assign(Id(j),BinaryOp(+,Id(i),IntLiteral(1))),While(BinaryOp(>,Id(j),IntLiteral(0)),[],[CallStmt(Id(print),[Id(char)])]),CallStmt(Id(print),[StringLiteral('\\n')])])])),FuncDecl(Id(main)[],([][CallStmt(Id(print_pattern),[IntLiteral(10),Id(plus)])]))])"""
        self.check_astgen(input, expect)


##
STMT_INPUT_TMPL = """
Function: main
    Body:
        {}
    EndBody.
"""
EXPR_TEST_TMPL = STMT_INPUT_TMPL.format("Return {};")


def stmt_expect_tmpl(ast):
    return Program([FuncDecl(Id("main"), [], ([], [ast]))])


def expr_expect_tmpl(ast):
    return stmt_expect_tmpl(Return(ast))


class TestVariableDeclaration(TestAST):
    def test_simple_var_decl(self):
        input = "Var: x;"
        expect = Program([VarDecl(Id("x"), [], None)])
        self.check_astgen(input, expect)

    def test_decl_array(self):
        input = "Var: x[5];"
        expect = Program([VarDecl(Id("x"), [5], None)])
        self.check_astgen(input, expect)

    def test_decl_arrays(self):
        input = "Var: x[5], y[5];"
        expect = Program([VarDecl(Id("x"), [5], None), VarDecl(Id("y"), [5], None)])
        self.check_astgen(input, expect)

    def test_decl_mult_dims_array(self):
        """Test declare multi-dimensional array"""
        input = "Var: x[5][5];"
        expect = Program([VarDecl(Id("x"), [5, 5], None)])
        self.check_astgen(input, expect)

    def test_var_decl_with_init(self):
        input = "Var: x = 1;"
        expect = Program([VarDecl(Id("x"), [], IntLiteral(1))])
        self.check_astgen(input, expect)

    def test_var_decl_with_dim(self):
        input = "Var: x[1] = 0;"
        expect = Program([VarDecl(Id("x"), [1], IntLiteral(0))])
        self.check_astgen(input, expect)

    def test_var_decl_with_dims(self):
        input = "Var: x[1][2] = 0;"
        expect = Program([VarDecl(Id("x"), [1, 2], IntLiteral(0))])
        self.check_astgen(input, expect)

    def test_multiple_var_decl(self):
        input = "Var: x, y;"
        expect = Program([VarDecl(Id("x"), [], None), VarDecl(Id("y"), [], None)])
        self.check_astgen(input, expect)

    def test_multiple_var_decl_with_init(self):
        input = "Var: x, y = 1;"
        expect = Program(
            [VarDecl(Id("x"), [], None), VarDecl(Id("y"), [], IntLiteral(1))]
        )
        self.check_astgen(input, expect)

    def test_decl_arr_var_with_init(self):
        input = "Var: x[1] = {0};"
        expect = Program([VarDecl(Id("x"), [1], ArrayLiteral([IntLiteral(0)]))])
        self.check_astgen(input, expect)

    def test_multiple_var_decl_stmt(self):
        input = "Var: x; Var: y;"
        expect = Program([VarDecl(Id("x"), [], None), VarDecl(Id("y"), [], None)])
        self.check_astgen(input, expect)

    def test_multiple_var_decl_stmt2(self):
        input = "Var: x; Var: y, z;"
        expect = Program(
            [
                VarDecl(Id("x"), [], None),
                VarDecl(Id("y"), [], None),
                VarDecl(Id("z"), [], None),
            ]
        )
        self.check_astgen(input, expect)


class TestFunction(TestAST):
    def test_empty_func(self):
        """Test function with no parameter and empty body."""
        input = """
Function: main
    Body:
    EndBody.
"""
        expect = Program([FuncDecl(Id("main"), [], ([], []))])
        self.check_astgen(input, expect)

    def test_empty_func2(self):
        """Test function with a parameter and empty body."""
        input = """
Function: main
    Parameter: x
    Body:
    EndBody.
"""
        expect = Program([FuncDecl(Id("main"), [VarDecl(Id("x"), [], None)], ([], []))])
        self.check_astgen(input, expect)

    def test_func_with_params(self):
        """Test function with multiple parameters."""
        input = """
Function: main
    Parameter: x, y
    Body:
    EndBody.
"""
        expect = Program(
            [
                FuncDecl(
                    Id("main"),
                    [VarDecl(Id("x"), [], None), VarDecl(Id("y"), [], None)],
                    ([], []),
                )
            ]
        )
        self.check_astgen(input, expect)

    def test_func_with_params2(self):
        """Test function with composite parameters."""
        input = """
Function: main
    Parameter: x, y[1], z[2][3]
    Body:
    EndBody.
"""
        expect = Program(
            [
                FuncDecl(
                    Id("main"),
                    [
                        VarDecl(Id("x"), [], None),
                        VarDecl(Id("y"), [1], None),
                        VarDecl(Id("z"), [2, 3], None),
                    ],
                    ([], []),
                )
            ]
        )
        self.check_astgen(input, expect)

    def test_simple_func(self):
        """Test function with no parameter and a simple body."""
        input = """
Function: main
    Body:
        Return;
    EndBody.
"""
        expect = Program([FuncDecl(Id("main"), [], ([], [Return(None)]))])
        self.check_astgen(input, expect)

    def test_func_with_var(self):
        """Test function with local variable declaration."""
        input = """
Function: main
    Body:
        Var: x;
    EndBody.
"""
        expect = Program([FuncDecl(Id("main"), [], ([VarDecl(Id("x"), [], None)], []))])
        self.check_astgen(input, expect)

    def test_func_with_complete_body(self):
        """Test function with body contain variable declaration and other statement."""
        input = """
Function: main
    Body:
        Var: x;
        Return;
    EndBody.
"""
        expect = Program(
            [FuncDecl(Id("main"), [], ([VarDecl(Id("x"), [], None)], [Return(None)]))]
        )
        self.check_astgen(input, expect)

    def test_func_with_complete_body2(self):
        """Test function with body contain variable declarations and other statements."""
        input = """
Function: main
    Body:
        Var: x, y;
        Break;
        Return;
    EndBody.
"""
        expect = Program(
            [
                FuncDecl(
                    Id("main"),
                    [],
                    (
                        [VarDecl(Id("x"), [], None), VarDecl(Id("y"), [], None)],
                        [Break(), Return(None)],
                    ),
                )
            ]
        )
        self.check_astgen(input, expect)

    def test_multiple_func_decls(self):
        input = """
Function: test
    Body:
    EndBody.
Function: main
    Body:
    EndBody.
"""
        expect = Program(
            [FuncDecl(Id("test"), [], ([], [])), FuncDecl(Id("main"), [], ([], []))]
        )
        self.check_astgen(input, expect)


class TestExpression(TestAST):
    def test_decimal_integer(self):
        input = EXPR_TEST_TMPL.format("0")
        expect = expr_expect_tmpl(IntLiteral(0))
        self.check_astgen(input, expect)

    def test_octal_integer(self):
        input = EXPR_TEST_TMPL.format("0o10")
        expect = expr_expect_tmpl(IntLiteral(8))
        self.check_astgen(input, expect)

    def test_hexadecimal(self):
        input = EXPR_TEST_TMPL.format("0x10")
        expect = expr_expect_tmpl(IntLiteral(16))
        self.check_astgen(input, expect)

    def test_float_literal(self):
        input = EXPR_TEST_TMPL.format("1.00")
        expect = expr_expect_tmpl(FloatLiteral(1.0))
        self.check_astgen(input, expect)

    def test_float_literal_with_exponent(self):
        input = EXPR_TEST_TMPL.format("1e1")
        expect = expr_expect_tmpl(FloatLiteral(10.0))
        self.check_astgen(input, expect)

    def test_float_literal_with_negative_exponent(self):
        input = EXPR_TEST_TMPL.format("1e-1")
        expect = expr_expect_tmpl(FloatLiteral(0.1))
        self.check_astgen(input, expect)

    def test_float_literal_with_decimal_and_exponent(self):
        input = EXPR_TEST_TMPL.format("1.5e1")
        expect = expr_expect_tmpl(FloatLiteral(15.0))
        self.check_astgen(input, expect)

    def test_string_literal(self):
        input = EXPR_TEST_TMPL.format('"a"')
        expect = expr_expect_tmpl(StringLiteral("a"))
        self.check_astgen(input, expect)

    def test_true_literal(self):
        input = EXPR_TEST_TMPL.format("True")
        expect = expr_expect_tmpl(BooleanLiteral(True))
        self.check_astgen(input, expect)

    def test_false_literal(self):
        input = EXPR_TEST_TMPL.format("False")
        expect = expr_expect_tmpl(BooleanLiteral(False))
        self.check_astgen(input, expect)

    def test_array_literal(self):
        """Test array literal contain one element"""
        input = EXPR_TEST_TMPL.format("{0}")
        expect = expr_expect_tmpl(ArrayLiteral([IntLiteral(0)]))
        self.check_astgen(input, expect)

    def test_array_literal2(self):
        """Test array literal contain many elements"""
        input = EXPR_TEST_TMPL.format("{0,1}")
        expect = expr_expect_tmpl(ArrayLiteral([IntLiteral(0), IntLiteral(1)]))
        self.check_astgen(input, expect)

    def test_nested_array_literal(self):
        """Test nested array literal contain one element"""
        input = EXPR_TEST_TMPL.format("{{0}}")
        expect = expr_expect_tmpl(ArrayLiteral([ArrayLiteral([IntLiteral(0)])]))
        self.check_astgen(input, expect)

    def test_nested_array_literal2(self):
        """Test nested array literal contain many elements"""
        input = EXPR_TEST_TMPL.format("{{0},{1}}")
        expect = expr_expect_tmpl(
            ArrayLiteral([ArrayLiteral([IntLiteral(0)]), ArrayLiteral([IntLiteral(1)])])
        )
        self.check_astgen(input, expect)

    def test_array_literal_with_types(self):
        """Test array literal contain many elements of different types"""
        input = EXPR_TEST_TMPL.format('{0,"a"}')
        expect = expr_expect_tmpl(ArrayLiteral([IntLiteral(0), StringLiteral("a")]))
        self.check_astgen(input, expect)

    def test_identifier(self):
        input = EXPR_TEST_TMPL.format("x")
        expect = expr_expect_tmpl(Id("x"))
        self.check_astgen(input, expect)

    def test_add_expr(self):
        input = EXPR_TEST_TMPL.format("3 + 4")
        expect = expr_expect_tmpl(BinaryOp("+", IntLiteral(3), IntLiteral(4)))
        self.check_astgen(input, expect)

    def test_add_expr2(self):
        input = EXPR_TEST_TMPL.format("0 - (3 + 4)")
        expect = expr_expect_tmpl(
            BinaryOp("-", IntLiteral(0), BinaryOp("+", IntLiteral(3), IntLiteral(4)))
        )
        self.check_astgen(input, expect)

    def test_mul_expr(self):
        input = EXPR_TEST_TMPL.format("1 * 2")
        expect = expr_expect_tmpl(BinaryOp("*", IntLiteral(1), IntLiteral(2)))
        self.check_astgen(input, expect)

    def test_mul_expr2(self):
        input = EXPR_TEST_TMPL.format("0 \\ (1 * 2)")
        expect = expr_expect_tmpl(
            BinaryOp("\\", IntLiteral(0), BinaryOp("*", IntLiteral(1), IntLiteral(2)))
        )
        self.check_astgen(input, expect)

    def test_logical_expr(self):
        input = EXPR_TEST_TMPL.format("True && False")
        expect = expr_expect_tmpl(
            BinaryOp("&&", BooleanLiteral(True), BooleanLiteral(False))
        )
        self.check_astgen(input, expect)

    def test_logical_expr2(self):
        input = EXPR_TEST_TMPL.format("0 || (True && False)")
        expect = expr_expect_tmpl(
            BinaryOp(
                "||",
                IntLiteral(0),
                BinaryOp("&&", BooleanLiteral(True), BooleanLiteral(False)),
            )
        )
        self.check_astgen(input, expect)

    def test_relational_expr(self):
        input = EXPR_TEST_TMPL.format("1 < 2")
        expect = expr_expect_tmpl(BinaryOp("<", IntLiteral(1), IntLiteral(2)))
        self.check_astgen(input, expect)

    def test_relational_expr2(self):
        input = EXPR_TEST_TMPL.format("(1 < 2) > 3")
        expect = expr_expect_tmpl(
            BinaryOp(">", BinaryOp("<", IntLiteral(1), IntLiteral(2)), IntLiteral(3))
        )
        self.check_astgen(input, expect)

    def test_parentheses_expr(self):
        input = EXPR_TEST_TMPL.format("(2+3)")
        expect = expr_expect_tmpl(BinaryOp("+", IntLiteral(2), IntLiteral(3)))
        self.check_astgen(input, expect)

    def test_parentheses_expr_with_index(self):
        input = EXPR_TEST_TMPL.format("(2+3)[0]")
        expect = expr_expect_tmpl(
            ArrayCell(BinaryOp("+", IntLiteral(2), IntLiteral(3)), [IntLiteral(0)])
        )
        self.check_astgen(input, expect)

    def test_unary_expr(self):
        input = EXPR_TEST_TMPL.format("-1")
        expect = expr_expect_tmpl(UnaryOp("-", IntLiteral(1)))
        self.check_astgen(input, expect)

    def test_unary_exprs(self):
        input = EXPR_TEST_TMPL.format("--1")
        expect = expr_expect_tmpl(UnaryOp("-", UnaryOp("-", IntLiteral(1))))
        self.check_astgen(input, expect)

    def test_unary_expr2(self):
        input = EXPR_TEST_TMPL.format("!(-1)")
        expect = expr_expect_tmpl(UnaryOp("!", UnaryOp("-", IntLiteral(1))))
        self.check_astgen(input, expect)

    def test_assoc_of_mul(self):
        input = EXPR_TEST_TMPL.format("1 * 2 \\ 3")
        expect = expr_expect_tmpl(
            BinaryOp("\\", BinaryOp("*", IntLiteral(1), IntLiteral(2)), IntLiteral(3))
        )
        self.check_astgen(input, expect)

    def test_assoc_of_add(self):
        """Test associativity of add operation"""
        input = EXPR_TEST_TMPL.format("1 - 2 + 3")
        expect = expr_expect_tmpl(
            BinaryOp("+", BinaryOp("-", IntLiteral(1), IntLiteral(2)), IntLiteral(3))
        )
        self.check_astgen(input, expect)

    def test_assoc_of_logical(self):
        """Test associativity of logical operation"""
        input = EXPR_TEST_TMPL.format("1 && 2 || 3")
        expect = expr_expect_tmpl(
            BinaryOp("||", BinaryOp("&&", IntLiteral(1), IntLiteral(2)), IntLiteral(3))
        )
        self.check_astgen(input, expect)

    def test_precedence_with_mul_and_prefix(self):
        input = EXPR_TEST_TMPL.format("-2 * 3")
        expect = expr_expect_tmpl(
            BinaryOp("*", UnaryOp("-", IntLiteral(2)), IntLiteral(3))
        )
        self.check_astgen(input, expect)

    def test_predcedence_with_mul_and_add(self):
        input = EXPR_TEST_TMPL.format("1 + 2 * 3")
        expect = expr_expect_tmpl(
            BinaryOp("+", IntLiteral(1), BinaryOp("*", IntLiteral(2), IntLiteral(3)))
        )
        self.check_astgen(input, expect)

    def test_predcedence_with_logical_and_add(self):
        input = EXPR_TEST_TMPL.format("1 && 2 - 3")
        expect = expr_expect_tmpl(
            BinaryOp("&&", IntLiteral(1), BinaryOp("-", IntLiteral(2), IntLiteral(3)))
        )
        self.check_astgen(input, expect)

    def test_precedence_with_rel_and_logical(self):
        input = EXPR_TEST_TMPL.format("1 > 2 && 3")
        expect = expr_expect_tmpl(
            BinaryOp(">", IntLiteral(1), BinaryOp("&&", IntLiteral(2), IntLiteral(3)))
        )
        self.check_astgen(input, expect)

    def test_precedence_with_prefix_and_index(self):
        input = EXPR_TEST_TMPL.format("-x[0]")
        expect = expr_expect_tmpl(UnaryOp("-", ArrayCell(Id("x"), [IntLiteral(0)])))
        self.check_astgen(input, expect)

    def test_precedence_with_func_call_and_prefix(self):
        input = EXPR_TEST_TMPL.format("-f()")
        expect = expr_expect_tmpl(UnaryOp("-", CallExpr(Id("f"), [])))
        self.check_astgen(input, expect)

    def test_elem_expr_with_literal(self):
        input = EXPR_TEST_TMPL.format("x[0]")
        expect = expr_expect_tmpl(ArrayCell(Id("x"), [IntLiteral(0)]))
        self.check_astgen(input, expect)

    def test_elem_expr_with_literals(self):
        input = EXPR_TEST_TMPL.format("x[0][1]")
        expect = expr_expect_tmpl(ArrayCell(Id("x"), [IntLiteral(0), IntLiteral(1)]))
        self.check_astgen(input, expect)

    def test_elem_expr_with_expr(self):
        input = EXPR_TEST_TMPL.format("x[i]")
        expect = expr_expect_tmpl(ArrayCell(Id("x"), [Id("i")]))
        self.check_astgen(input, expect)

    def test_elem_expr_with_expr2(self):
        input = EXPR_TEST_TMPL.format("x[i][j]")
        expect = expr_expect_tmpl(ArrayCell(Id("x"), [Id("i"), Id("j")]))
        self.check_astgen(input, expect)

    def test_call_expr(self):
        input = EXPR_TEST_TMPL.format("f()")
        expect = expr_expect_tmpl(CallExpr(Id("f"), []))
        self.check_astgen(input, expect)

    def test_unary_func(self):
        """Test function call with literal as argument."""
        input = EXPR_TEST_TMPL.format("f(0)")
        expect = expr_expect_tmpl(CallExpr(Id("f"), [IntLiteral(0)]))
        self.check_astgen(input, expect)

    def test_binary_func(self):
        input = EXPR_TEST_TMPL.format("f(0,1)")
        expect = expr_expect_tmpl(CallExpr(Id("f"), [IntLiteral(0), IntLiteral(1)]))
        self.check_astgen(input, expect)

    def test_func_call_expr(self):
        """Test function call with expression as argument."""
        input = EXPR_TEST_TMPL.format("f(1+2)")
        expect = expr_expect_tmpl(
            CallExpr(Id("f"), [BinaryOp("+", IntLiteral(1), IntLiteral(2))])
        )
        self.check_astgen(input, expect)

    def test_elem_expr_with_func(self):
        input = EXPR_TEST_TMPL.format("f()[0]")
        expect = expr_expect_tmpl(ArrayCell(CallExpr(Id("f"), []), [IntLiteral(0)]))
        self.check_astgen(input, expect)

    def test_float_pred(self):
        input = EXPR_TEST_TMPL.format("2 +. 3 *. 3")
        expect = expr_expect_tmpl(
            BinaryOp("+.", IntLiteral(2), BinaryOp("*.", IntLiteral(3), IntLiteral(3)))
        )
        self.check_astgen(input, expect)


class TestAssignment(TestAST):
    def test_assign_scalar(self):
        input = STMT_INPUT_TMPL.format("x = 0;")
        expect = stmt_expect_tmpl(Assign(Id("x"), IntLiteral(0)))
        self.check_astgen(input, expect)

    def test_assign_array(self):
        input = STMT_INPUT_TMPL.format("a[0] = 0;")
        expect = stmt_expect_tmpl(
            Assign(ArrayCell(Id("a"), [IntLiteral(0)]), IntLiteral(0))
        )
        self.check_astgen(input, expect)

    def test_assign_array2(self):
        input = STMT_INPUT_TMPL.format("f()[0] = 0;")
        expect = stmt_expect_tmpl(
            Assign(ArrayCell(CallExpr(Id("f"), []), [IntLiteral(0)]), IntLiteral(0))
        )
        self.check_astgen(input, expect)

    def test_assign_mult_dims_array(self):
        input = STMT_INPUT_TMPL.format("a[0][0] = 0;")
        expect = stmt_expect_tmpl(
            Assign(ArrayCell(Id("a"), [IntLiteral(0), IntLiteral(0)]), IntLiteral(0))
        )
        self.check_astgen(input, expect)

    def test_assign_scalar_to_expr(self):
        input = STMT_INPUT_TMPL.format("x = 1 + 1;")
        expect = stmt_expect_tmpl(
            Assign(Id("x"), BinaryOp("+", IntLiteral(1), IntLiteral(1)))
        )
        self.check_astgen(input, expect)


class TestForStatement(TestAST):
    def test_empty_for_stmt(self):
        input = STMT_INPUT_TMPL.format("For (i = 0, 1, 1) Do EndFor.")
        expect = stmt_expect_tmpl(
            For(Id("i"), IntLiteral(0), IntLiteral(1), IntLiteral(1), ([], []))
        )
        self.check_astgen(input, expect)

    def test_simple_for_stmt(self):
        input = STMT_INPUT_TMPL.format("For (i=0, 1, 1) Do Return; EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                IntLiteral(0),
                IntLiteral(1),
                IntLiteral(1),
                ([], [Return(None)]),
            )
        )
        self.check_astgen(input, expect)

    def test_for_stmt_with_init_expr(self):
        """Test for statement with complex initial expression"""
        input = STMT_INPUT_TMPL.format("For (i=0+1, 1, 1) Do EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                BinaryOp("+", IntLiteral(0), IntLiteral(1)),
                IntLiteral(1),
                IntLiteral(1),
                ([], []),
            )
        )
        self.check_astgen(input, expect)

    def test_for_stmt_with_cond_expr(self):
        """Test for statement with complex condition expression"""
        input = STMT_INPUT_TMPL.format("For (i=0, i<1, 1) Do EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                IntLiteral(0),
                BinaryOp("<", Id("i"), IntLiteral(1)),
                IntLiteral(1),
                ([], []),
            )
        )
        self.check_astgen(input, expect)

    def test_for_stmt_with_update_expr(self):
        """Test for statement with complex update expression"""
        input = STMT_INPUT_TMPL.format("For (i=0, 1, 1+1) Do EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                IntLiteral(0),
                IntLiteral(1),
                BinaryOp("+", IntLiteral(1), IntLiteral(1)),
                ([], []),
            )
        )
        self.check_astgen(input, expect)

    def test_for_stmt_with_var_decl(self):
        input = STMT_INPUT_TMPL.format("For (i=0, 1, 1) Do Var: x; EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                IntLiteral(0),
                IntLiteral(1),
                IntLiteral(1),
                ([VarDecl(Id("x"), [], None)], []),
            )
        )
        self.check_astgen(input, expect)

    def test_for_stmt_with_complete_body(self):
        """Test for statement with body contain both variable declaration and other stmt"""
        input = STMT_INPUT_TMPL.format("For (i=0, 1, 1) Do Var: x; Return; EndFor.")
        expect = stmt_expect_tmpl(
            For(
                Id("i"),
                IntLiteral(0),
                IntLiteral(1),
                IntLiteral(1),
                ([VarDecl(Id("x"), [], None)], [Return(None)]),
            )
        )
        self.check_astgen(input, expect)


class TestIfStatement(TestAST):
    def test_empty_if_stmt(self):
        input = STMT_INPUT_TMPL.format("If True Then EndIf.")
        expect = stmt_expect_tmpl(If([(BooleanLiteral(True), [], [])], ([], [])))
        self.check_astgen(input, expect)

    def test_empty_if_stmt2(self):
        """Test empty if statement with complex condition expression"""
        input = STMT_INPUT_TMPL.format("If x > 2 Then EndIf.")
        expect = stmt_expect_tmpl(
            If([(BinaryOp(">", Id("x"), IntLiteral(2)), [], [])], ([], []))
        )
        self.check_astgen(input, expect)

    def test_simple_if_stmt(self):
        input = STMT_INPUT_TMPL.format("If True Then Return; EndIf.")
        expect = stmt_expect_tmpl(
            If([(BooleanLiteral(True), [], [Return(None)])], ([], []))
        )
        self.check_astgen(input, expect)

    def test_if_stmt_with_var_decl(self):
        input = STMT_INPUT_TMPL.format("If x Then Var: x; EndIf.")
        expect = stmt_expect_tmpl(
            If([(Id("x"), [VarDecl(Id("x"), [], None)], [])], ([], []))
        )
        self.check_astgen(input, expect)

    def test_if_stmt_with_else(self):
        input = STMT_INPUT_TMPL.format("If True Then Return; Else Return; EndIf.")
        expect = stmt_expect_tmpl(
            If([(BooleanLiteral(True), [], [Return(None)])], ([], [Return(None)]))
        )
        self.check_astgen(input, expect)

    def test_else_if_stmt(self):
        input = STMT_INPUT_TMPL.format("If 1 Then ElseIf 1 Then EndIf.")
        expect = stmt_expect_tmpl(
            If([(IntLiteral(1), [], []), (IntLiteral(1), [], [])], ([], []))
        )
        self.check_astgen(input, expect)

    def test_full_if_stmt(self):
        input = STMT_INPUT_TMPL.format("If 1 Then ElseIf 1 Then Else EndIf.")
        expect = stmt_expect_tmpl(
            If([(IntLiteral(1), [], []), (IntLiteral(1), [], [])], ([], []))
        )
        self.check_astgen(input, expect)

    def test_nested_if_stmt(self):
        input = STMT_INPUT_TMPL.format("If 1 Then If 1 Then EndIf. EndIf.")
        expect = stmt_expect_tmpl(
            If(
                [(IntLiteral(1), [], [If([(IntLiteral(1), [], [])], ([], []))])],
                ([], []),
            )
        )
        self.check_astgen(input, expect)


class TestWhileStatement(TestAST):
    def test_empty_while_stmt(self):
        input = STMT_INPUT_TMPL.format("While 1 Do EndWhile.")
        expect = stmt_expect_tmpl(While(IntLiteral(1), ([], [])))
        self.check_astgen(input, expect)

    def test_simple_while_stmt(self):
        input = STMT_INPUT_TMPL.format("While 1 Do Return; EndWhile.")
        expect = stmt_expect_tmpl(While(IntLiteral(1), ([], [Return(None)])))
        self.check_astgen(input, expect)

    def test_while_stmt_with_cond(self):
        """Test while statement with complex condition expression"""
        input = STMT_INPUT_TMPL.format("While i > a Do EndWhile.")
        expect = stmt_expect_tmpl(While(BinaryOp(">", Id("i"), Id("a")), ([], [])))
        self.check_astgen(input, expect)

    def test_nested_while_stmt(self):
        input = STMT_INPUT_TMPL.format("While 1 Do While 1 Do EndWhile. EndWhile.")
        expect = stmt_expect_tmpl(
            While(IntLiteral(1), ([], [While(IntLiteral(1), ([], []))]))
        )
        self.check_astgen(input, expect)


class TestDoWhileStatement(TestAST):
    def test_empty_do_while_stmt(self):
        input = STMT_INPUT_TMPL.format("Do While 1 EndDo.")
        expect = stmt_expect_tmpl(Dowhile(([], []), IntLiteral(1)))
        self.check_astgen(input, expect)

    def test_simple_do_while_stmt(self):
        input = STMT_INPUT_TMPL.format("Do Return; While 1 EndDo.")
        expect = stmt_expect_tmpl(Dowhile(([], [Return(None)]), IntLiteral(1)))
        self.check_astgen(input, expect)

    def test_do_while_stmt_with_cond(self):
        """Test do while statement with complex condition expression"""
        input = STMT_INPUT_TMPL.format("Do While i > a EndDo.")
        expect = stmt_expect_tmpl(Dowhile(([], []), BinaryOp(">", Id("i"), Id("a"))))
        self.check_astgen(input, expect)

    def test_do_while_stmt_with_var_decl(self):
        input = STMT_INPUT_TMPL.format("Do Var: x; While x EndDo.")
        expect = stmt_expect_tmpl(Dowhile(([VarDecl(Id("x"), [], None)], []), Id("x")))
        self.check_astgen(input, expect)


class TestMisc(TestAST):
    def test_break_stmt(self):
        input = STMT_INPUT_TMPL.format("Break;")
        expect = stmt_expect_tmpl(Break())
        self.check_astgen(input, expect)

    def test_continue_stmt(self):
        input = STMT_INPUT_TMPL.format("Continue;")
        expect = stmt_expect_tmpl(Continue())
        self.check_astgen(input, expect)

    def test_call_stmt(self):
        input = STMT_INPUT_TMPL.format("f(0, 1 + 1);")
        expect = stmt_expect_tmpl(
            CallStmt(
                Id("f"), [IntLiteral(0), BinaryOp("+", IntLiteral(1), IntLiteral(1))]
            )
        )
        self.check_astgen(input, expect)

    def test_var_decl_and_func_decl(self):
        input = """
Var: x;
Function: main
    Body:
    EndBody.
"""
        expect = Program(
            [VarDecl(Id("x"), [], None), FuncDecl(Id("main"), [], ([], []))]
        )
        self.check_astgen(input, expect)
