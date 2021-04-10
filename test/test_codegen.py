import os
import shutil
import subprocess
import unittest

from antlr4 import InputStream, CommonTokenStream
from bkit.parser import BKITLexer, BKITParser
from bkit.astgen import ASTGeneration
from bkit.checker import StaticChecker
from bkit.utils.ast import *
from bkit.codegen.code_generator import CodeGenerator


class TestCodeGen(unittest.TestCase):
    def check_codegen(self, input, expect):
        if isinstance(input, str):
            lexer = BKITLexer(InputStream(input))
            tokens = CommonTokenStream(lexer)
            parser = BKITParser(tokens)
            tree = parser.program()
            input = ASTGeneration().visit(tree)

        StaticChecker(input).check()
        path = 'test/codegen_out/'
        if not os.path.exists(path):
            os.makedirs(path)
        CodeGenerator().gen(input, path)
        # os.environ.pop('_JAVA_OPTIONS', None)
        jasmin_cmd = ['java', 'jasmin.Main', '-d', path, '-g', path + 'MCClass.j']
        p = subprocess.run(jasmin_cmd, capture_output=True, text=True)
        if p.returncode != 0:
            self.fail("Jasmin Assembler Error:\n" + p.stderr)
        cmd = ['java', '-Xverify:all', '-cp', path + ':lib', 'MCClass']
        p = subprocess.run(cmd, timeout=2, capture_output=True, text=True)
        if p.returncode != 0:
            self.fail("Java Runtime Error:\n" + p.stderr)
        output = p.stdout
        self.assertEqual(output, expect)


class TestLong(TestCodeGen):
    def test_13(self):
        input = """
Var: a=5, b="string", c=5.6;
Function: main
    Body:
        Var: x=7, y="x", z=2, k = 1.5;
        k = c +. k *. k -. float_to_int(z);
        print(string_of_float(k));
    EndBody.
"""
        input = Program([
            VarDecl(Id('c'), [], FloatLiteral(5.6)),
            FuncDecl(Id('main'), [], ([
                VarDecl(Id('z'), [], IntLiteral(2)),
                VarDecl(Id('k'), [], FloatLiteral(1.5)),
            ], [
                Assign(Id('k'), BinaryOp('-.',
                    BinaryOp('+.', Id('c'), BinaryOp('*.', Id('k'), Id('k'))),
                    CallExpr(Id('float_to_int'), [Id('z')])
                )),
                CallStmt(Id('print'), [CallExpr(Id('string_of_float'), [
                    Id('k')
                ])]),
            ])),
        ])
        expect = "5.85"
        self.check_codegen(input, expect)

    def test_72(self):
        input = """
Function: main
    Body:
        Var: a[3] = {1,2,3};
        a = f(a);
        f1(a[0]);
        f1(a[1]);
        f1(a[2]);
    EndBody.
Function: f
    Parameter: x[3]
    Body:
        x[0] = x[0] + 1;
        x[1] = x[1] + 2;
        x[2] = x[2] + 3;
        Return x;
    EndBody.
Function: f1
    Parameter: temp
    Body:
        print(string_of_int(temp));
        Return;
    EndBody.
"""
        expect = "246"
        self.check_codegen(input, expect)

    # def test_73(self):
    #     input = """"""
    #     expect = ""
    #     self.check_codegen(input, expect)

    # def test_74(self):
    #     input = ""
    #     expect = ""
    #     self.check_codegen(input, expect)


##
EXPR_INPUT_TMPL = """
Function: main
    Body:
        print({0}({1}));
    EndBody.
"""


def expr_input_tmpl(expr, typ):
    print_func = {
        'bool': 'string_of_bool',
        'int': 'string_of_int',
        'float': 'string_of_float',
        'str': '',
    }
    return EXPR_INPUT_TMPL.format(print_func[typ], expr)


