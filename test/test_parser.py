import unittest

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ConsoleErrorListener
from bkit.parser import BKITLexer, BKITParser


class SyntaxException(Exception):
    pass


class NewErrorListener(ConsoleErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # message = f"Error on line {line} col {column}: " + offendingSymbol.text
        message = f"Error on line {line} col {column}: {offendingSymbol.text}"
        raise SyntaxException(message)


NewErrorListener.INSTANCE = NewErrorListener()


class TestParser(unittest.TestCase):
    def check_parser(self, input, expect):
        lexer = BKITLexer(InputStream(input))
        tokens = CommonTokenStream(lexer)
        parser = BKITParser(tokens)
        # parser.setTrace(True)
        parser.removeErrorListeners()
        parser.addErrorListener(NewErrorListener.INSTANCE)
        try:
            parser.program()
        except SyntaxException as f:
            result = str(f)
        # except Exception as e:
        #     result = str(e)
        else:
            result = "successful"
        self.assertEqual(result, expect, f"Input:\n{input}")


##
class TestVariableDeclaration(TestParser):
    def test_simple_decl(self):
        input = "Var: x;"
        expect = "successful"
        self.check_parser(input, expect)

    def test_decl_with_init_val(self):
        """Test declare variable with initial value."""
        input = "Var: x = 0;"
        # input = "Var: array[1][2] = {}"
        expect = "successful"
        self.check_parser(input, expect)

    def test_decl_without_var(self):
        input = "Var: ;"
        expect = "Error on line 1 col 5: ;"
        self.check_parser(input, expect)

    def test_decl_missing_semi(self):
        """Test a variable declaration without semicolon."""
        input = "Var: x"
        expect = "Error on line 1 col 6: <EOF>"
        self.check_parser(input, expect)

    def test_arr_var(self):
        input = "Var: x[5];"
        expect = "successful"
        self.check_parser(input, expect)

    def test_arr_var2(self):
        """Test declare array variable with initial value."""
        input = "Var: x[1] = {0};"
        expect = "successful"
        self.check_parser(input, expect)

    def test_invalid_arr_var(self):
        """Test declare array variable with non-integer dimension."""
        input = "Var: x[2.3];"
        expect = "Error on line 1 col 7: 2.3"
        self.check_parser(input, expect)

    def test_arr_var_with_invalid_dim(self):
        """Test declare array variable with non-literal dimension."""
        input = "Var: x[a];"
        expect = "Error on line 1 col 7: a"
        self.check_parser(input, expect)

    def test_wrong_rvalue(self):
        """Test variable declaration with non-literal right hand side."""
        input = "Var: x = 1 + 2;"
        expect = "Error on line 1 col 11: +"
        self.check_parser(input, expect)

    def test_wrong_rvalue2(self):
        """Test variable declarations with non-literal right hand side."""
        input = "Var: x = 1, y = x;"
        expect = "Error on line 1 col 16: x"
        self.check_parser(input, expect)

    # We will detect dimension mismatch in semantic analysis phase
    def test_assign_mismatch_dim(self):
        """Test assign array literal to scalar variable."""
        input = "Var: x = {1};"
        # expect = "Error on line 1 col 9: {"
        expect = "successful"
        self.check_parser(input, expect)

    def test_assign_mismatch_dim2(self):
        """Test assign literal to array variable."""
        input = "Var: x[1] = 1;"
        # expect = "Error on line 1 col 12: 1"
        expect = "successful"
        self.check_parser(input, expect)

    def test_declare_local_var(self):
        """Test declare a variable inside a statement list."""
        input = """
Function: main
    Body:
        Var: x;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)


class TestFunction(TestParser):
    def test_empty_func(self):
        """Test function with no parameter and empty body."""
        input = """
Function: test
    Body:
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_empty_func2(self):
        """Test function with a parameter and empty body."""
        input = """
Function: test
    Parameter: x
    Body:
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_simple_func(self):
        input = """
Function: main
    Body:
        Return;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_nested_function(self):
        input = """
Function: main
    Body:
        Function: nested
            Body:
            EndBody.
    EndBody.
"""
        expect = "Error on line 4 col 8: Function"
        self.check_parser(input, expect)

    def test_func_without_name(self):
        input = """
Function:
    Body:
    EndBody.
"""
        expect = "Error on line 3 col 4: Body"
        self.check_parser(input, expect)

    def test_func_with_empty_param(self):
        input = """
Function: main
    Parameter:
    Body:
    EndBody.
"""
        expect = "Error on line 4 col 4: Body"
        self.check_parser(input, expect)

    def test_func_without_end(self):
        input = """
Function: main
    Body:
        x = 1;
"""
        expect = "Error on line 5 col 0: <EOF>"
        self.check_parser(input, expect)


class TestExpression(TestParser):
    EXPR_TEST_TEMPLATE = """
Function: test
    Body:
        Return {};
    EndBody.
"""

    def test_literal(self):
        input = self.EXPR_TEST_TEMPLATE.format("1")
        expect = "successful"
        self.check_parser(input, expect)

    def test_func_call(self):
        input = self.EXPR_TEST_TEMPLATE.format("sin(0)")
        expect = "successful"
        self.check_parser(input, expect)

    def test_invalid_func_call(self):
        input = self.EXPR_TEST_TEMPLATE.format("5(0)")
        expect = "Error on line 4 col 16: ("
        self.check_parser(input, expect)

    def test_binary_expr(self):
        input = self.EXPR_TEST_TEMPLATE.format("2 + 3")
        expect = "successful"
        self.check_parser(input, expect)

    def test_sign_expr(self):
        """Test sign negation operator."""
        input = self.EXPR_TEST_TEMPLATE.format("-2")
        expect = "successful"
        self.check_parser(input, expect)

    def test_float_sign_expr(self):
        """Test float sign negation operator."""
        input = self.EXPR_TEST_TEMPLATE.format("-. 2.0")
        expect = "successful"
        self.check_parser(input, expect)

    def test_many_prefix_expr(self):
        input = self.EXPR_TEST_TEMPLATE.format("--2")
        expect = "successful"
        self.check_parser(input, expect)

    def test_prefix_expr2(self):
        """Test prefix operator put at postfix location."""
        input = self.EXPR_TEST_TEMPLATE.format("True !")
        expect = "Error on line 4 col 20: !"
        self.check_parser(input, expect)

    def test_parentheses_expr(self):
        input = self.EXPR_TEST_TEMPLATE.format("(2+3)")
        expect = "successful"
        self.check_parser(input, expect)

    def test_unclosed_parentheses(self):
        input = self.EXPR_TEST_TEMPLATE.format("(2+3")
        expect = "Error on line 4 col 19: ;"
        self.check_parser(input, expect)

    def test_bool_op(self):
        input = self.EXPR_TEST_TEMPLATE.format("! True && False || True")
        expect = "successful"
        self.check_parser(input, expect)

    def test_non_assoc_op(self):
        input = self.EXPR_TEST_TEMPLATE.format("2 < 3 < 4")
        expect = "Error on line 4 col 21: <"
        self.check_parser(input, expect)

    def test_add_op(self):
        """Test integer additive operators."""
        input = self.EXPR_TEST_TEMPLATE.format("2 + 1 - 1")
        expect = "successful"
        self.check_parser(input, expect)

    def test_float_add_op(self):
        """Test float additive operators."""
        input = self.EXPR_TEST_TEMPLATE.format("2.5 +. 1.0 -. 1.5")
        expect = "successful"
        self.check_parser(input, expect)

    def test_mul_op(self):
        """Test integer mulplicative operators."""
        input = self.EXPR_TEST_TEMPLATE.format("2 * 3 \\ 2 % 1")
        expect = "successful"
        self.check_parser(input, expect)

    def test_float_mul_op(self):
        """Test float mulplicative operators."""
        input = self.EXPR_TEST_TEMPLATE.format("2.0 *. 3.0 \\. 2.0")
        expect = "successful"
        self.check_parser(input, expect)

    def test_rel_op(self):
        input = """
Function: main
    Body:
        x = 1 == 2;
        x = 2 != 3;
        x = 2 < 3;
        x = 3 > 10;
        x = 1 <= 2;
        x = 3 >= 9;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_float_rel_op(self):
        input = """
Function: main
    Body:
        x = 1.0 =/= 2.5;
        x = 2.5 <. 3.0;
        x = 3.0 >. 1.0;
        x = 1.5 <=. 2.0;
        x = 3.5 >=. 9.6;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_elem_expr(self):
        """Test element expression with literal index."""
        input = self.EXPR_TEST_TEMPLATE.format("arr[1]")
        expect = "successful"
        self.check_parser(input, expect)

    def test_elem_expr2(self):
        """Test element expression with expression index."""
        input = self.EXPR_TEST_TEMPLATE.format("arr[i - 1]")
        expect = "successful"
        self.check_parser(input, expect)

    def test_elem_expr3(self):
        """Test element expression with invalid index."""
        input = self.EXPR_TEST_TEMPLATE.format("arr[i -]")
        expect = "Error on line 4 col 22: ]"
        self.check_parser(input, expect)

    def test_elem_expr4(self):
        """Test element expression with multiple indexes."""
        input = self.EXPR_TEST_TEMPLATE.format("arr[i][j]")
        expect = "successful"
        self.check_parser(input, expect)

    def test_elem_expr5(self):
        input = self.EXPR_TEST_TEMPLATE.format("5[i]")
        expect = "Error on line 4 col 16: ["
        self.check_parser(input, expect)

    def test_elem_expr6(self):
        input = self.EXPR_TEST_TEMPLATE.format("f()[i]")
        expect = "successful"
        self.check_parser(input, expect)

    def test_expr_array_literal(self):
        input = self.EXPR_TEST_TEMPLATE.format("{0}")
        # expect = "Error on line 4 col 15: {"
        expect = "successful"
        self.check_parser(input, expect)


class TestAssignment(TestParser):
    def test_normal_assign(self):
        input = """
Function: main
    Body:
        x = 1;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_chain_assign(self):
        """Test chain assignment."""
        input = """
Function: main
    Body:
        a = b = 1;
    EndBody.
"""
        expect = "Error on line 4 col 14: ="
        self.check_parser(input, expect)

    def test_assign_empty_expr(self):
        input = """
Function: main
    Body:
        x = ;
    EndBody.
"""
        expect = "Error on line 4 col 12: ;"
        self.check_parser(input, expect)

    @unittest.skip
    def test_assign_with_literal_lvalue(self):
        """Test assignment with literal on left hand side."""
        input = """
Function: main
    Body:
        5 = 9;
    EndBody.
"""
        expect = "Error on line 4 col 8: 5"
        self.check_parser(input, expect)

    def test_assign_stmt_rvalue(self):
        """Test assignment with statement on right hand side."""
        input = """
Function: main
    Body:
        a = If a == 1 Then EndIf.;
    EndBody.
"""
        expect = "Error on line 4 col 12: If"
        self.check_parser(input, expect)

    def test_assign_missing_semi(self):
        """Test assignment statement without semicolon."""
        input = """
Function: main
    Body:
        x = 2
    EndBody.
"""
        expect = "Error on line 5 col 4: EndBody"
        self.check_parser(input, expect)

    def test_assign_array_literal(self):
        """Test assignment with rvalue is array literal."""
        input = """
Function: main
    Body:
        x = {1};
    EndBody.
"""
        # expect = "Error on line 4 col 12: {"
        expect = "successful"
        self.check_parser(input, expect)

    def test_assign_to_arr_var(self):
        input = """
Function: main
    Body:
        x[0] = 1;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    # def test_assign_ouside_func(self):
    #     input = "x = 1;"
    #     # expect = "Error on line 1 col 0: x"
    #     expect = "successful"
    #     self.check_parser(input, expect)


class TestIfStatement(TestParser):
    def test_simple_if_stmt(self):
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_if_stmt_with_else(self):
        """Test if statement with else clause."""
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        Else
            a = x - 1;
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_if_stmt_with_elif(self):
        """Test if statement with else if clause."""
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        ElseIf a < 0 Then
            a = x - 1;
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_if_stmt_with_multiple_elif(self):
        """Test if statement with multiple else if clauses."""
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        ElseIf a < 5 Then
            a = x - 1;
        ElseIf a < 0 Then
            a = x * 1;
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_if_stmt_with_multiple_else(self):
        """Test if statement with multiple else clauses."""
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        Else
            a = x - 1;
        Else
            a = x * 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 8 col 8: Else"
        self.check_parser(input, expect)

    def test_if_stmt_wrong_order(self):
        """Test if statement with else clause appear before else if clause."""
        input = """
Function: main
    Body:
        If a < 8 Then
            a = x + 1;
        Else
            a = x - 1;
        ElseIf a > 10 Then
            a = x * 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 8 col 8: ElseIf"
        self.check_parser(input, expect)

    def test_nested_if_stmts(self):
        input = """
Function: main
    Body:
        If a < 8 Then
            If a < 5 Then
                x = 1;
            EndIf.
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_empty_if_stmt(self):
        input = """
Function: main
    Body:
        If a == 0 Then
        EndIf.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_unterminated_if_stmt(self):
        input = """
Function: main
    Body:
        If a == 0 Then
            a = 9;
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    def test_wrong_elif_stmt(self):
        input = """
Function: main
    Body:
        If a == 0 Then
            Return 1;
        ElseIf
            Return 2;
        EndIf.
    EndBody.
"""
        expect = "Error on line 7 col 12: Return"
        self.check_parser(input, expect)

    def test_if_stmt_without_cond(self):
        """Test if statement without condition expression."""
        input = """
Function: main
    Body:
        If Then
            a = x + 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 4 col 11: Then"
        self.check_parser(input, expect)

    def test_if_stmt_with_invalid_cond(self):
        """Test if statement with invalid condition expression."""
        input = """
Function: main
    Body:
        If a > Then
            a = x + 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 4 col 15: Then"
        self.check_parser(input, expect)

    def test_if_stmt_with_invalid_cond2(self):
        """Test if statement with invalid condition expression."""
        input = """
Function: main
    Body:
        If a = 0 Then
            a = x + 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 4 col 13: ="
        self.check_parser(input, expect)

    def test_if_stmt_without_end(self):
        input = """
Function: main
    Body:
        If True Then
            x = 1;
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    def test_if_stmt_without_dot(self):
        input = """
Function: main
    Body:
        If True Then
            x = 1;
        EndIf
    EndBody.
"""
        expect = "Error on line 7 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_if_stmt_outside_func(self):
    #     input = "If True Then x = 1; EndIf."
    #     expect = "Error on line 1 col 0: If"
    #     self.check_parser(input, expect)

    def test_if_stmt_missing_then(self):
        input = """
Function: main
    Body:
        If True
            x = 1;
        EndIf.
    EndBody.
"""
        expect = "Error on line 5 col 12: x"
        self.check_parser(input, expect)


class TestForStatement(TestParser):
    def test_normal_for_stmt(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, 1) Do
            x = 1;
        EndFor.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_empty_for_stmt(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, 1) Do
        EndFor.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_for_stmt_with_empty_cond(self):
        input = """
Function: main
    Body:
        For () Do
        EndFor.
    EndBody.
"""
        expect = "Error on line 4 col 13: )"
        self.check_parser(input, expect)

    def test_for_stmt_with_arr_var(self):
        input = """
Function: main
    Body:
        For (a[1] = {0}, a[0] < 10, 1) Do
        EndFor.
    EndBody.
"""
        expect = "Error on line 4 col 14: ["
        self.check_parser(input, expect)

    def test_for_stmt_without_end(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, 1) Do
            x = 1;
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    def test_for_stmt_without_dot(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, 1) Do
            x = 1;
        EndFor
    EndBody.
"""
        expect = "Error on line 7 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_for_stmt_outside_func(self):
    #     input = "For (i = 0; i < 1, 1) Do x = 1; EndFor."
    #     expect = "Error on line 1 col 0: For"
    #     self.check_parser(input, expect)

    def test_for_stmt_use_semi(self):
        input = """
Function: main
    Body:
        For (i = 0; i < 10; 1) Do
            x = 1;
        EndFor.
    EndBody.
"""
        expect = "Error on line 4 col 18: ;"
        self.check_parser(input, expect)

    def test_for_stmt_missing_do(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, 1)
            x = 1;
        EndFor.
    EndBody.
"""
        expect = "Error on line 5 col 12: x"
        self.check_parser(input, expect)

    def test_for_stmt_with_invalid_update(self):
        input = """
Function: main
    Body:
        For (i = 0, i < 10, i = i + 1) Do
        EndDo.
    EndBody.
"""
        expect = "Error on line 4 col 30: ="
        self.check_parser(input, expect)


class TestWhileStatement(TestParser):
    def test_simple_while_stmt(self):
        input = """
Function: test
    Body:
        While a < 8 Do
            a = x + 1;
        EndWhile.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_empty_while_stmt(self):
        input = """
Function: test
    Body:
        While a < 8 Do
        EndWhile.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_while_stmt_without_expr(self):
        input = """
Function: test
    Body:
        While Do
        EndWhile.
    EndBody.
"""
        expect = "Error on line 4 col 8: While"
        self.check_parser(input, expect)

    def test_while_stmt_with_invalid_cond(self):
        input = """
Function: main
    Body:
        While x > Do
        EndWhile.
    EndBody.
"""
        expect = "Error on line 4 col 8: While"
        self.check_parser(input, expect)

    def test_while_stmt_without_end(self):
        input = """
Function: main
    Body:
        While True Do
            a = x + 1;
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    def test_while_stmt_without_dot(self):
        input = """
Function: main
    Body:
        While True Do
            a = x + 1;
        EndWhile
    EndBody.
"""
        expect = "Error on line 7 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_while_stmt_outside_func(self):
    #     input = "While True Do x = 1; EndDo."
    #     expect = "Error on line 1 col 0: While"
    #     self.check_parser(input, expect)

    def test_while_stmt_missing_do(self):
        input = """
Function: main
    Body:
        While True
            a = x + 1;
        EndWhile.
    EndBody.
"""
        expect = "Error on line 4 col 8: While"
        self.check_parser(input, expect)


class TestDoWhileStatement(TestParser):
    def test_simple_do_while_stmt(self):
        input = """
Function: main
    Body:
        Do a = a + 1;
        While a < 8 EndDo.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_empty_do_while_stmt(self):
        input = """
Function: main
    Body:
        Do While True EndDo.
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_do_while_stmt_wrong_end(self):
        input = """
Function: main
    Body:
        Do a = a + 1;
        While a < 8 EndWhile.
    EndBody.
"""
        expect = "Error on line 5 col 20: EndWhile"
        self.check_parser(input, expect)

    def test_do_while_stmt_wrong_order(self):
        input = """
Function: main
    Body:
        Do a < 8
        While a = a + 1; EndWhile.
    EndBody.
"""
        expect = "Error on line 4 col 13: <"
        self.check_parser(input, expect)

    def test_do_while_stmt_wrong_cond(self):
        input = """
Function: main
    Body:
        Do a = a + 1;
        While a < EndDo.
    EndBody.
"""
        expect = "Error on line 5 col 18: EndDo"
        self.check_parser(input, expect)

    def test_do_while_stmt_without_end(self):
        input = """
Function: main
    Body:
        Do a = a + 1;
        While a < 8
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    def test_do_while_stmt_without_dot(self):
        input = """
Function: main
    Body:
        Do a = a + 1;
        While a < 8 EndDo
    EndBody.
"""
        expect = "Error on line 6 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_do_while_stmt_outside_func(self):
    #     input = "Do x = 1; While True EndDo."
    #     expect = "Error on line 1 col 0: Do"
    #     self.check_parser(input, expect)

    def test_do_while_stmt_missing_while(self):
        """Test do/while statement missing while keyword."""
        input = """
Function: main
    Body:
        Do a = a + 1;
        True EndDo.
    EndBody.
"""
        expect = "Error on line 5 col 8: True"
        self.check_parser(input, expect)


class TestStatement(TestParser):
    def test_break_stmt(self):
        input = """
Function: main
    Body:
        Break;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    # def test_break_stmt_outside_func(self):
    #     input = "Break;"
    #     expect = "Error on line 1 col 0: Break"
    #     self.check_parser(input, expect)

    def test_break_stmt_missing_semi(self):
        input = """
Function: main
    Body:
        Break
    EndBody.
"""
        expect = "Error on line 5 col 4: EndBody"
        self.check_parser(input, expect)

    def test_return_stmt(self):
        input = """
Function: main
    Body:
        Return;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_return_stmt_with_expr(self):
        input = """
Function: main
    Body:
        Return 1 + 1;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_return_stmt_missing_semi(self):
        input = """
Function: main
    Body:
        Return
    EndBody.
"""
        expect = "Error on line 5 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_return_stmt_outside_func(self):
    #     input = "Return;"
    #     expect = "Error on line 1 col 0: Return"
    #     self.check_parser(input, expect)

    def test_cont_stmt(self):
        input = """
Function: main
    Body:
        Continue;
    EndBody.
"""
        expect = "successful"
        self.check_parser(input, expect)

    def test_cont_stmt_missing_semi(self):
        input = """
Function: main
    Body:
        Continue
    EndBody.
"""
        expect = "Error on line 5 col 4: EndBody"
        self.check_parser(input, expect)

    # def test_cont_stmt_outside_func(self):
    #     input = "Continue;"
    #     expect = "Error on line 1 col 0: Continue"
    #     self.check_parser(input, expect)