class TestSimplePrint(TestCodeGen):
    def test_int_ast(self):
        input = expr_input_tmpl("120", 'int')
        expect = "120"
        self.check_codegen(input, expect)

    def test_large_int(self):
        """Test integer literal larger than short int"""
        input = expr_input_tmpl("327700", 'int')
        expect = "327700"
        self.check_codegen(input, expect)

    def test_print_float(self):
        input = expr_input_tmpl("1.000", 'float')
        expect = "1.0"
        self.check_codegen(input, expect)

    def test_print_string(self):
        input = expr_input_tmpl('"ok"', 'str')
        expect = "ok"
        self.check_codegen(input, expect)

    def test_print_bool(self):
        input = expr_input_tmpl("True", 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_print_inf(self):
        input = expr_input_tmpl("1.0 \\. 0.0", 'float')
        expect = 'Infinity'
        self.check_codegen(input, expect)

    def test_print_neg_inf(self):
        input = expr_input_tmpl("1.0 \\. 0.0", 'float')
        expect = 'Infinity'
        self.check_codegen(input, expect)

    def test_print_neg_zero(self):
        input = expr_input_tmpl("-.1.0 \\. (1.0 \\. 0.0)", 'float')
        expect = "-0.0"
        self.check_codegen(input, expect)

    def test_print_nan(self):
        input = expr_input_tmpl("0.0 \\. 0.0", 'float')
        expect = "NaN"
        self.check_codegen(input, expect)

    def test_float_array(self):
        input = """
Function: main
    Body:
        Var: x[4] = {0.0, 1.0, 2.0, 3.0};
        print(string_of_float(x[0]));
    EndBody.
"""
        expect = "0.0"
        self.check_codegen(input, expect)

    def test_bool_array(self):
        input = """
Function: main
    Body:
        Var: x[2] = {True, False};
        print(string_of_bool(x[0]));
    EndBody.
"""
        expect = "true"
        self.check_codegen(input, expect)

    def test_print_multidim_array(self):
        input = """
Function: main
    Body:
        Var: x[2][2] = {{0, 1}, {2, 3}};
        Var: i = 0, j = 0;
        For (i = 0, i < 2, 1) Do
            For (j = 0, j < 2, 1) Do
                print(string_of_int(x[i][j]));
            EndFor.
        EndFor.
    EndBody.
"""
        expect = "0123"
        self.check_codegen(input, expect)

    def test_print_multidim_array2(self):
        input = """
Function: main
    Body:
        Var: x[2][2] = {{0, 1}, {2, 3}};
        x[0][0] = 5;
        print(string_of_int(x[0][0]));
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_print_multidim_array3(self):
        input = """
Function: main
    Body:
        Var: x[2][2] = {{"0", "1"}, {"2", "3"}};
        x[0][0] = "5";
        print(x[0][0]);
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_print_multidim_array4(self):
        input = """
Function: main
    Body:
        Var: x[1][1][1][1][1] = {{{{{"0"}}}}};
        print(x[0][0][0][0][0]);
    EndBody.
"""
        expect = "0"
        self.check_codegen(input, expect)


class TestExpression(TestCodeGen):
    def test_int_arith(self):
        input = expr_input_tmpl('1 + 2 - 3', 'int')
        expect = "0"
        self.check_codegen(input, expect)

    def test_int_mul(self):
        input = expr_input_tmpl('1 * 2', 'int')
        expect = "2"
        self.check_codegen(input, expect)

    def test_int_pow(self):
        input = """
Function: pow
    Parameter: a, b
    Body:
        Var: i = 0, n = 1;
        For (i = 0, i < b, 1) Do
            n = n * a;
        EndFor.
        Return n;
    EndBody.
Function: main
    Body:
        print(string_of_int(pow(2, 10)));
    EndBody.
"""
        expect = "1024"
        self.check_codegen(input, expect)

    def test_int_div(self):
        input = expr_input_tmpl('3 \\ 2', 'int')
        expect = "1"
        self.check_codegen(input, expect)

    def test_int_neg(self):
        input = expr_input_tmpl('-5', 'int')
        expect = "-5"
        self.check_codegen(input, expect)

    def test_int_comp(self):
        input = expr_input_tmpl('1 < 2', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_int_comp2(self):
        input = expr_input_tmpl('2 > 1', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_int_comp3(self):
        input = expr_input_tmpl('2 != 1', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_int_comp4(self):
        input = expr_input_tmpl('2 >= 2', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_int_comp5(self):
        input = expr_input_tmpl('1 == 1', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_int_assoc(self):
        input = expr_input_tmpl('2 - 3 + 2', 'int')
        expect = "1"
        self.check_codegen(input, expect)

    def test_int_precedence(self):
        input = expr_input_tmpl('1 + 2 * 3', 'int')
        expect = '7'
        self.check_codegen(input, expect)

    def test_modulo(self):
        input = expr_input_tmpl('5 % 2', 'int')
        expect = "1"
        self.check_codegen(input, expect)

    def test_float_mul(self):
        input = expr_input_tmpl('0.5 *. 2.0', 'float')
        expect = "1.0"
        self.check_codegen(input, expect)

    def test_float_div(self):
        input = expr_input_tmpl('1.0 \\. 2.0', 'float')
        expect = "0.5"
        self.check_codegen(input, expect)

    def test_float_comp(self):
        input = expr_input_tmpl('1.0 <. 2.0', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_float_comp2(self):
        input = expr_input_tmpl('2.0 >. 1.0', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_float_comp3(self):
        input = expr_input_tmpl('0.9999 =/= 1.0', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_float_comp4(self):
        input = expr_input_tmpl('0.9999 <=. 1.0', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_float_comp5(self):
        input = expr_input_tmpl('0.9999 >=. 1.0', 'bool')
        expect = "false"
        self.check_codegen(input, expect)

    def test_logical_not(self):
        input = expr_input_tmpl('!False', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_logical_and(self):
        input = expr_input_tmpl('True && True', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_logical_and2(self):
        input = expr_input_tmpl('True && False', 'bool')
        expect = "false"
        self.check_codegen(input, expect)

    def test_logical_or(self):
        input = expr_input_tmpl('False || False', 'bool')
        expect = "false"
        self.check_codegen(input, expect)

    def test_logical_or2(self):
        input = expr_input_tmpl('False || True', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_complex_compare(self):
        input = expr_input_tmpl('(2 < 1) || (1.0 =/= 2.0)', 'bool')
        expect = 'true'
        self.check_codegen(input, expect)

    def test_complex_logical(self):
        input = expr_input_tmpl('(2 > 3) && (1 == 1) || (0 == 0)', 'bool')
        expect = "true"
        self.check_codegen(input, expect)

    def test_compare_inf(self):
        input = """
Function: main
    Body:
        Var: x = 0.0, y = 0.0;
        x = 1.0 \\. 0.0; ** Infinity **
        y = -.x; ** -Infinity **
        print(string_of_bool(1.0 <. x));
        print(",");
        print(string_of_bool(0.0 >. y));
        print(",");
        print(string_of_bool(y <. x));
    EndBody.
"""
        expect = "true,true,true"
        self.check_codegen(input, expect)

    def test_compare_nan(self):
        input = """
Function: main
    Body:
        Var: nan = 0.0;
        nan = 0.0 \\. 0.0;
        **All comparision with NaN return False**
        f(1.0 <. nan);
        f(nan >. 9.0);
        f(nan >=. 1.0);
        f(1.0 <=. nan);
        **Except not equal**
        f(nan =/= nan);
    EndBody.
Function: f
    Parameter: x
    Body:
        print(string_of_bool(x));
        print(",");
    EndBody.
"""
        expect = "false,false,false,false,true,"
        self.check_codegen(input, expect)

    def test_idx_expr(self):
        input = """
Function: main
    Body:
        Var: x[1] = {0}, i = 0;
        print(string_of_int(x[i]));
    EndBody.
"""
        expect = "0"
        self.check_codegen(input, expect)


class TestVariable(TestCodeGen):
    def test_int_global_var(self):
        input = """
Var: x = 1;
Function: main
    Body:
        print(string_of_int(x));
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_array_global_var(self):
        input = """
Var: x[1] = {1};
Function: main
    Body:
        print(string_of_int(x[0]));
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_array_local_var(self):
        input = """
Function: main
    Parameter: args[0]
    Body:
        Var: x[1] = {1};
        print(string_of_int(x[0]));
    EndBody.
"""
        expect = '1'
        self.check_codegen(input, expect)

    def test_var_scope(self):
        """Test local variable shadow function"""
        input = """
Function: main
    Body:
        Var: main = "1";
        print(main);
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_var_scope2(self):
        """Test inner variable shadow outer variable"""
        input = """
Function: main
    Body:
        Var: x = "0";
        If True Then
            Var: x = "1";
            print(x);
        EndIf.
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_var_scope3(self):
        """Test inner variable live in inner scope"""
        input = """
Function: main
    Body:
        Var: x = "0";
        If True Then
            Var: x = "1";
        EndIf.
        print(x);
    EndBody.
"""
        expect = "0"
        self.check_codegen(input, expect)

    def test_var_scope4(self):
        """Test change outer variable from inner scope"""
        input = """
Function: main
    Body:
        Var: x = "0";
        If True Then
            x = "1";
        EndIf.
        print(x);
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_var_scope5(self):
        input = """
Var: x = "0";
Function: main
    Body:
        Var: x = "1";
        print(x);
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_var_scope_if(self):
        input = """
Function: f
    Parameter: b
    Body:
        Var: x = "0";
        If b Then
            Var: x = "1";
            print(x);
        Else
            print(x);
        EndIf.
    EndBody.
Function: main
    Body:
        f(True);
        f(False);
    EndBody.
"""
        expect = "10"
        self.check_codegen(input, expect)


class TestLoop(TestCodeGen):
    def test_simple_for(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        For (i = 0, i < 5, 1) Do
            print(string_of_int(i));
        EndFor.
    EndBody.
"""
        expect = "01234"
        self.check_codegen(input, expect)

    def test_nested_for(self):
        input = """
Function: main
    Body:
        Var: i = 0, j = 0;
        For (i = 0, i < 2, 1) Do
            print(string_of_int(i));
            For (j = 0, j < 2, 1) Do
                print(string_of_int(j));
            EndFor.
        EndFor.
    EndBody.
"""
        expect = "001101"
        self.check_codegen(input, expect)

    def test_simple_while(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        While i < 5 Do
            print(string_of_int(i));
            i = i + 1;
        EndWhile.
    EndBody.
"""
        expect = "01234"
        self.check_codegen(input, expect)

    def test_while_with_break(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        While True Do
            i = i + 1;
            If i == 5 Then
                Break;
            EndIf.
        EndWhile.
        print(string_of_int(i));
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_while_with_cont(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        While True Do
            i = i + 1;
            If i < 5 Then
                Continue;
            EndIf.
            Break;
        EndWhile.
        print(string_of_int(i));
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_simple_dowhile(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        Do
            print(string_of_int(i));
            i = i + 1;
        While i < 5 EndDo.
    EndBody.
"""
        expect = "01234"
        self.check_codegen(input, expect)

    def test_dowhile_run_once(self):
        """Test do while loop run at least once"""
        input = """
Function: main
    Body:
        Do
            print("ok");
        While False EndDo.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_dowhile_with_break(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        Do
            i = i + 1;
            If i == 5 Then
                Break;
            EndIf.
        While True EndDo.
        print(string_of_int(i));
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_dowhile_with_cont(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        Do
            i = i + 1;
            If i < 5 Then
                Continue;
            EndIf.
            Break;
        While True EndDo.
        print(string_of_int(i));
    EndBody.
"""
        expect = "5"
        self.check_codegen(input, expect)

    def test_break_inner_loop(self):
        input = """
Function: main
    Body:
        Var: x = 0;
        While True Do
            For (x = 0, x < 5, 1) Do
                If x == 1 Then
                    Break;
                EndIf.
            EndFor.
            print("ok");
            Break;
        EndWhile.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_short_return(self):
        input = """
Function: main
    Body:
        print("ok");
        Return;
        print("not ok");
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_short_return2(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        While True Do
            print(string_of_int(i));
            If i > 5 Then
                Return;
            Else
                i = i + 1;
            EndIf.
        EndWhile.
    EndBody.
"""
        expect = "0123456"
        self.check_codegen(input, expect)


class TestFunction(TestCodeGen):
    def test_func_array(self):
        input = """
Var: a[1] = {0};
Function: f
    Parameter: x[1]
    Body:
        Return a;
    EndBody.
Function: main
    Body:
        f(f(a))[0] = 1;
        print(string_of_int(a[0]));
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_simple_func_call(self):
        input = """
Function: main
    Body:
        f();
    EndBody.
Function: f
    Body:
        print("ok");
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_func_call_with_param(self):
        input = """
Function: f
    Parameter: x
    Body:
        print(x);
    EndBody.
Function: main
    Body:
        f("ok");
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_func_call_with_array_param(self):
        input = """
Function: f
    Parameter: x[1]
    Body:
        print(x[0]);
    EndBody.
Function: main
    Body:
        f({"ok"});
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_func_call_with_array_param2(self):
        input = """
Function: f
    Parameter: x[2][2]
    Body:
        Var: i = 0, j = 0;
        For (i = 0, i < 2, 1) Do
            For (j = 0, j < 2, 1) Do
                print(string_of_int(x[i][j]));
            EndFor.
        EndFor.
        Return;
    EndBody.
Function: main
    Body:
        Var: x[2][2] = {{0, 1}, {2, 3}};
        f(x);
    EndBody.
"""
        expect = "0123"
        self.check_codegen(input, expect)

    def test_empty_func(self):
        input = """
Function: main
    Body:
        f();
        g(0, 1.0);
    EndBody.
Function: f
    Body:
    EndBody.
Function: g
    Parameter: x, y
    Body:
    EndBody.
"""
        expect = ""
        self.check_codegen(input, expect)

    def test_func_return_array(self):
        input = """
Var: x[1] = {0};
Function: f
    Body:
        Return x;
    EndBody.
Function: main
    Body:
        f()[0] = 1;
        print(string_of_int(x[0]));
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_pass_by_value(self):
        input = """
Function: f
    Parameter: x
    Body:
        x = 1;
    EndBody.
Function: main
    Body:
        Var: x = 0;
        f(x);
        print(string_of_int(x));
    EndBody.
"""
        expect = "0"
        self.check_codegen(input, expect)

    def test_pass_by_reference(self):
        """Test pass array by reference"""
        input = """
Function: main
    Body:
        Var: x[1] = {0};
        f(x);
        print(string_of_int(x[0]));
    EndBody.
Function: f
    Parameter: x[1]
    Body:
        x[0] = 1;
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)

    def test_strict_arg_eval(self):
        """Evaluate all arguments before pass them to function"""
        input = """
Function: f
    Body:
        print("0");
        Return True;
    EndBody.
Function: g
    Body:
        print("1");
        Return True;
    EndBody.
Function: main
    Body:
        h(f(), g());
    EndBody.
Function: h
    Parameter: x, y
    Body:
        print("2");
    EndBody.
"""
        expect = "012"
        self.check_codegen(input, expect)

    def test_func_infer_from_arr_idx(self):
        input = """
Function: main
    Body:
        Var: x[1] = {0};
        print(string_of_int(x[f(0)]));
    EndBody.
Function: f
    Parameter: x
    Body:
        Return x;
    EndBody.
"""
        expect = "0"
        self.check_codegen(input, expect)

    def test_func_infer(self):
        """Test simple function infer tree.

        main --> g --> f
        """
        input = """
Function: main
    Body:
        print(string_of_int(g(1)));
    EndBody.
Function: g
    Parameter: x
    Body:
        Return x + f(x);
    EndBody.
Function: f
    Parameter: x
    Body:
        Return x;
    EndBody.
"""
        expect = "2"
        self.check_codegen(input, expect)

    def test_func_infer2(self):
        """Test complex function infer tree.

             --> g --> f
            /
        main --> h
        """
        input = """
Function: main
    Body:
        Var: x = 0;
        x = g(1);
        h("2");
    EndBody.
Function: f
    Parameter: x
    Body:
        Return {1};
    EndBody.
Function: g
    Parameter: x
    Body:
        Return x + f(x)[0];
    EndBody.
Function: h
    Parameter: x
    Body:
        print(x);
    EndBody.
"""
        expect = "2"
        self.check_codegen(input, expect)

    def test_func_infer3(self):
        """Test even more complex function infer tree.

             --> g --> h
            /
        main --> f
        """
        input = """
Function: main
    Body:
        Var: x = 0;
        x = f(f(x, 0), g());
        print(string_of_int(x));
    EndBody.
Function: f
    Parameter: x, y
    Body:
        Return 1;
    EndBody.
Function: g
    Body:
        Return h(0);
    EndBody.
Function: h
    Parameter: x
    Body:
        Return f(0, 0);
    EndBody.
"""
        expect = "1"
        self.check_codegen(input, expect)


class TestControlFlow(TestCodeGen):
    def test_simple_if(self):
        input = """
Function: main
    Parameter: args[0]
    Body:
        If True Then
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_simple_if2(self):
        input = """
Function: main
    Parameter: args[0]
    Body:
        If False Then
            print("not ok");
        Else
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_if_full_cond(self):
        input = """
Function: main
    Parameter: args[0]
    Body:
        Var: n = 0;
        If n > 0 Then
            print("not ok");
        Else
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_else_if(self):
        input = """
Function: main
    Body:
        If False Then
            print("not ok");
        ElseIf True Then
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_else_if_chain(self):
        input = """
Function: f
    Parameter: n
    Body:
        If n < 5 Then
            print("0");
        ElseIf n < 10 Then
            print("1");
        ElseIf n < 20 Then
            print("2");
        EndIf.
    EndBody.
Function: main
    Body:
        f(0);
        f(5);
        f(10);
    EndBody.
"""
        expect = "012"
        self.check_codegen(input, expect)

    def test_else_if_chain2(self):
        input = """
Function: f
    Parameter: n
    Body:
        If n < 5 Then
            print("0");
        ElseIf n < 10 Then
            print("1");
        ElseIf n < 20 Then
            print("2");
        Else
            print("3");
        EndIf.
    EndBody.
Function: main
    Body:
        f(0);
        f(5);
        f(10);
        f(20);
    EndBody.
"""
        expect = "0123"
        self.check_codegen(input, expect)

    def test_nested_if(self):
        input = """
Function: f
    Parameter: x
    Body:
        If x Then
            print("0");
            If x Then
                print("1");
            EndIf.
        Else
            If !x Then
                print("2");
            EndIf.
        EndIf.
    EndBody.
Function: main
    Body:
        f(True);
        f(False);
    EndBody.
"""
        expect = "012"
        self.check_codegen(input, expect)

    def test_short_and(self):
        input = """
Function: f
    Body:
        print("not ok");
        Return True;
    EndBody.
Function: main
    Body:
        If False && f() Then
        Else
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_short_or(self):
        input = """
Function: f
    Body:
        print("not ok");
        Return True;
    EndBody.
Function: main
    Body:
        If True || f() Then
            print("ok");
        EndIf.
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_short_and_or(self):
        input = """
Function: f
    Body:
        print("ok");
        Return True;
    EndBody.
Function: main
    Body:
        Var: x = True;
        x = True && f() || f();
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)

    def test_short_and_or2(self):
        input = """
Function: f
    Body:
        print("ok");
        Return True;
    EndBody.
Function: main
    Body:
        Var: x = True;
        x = f() || f() && f();
    EndBody.
"""
        expect = "okok"
        self.check_codegen(input, expect)

    def test_short_and_or3(self):
        input = """
Function: f
    Body:
        print("ok");
        Return True;
    EndBody.
Function: main
    Body:
        Var: a = False, b = True, c = True;
        b = (a && f()) || c; **Not call f**
        b = (a || c) && (f() || c); **Call f**
    EndBody.
"""
        expect = "ok"
        self.check_codegen(input, expect)


# @unittest.skip
class TestComplete(TestCodeGen):
    def test_factorial(self):
        input = """
Function: main
    Body:
        print(string_of_int(fact(5)));
    EndBody.
Function: fact
    Parameter: n
    Body:
        If n == 0 Then
            Return 1;
        Else
            Return n * fact(n - 1);
        EndIf.
    EndBody.
"""
        expect = "120"
        self.check_codegen(input, expect)

    def test_fibonacci(self):
        input = """
Function: fib
    Parameter: n
    Body:
        Var: x = 0;
        If (n == 0) || (n == 1) Then
            x = 1;
        Else
            x = fib(n - 1) + fib(n - 2);
        EndIf.
        Return x;
    EndBody.
Function: main
    Body:
        print(string_of_int(fib(5)));
    EndBody.
"""
        expect = '8'
        self.check_codegen(input, expect)

    def test_float_factorial(self):
        input = """
Function: main
    Body:
        print(string_of_float(fact(50.0)));
    EndBody.
Function: fact
    Parameter: n
    Body:
        If n <=. 0.0 Then
            Return 1.0;
        Else
            Return n *. fact(n -. 1.0);
        EndIf.
    EndBody.
"""
        expect = "Infinity"
        self.check_codegen(input, expect)

    def test_float_factorial2(self):
        input = """
Function: main
    Body:
        Var: x = 0.0;
        x = fact(50.0);
        print(string_of_float(x -. x));
    EndBody.
Function: fact
    Parameter: n
    Body:
        If n <=. 0.0 Then
            Return 1.0;
        Else
            Return n *. fact(n -. 1.0);
        EndIf.
    EndBody.
"""
        expect = "NaN"
        self.check_codegen(input, expect)

    def test_mutual_rec_func(self):
        """Test mutally recursive function"""
        input = """
Function: is_even
    Parameter: n
    Body:
        If n == 0 Then
            Return True;
        Else
            Return is_odd(n - 1);
        EndIf.
    EndBody.
Function: is_odd
    Parameter: n
    Body:
        If n == 0 Then
            Return False;
        Else
            Return is_even(n - 1);
        EndIf.
    EndBody.
Function: main
    Body:
        print(string_of_bool(is_even(5)));
        print(",");
        print(string_of_bool(is_odd(5)));
        print(",");
        print(string_of_bool(is_even(4)));
        print(",");
        print(string_of_bool(is_odd(4)));
    EndBody.
"""
        expect = 'false,true,true,false'
        self.check_codegen(input, expect)

    def test_mutual_rec_func2(self):
        """Test mutally recursive function (shorter)"""
        input = """
Function: is_even
    Parameter: n
    Body:
        Return (n == 0) || is_odd(n - 1);
    EndBody.
Function: is_odd
    Parameter: n
    Body:
        Return !((n == 0) || !is_even(n - 1));
    EndBody.
Function: main
    Body:
        print(string_of_bool(is_even(5)));
        print(",");
        print(string_of_bool(is_odd(5)));
        print(",");
        print(string_of_bool(is_even(4)));
        print(",");
        print(string_of_bool(is_odd(4)));
    EndBody.
"""
        expect = 'false,true,true,false'
        self.check_codegen(input, expect)

    def test_short_halt(self):
        """This program will not halt if || is not short-circuit"""
        input = """
Function: main
    Body:
        Var: x = False;
        x = True || f();
        print(string_of_bool(x));
    EndBody.
Function: f
    Body:
        Return f();
    EndBody.
"""
        expect = 'true'
        self.check_codegen(input, expect)

    def test_short_halt2(self):
        """This program will not halt if && is not short-circuit"""
        input = """
Function: main
    Body:
        Var: x = False;
        x = False && f();
        print(string_of_bool(x));
    EndBody.
Function: f
    Body:
        While True Do
        EndWhile.
        Return False;
    EndBody.
"""
        expect = 'false'
        self.check_codegen(input, expect)

    def test_fizzbuzz(self):
        input = """
Function: main
    Body:
        Var: i = 0;
        For (i = 0, i <= 5, 1) Do
            fizzbuzz(i);
        EndFor.
    EndBody.
Function: fizzbuzz
    Parameter: i
    Body:
        If i % 3 == 0 Then
            print("fizz");
        EndIf.
        If i % 5 == 0 Then
            print("buzz");
        EndIf.
        If (i % 3) * (i % 5) != 0 Then
            print(string_of_int(i));
        EndIf.
        printLn();
    EndBody.
"""
        expect = "fizzbuzz\n1\n2\nfizz\n4\nbuzz\n"
        self.check_codegen(input, expect)
