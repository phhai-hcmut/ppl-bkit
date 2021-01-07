import logging
import unittest

from bkit.checker import StaticChecker
from bkit.checker.exceptions import *
from bkit.utils.ast import *


class TestChecker(unittest.TestCase):
    def check_static(self, input, expect):
        # with open('test_cases.py', 'a') as f:
        #     pprint(input, stream=f)
        #     f.write('\n')
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        checker = StaticChecker(input)
        try:
            checker.check()
        except StaticError as result:
            msg = "\nExpected error: " + str(expect)
            self.assertEqual(result, expect, msg)
        else:
            if expect:
                self.fail("Fail to detect error")


class LongTest(TestChecker):
    def test_array_assign(self):
        stmt = Assign(Id('x'), ArrayCell(Id('y'), [IntLiteral(0)]))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [
                    VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)])),
                    VarDecl(Id('y'), [1], None),
                ],
                [stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_khanh(self):
        # input = Program([
        #     FuncDecl(Id('foo'), [VarDecl(Id('x'), [], None)], ([], [Return(IntLiteral(10))])),
        #     FuncDecl(Id('main'), [], ([], [If([(CallExpr(Id('foo'), [CallExpr(Id('foo'), [IntLiteral(5)])]), [], [])], ([], []))]))
        # ])
        input = FuncDecl(
            Id('foo'),
            [VarDecl(Id('x'), [], None), VarDecl(Id('y'), [], None)],
            (
                [VarDecl(Id('z'), [], None)],
                [
                    While(
                        BooleanLiteral(True),
                        (
                            [],
                            [
                                Assign(
                                    Id('z'),
                                    CallExpr(
                                        Id('foo'),
                                        [
                                            IntLiteral(0),
                                            CallExpr(
                                                Id('foo'),
                                                [Id('x'), BooleanLiteral(True)],
                                            ),
                                        ],
                                    ),
                                )
                            ],
                        ),
                    ),
                    Return(BinaryOp('&&', Id('y'), Id('z'))),
                ],
            ),
        )
        expect = ''
        self.check_static(input, expect)

    @unittest.skip
    def test_number_107(self):
        """indexing non array element"""
        raw_input = """Var:a; Function: main Body: a[2][3] = 5; EndBody."""
        input = Program(
            [
                VarDecl(Id('a'), [], None),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [],
                        [
                            Assign(
                                ArrayCell(Id('a'), [IntLiteral(2), IntLiteral(3)]),
                                IntLiteral(5),
                            )
                        ],
                    ),
                ),
            ]
        )
        expect = TypeCannotBeInferred(
            Assign(ArrayCell(Id('a'), [IntLiteral(2), IntLiteral(3)]), IntLiteral(5))
        )
        self.check_static(input, expect)

    @unittest.skip
    def test_number_110(self):
        """call stmt with uninfered array"""
        raw_input = (
            """Function: main Parameter: x Body: Var: arr[2][3]; main(arr); EndBody."""
        )
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [VarDecl(Id('x'), [], None)],
                    (
                        [VarDecl(Id('arr'), [2, 3], None)],
                        [CallStmt(Id('main'), [Id('arr')])],
                    ),
                )
            ]
        )
        expect = TypeCannotBeInferred(CallStmt(Id('main'), [Id('arr')]))
        self.check_static(input, expect)

    def test_number_120(self):
        """many composite function params update"""
        # Raw input
        # Function: main
        #   Parameter: a[2],b[1],c[3]
        #   Body:
        #       Var: x[2],y[1],z[3];
        #       x={1,2};
        #       y[2] = 5;
        #       y = main(x,{1}, {2,3,4});
        #       y = main(x,c,{4,5,6});
        #       c = y;
        #   EndBody.
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [
                        VarDecl(Id('a'), [2], None),
                        VarDecl(Id('b'), [1], None),
                        VarDecl(Id('c'), [3], None),
                    ],
                    (
                        [
                            VarDecl(Id('x'), [2], None),
                            VarDecl(Id('y'), [1], None),
                            VarDecl(Id('z'), [3], None),
                        ],
                        [
                            Assign(
                                Id('x'), ArrayLiteral([IntLiteral(1), IntLiteral(2)])
                            ),
                            Assign(ArrayCell(Id('y'), [IntLiteral(2)]), IntLiteral(5)),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        ArrayLiteral([IntLiteral(1)]),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(2),
                                                IntLiteral(3),
                                                IntLiteral(4),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        Id('c'),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(4),
                                                IntLiteral(5),
                                                IntLiteral(6),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(Id('c'), Id('y')),
                        ],
                    ),
                )
            ]
        )
        expect = TypeMismatchInExpression(
            CallExpr(
                Id('main'),
                [
                    Id('x'),
                    Id('c'),
                    ArrayLiteral([IntLiteral(4), IntLiteral(5), IntLiteral(6)]),
                ],
            )
        )
        self.check_static(input, expect)

    def test_number_121(self):
        """many composite function params update 3"""
        raw_input = """Function: main Parameter: a[2],b[1],c[3] Body: Var: x[2],y[1],z[1]; x={1,2}; y[2] = 5;  y = main(x,{1}, {2,3,4}) ; y = main(x,z,{4,5,6}); c = y; EndBody.  """
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [
                        VarDecl(Id('a'), [2], None),
                        VarDecl(Id('b'), [1], None),
                        VarDecl(Id('c'), [3], None),
                    ],
                    (
                        [
                            VarDecl(Id('x'), [2], None),
                            VarDecl(Id('y'), [1], None),
                            VarDecl(Id('z'), [1], None),
                        ],
                        [
                            Assign(
                                Id('x'), ArrayLiteral([IntLiteral(1), IntLiteral(2)])
                            ),
                            Assign(ArrayCell(Id('y'), [IntLiteral(2)]), IntLiteral(5)),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        ArrayLiteral([IntLiteral(1)]),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(2),
                                                IntLiteral(3),
                                                IntLiteral(4),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        Id('z'),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(4),
                                                IntLiteral(5),
                                                IntLiteral(6),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(Id('c'), Id('y')),
                        ],
                    ),
                )
            ]
        )
        expect = TypeMismatchInStatement(Assign(Id('c'), Id('y')))
        self.check_static(input, expect)

    def test_number_122(self):
        """many composite function params update 4"""
        raw_input = """Function: main Parameter: a[2],b[1],c[3] Body: Var: x[2],y[1],z[1]; x={1,2}; y[2] = 5;  y = main(x,{1}, {2,3,4}) ; y = main(x,z,{4,5,6}); z =x; EndBody.  """
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [
                        VarDecl(Id('a'), [2], None),
                        VarDecl(Id('b'), [1], None),
                        VarDecl(Id('c'), [3], None),
                    ],
                    (
                        [
                            VarDecl(Id('x'), [2], None),
                            VarDecl(Id('y'), [1], None),
                            VarDecl(Id('z'), [1], None),
                        ],
                        [
                            Assign(
                                Id('x'), ArrayLiteral([IntLiteral(1), IntLiteral(2)])
                            ),
                            Assign(ArrayCell(Id('y'), [IntLiteral(2)]), IntLiteral(5)),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        ArrayLiteral([IntLiteral(1)]),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(2),
                                                IntLiteral(3),
                                                IntLiteral(4),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(
                                Id('y'),
                                CallExpr(
                                    Id('main'),
                                    [
                                        Id('x'),
                                        Id('z'),
                                        ArrayLiteral(
                                            [
                                                IntLiteral(4),
                                                IntLiteral(5),
                                                IntLiteral(6),
                                            ]
                                        ),
                                    ],
                                ),
                            ),
                            Assign(Id('z'), Id('x')),
                        ],
                    ),
                )
            ]
        )
        expect = TypeMismatchInStatement(Assign(Id('z'), Id('x')))
        self.check_static(input, expect)


class TestArray(TestChecker):
    def test_1(self):
        stmt = Assign(Id('x'), ArrayLiteral([IntLiteral(0), IntLiteral(0)]))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [1], None)], [stmt]))
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_2(self):
        stmt = Assign(Id('y'), Id('x'))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [
                    VarDecl(Id('x'), [1], None),
                    VarDecl(Id('y'), [2], ArrayLiteral([IntLiteral(0), IntLiteral(0)])),
                ],
                [stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)


# class CheckSuite(TestChecker):
#     @unittest.skip
#     def test_undeclared_function(self):
#         """Simple program: main"""
#         input = """Function: main
#                    Body:
#                         foo();
#                    EndBody."""
#         expect = str(Undeclared(Function(), "foo"))
#         self.assertTrue(TestChecker.test(input, expect, 400))

#     @unittest.skip
#     def test_diff_numofparam_stmt(self):
#         """Complex program"""
#         input = """Function: main
#                    Body:
#                         printStrLn();
#                     EndBody."""
#         expect = str(TypeMismatchInStatement(CallStmt(Id("printStrLn"), [])))
#         self.assertTrue(TestChecker.test(input, expect, 401))

#     @unittest.skip
#     def test_diff_numofparam_expr(self):
#         """More complex program"""
#         input = """Function: main
#                     Body:
#                         printStrLn(read(4));
#                     EndBody."""
#         expect = str(TypeMismatchInExpression(CallExpr(Id("read"), [IntLiteral(4)])))
#         self.assertTrue(TestChecker.test(input, expect, 402))

#     def test_undeclared_function_use_ast(self):
#         """Simple program: main """
#         input = Program([FuncDecl(Id("main"), [], ([], [CallExpr(Id("foo"), [])]))])
#         expect = str(Undeclared(Function(), "foo"))
#         self.assertTrue(TestChecker.test(input, expect, 403))

#     def test_diff_numofparam_expr_use_ast(self):
#         """More complex program"""
#         input = Program([
#             FuncDecl(
#                 Id("main"), [],
#                 (
#                     [],
#                     [
#                         CallStmt(
#                             Id("printStrLn"),
#                             [CallExpr(Id("read"), [IntLiteral(4)])],
#                         )
#                     ],
#                 ),
#             )
#         ])
#         expect = TypeMismatchInExpression(CallExpr(Id("read"), [IntLiteral(4)]))
#         self.check_static(input, expect)

#     def test_diff_numofparam_stmt_use_ast(self):
#         """Complex program"""
#         input = Program(
#             [FuncDecl(Id("main"), [], ([], [CallStmt(Id("printStrLn"), [])]))]
#         )
#         expect = TypeMismatchInStatement(CallStmt(Id("printStrLn"), []))
#         self.check_static(input, expect)


##
def stmt_input_ast(stmt):
    return Program([FuncDecl(Id('main'), [], ([], [stmt]))])


def expr_input_ast(expr):
    return Program([FuncDecl(Id('main'), [], ([], [Return(expr)]))])


class TestDeclaration(TestChecker):
    def test_redecl_var(self):
        """Test redeclare global variable"""
        input = Program([VarDecl(Id('x'), [], None), VarDecl(Id('x'), [], None)])
        expect = Redeclared(Variable(), 'x')
        self.check_static(input, expect)

    def test_redecl_local_var(self):
        """Test redeclare local variable"""
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [], None), VarDecl(Id('x'), [], None)], []),
        )
        expect = Redeclared(Variable(), 'x')
        self.check_static(input, expect)

    def test_redecl_param(self):
        """Redeclare function parameter"""
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None), VarDecl(Id('x'), [], None)],
            ([], []),
        )
        expect = Redeclared(Parameter(), 'x')
        self.check_static(input, expect)

    def test_redecl_param_and_local_var(self):
        """Function with parameter and local variable of the same name"""
        input = FuncDecl(
            Id('main'), [VarDecl(Id('x'), [], None)], ([VarDecl(Id('x'), [], None)], [])
        )
        expect = Redeclared(Variable(), 'x')
        self.check_static(input, expect)

    def test_redecl_param_and_local_var2(self):
        """Function with parameter and inner-scoped local variable of the same name"""
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            ([], [While(BooleanLiteral(True), ([], [VarDecl(Id('x'), [], None)]))]),
        )
        expect = ''
        self.check_static(input, expect)

    def test_redecl_func(self):
        input = Program(
            [FuncDecl(Id('main'), [], ([], [])), FuncDecl(Id('main'), [], ([], []))]
        )
        expect = Redeclared(Function(), 'main')
        self.check_static(input, expect)

    def test_redecl_builtin_func(self):
        """Redeclare built-in function"""
        input = Program([FuncDecl(Id('read'), [], ([], []))])
        expect = Redeclared(Function(), 'read')
        self.check_static(input, expect)

    def test_redeclare_builtin_func_with_var(self):
        """Declare global variable with same name as built-in function"""
        name = 'read'
        input = Program([VarDecl(Id(name), [], None)])
        expect = Redeclared(Variable(), name)
        self.check_static(input, expect)

    def test_redecl_func_var(self):
        """Redeclare a function local variable with same name as parameter"""
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            ([VarDecl(Id('x'), [], None)], []),
        )
        expect = Redeclared(Variable(), 'x')
        self.check_static(input, expect)

    def test_undecl_var(self):
        """Use undeclared variable"""
        input = FuncDecl(Id('main'), [], ([], [Return(Id('x'))]))
        expect = Undeclared(Identifier(), 'x')
        self.check_static(input, expect)

    def test_undecl_func(self):
        """Call undeclared function"""
        input = Program([FuncDecl(Id('main'), [], ([], [CallStmt(Id('foo'), [])]))])
        expect = Undeclared(Function(), 'foo')
        self.check_static(input, expect)

    def test_decl_var_shadow_func(self):
        """Declare a variable that shadow a function with the same name"""
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('main'), [], IntLiteral(0))],
                [CallStmt(Id('main'), [])],
            ),
        )
        expect = Undeclared(Function(), 'main')
        self.check_static(input, expect)

    def test_decl_var_shadow_builtin_func(self):
        """Declare a variable that shadow a built-in function with the same name"""
        name = 'printLn'
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id(name), [], IntLiteral(0))],
                [CallStmt(Id(name), [])],
            ),
        )
        expect = Undeclared(Function(), name)
        self.check_static(input, expect)

    def test_decl_var_in_inner_scope(self):
        """Use variable that is declared in inner scope"""
        input = FuncDecl(
            Id('main'),
            [],
            (
                [],
                [
                    While(
                        BooleanLiteral(True),
                        ([VarDecl(Id('x'), [], None)], []),
                    ),
                    Return(Id('x')),
                ],
            ),
        )
        expect = Undeclared(Identifier(), 'x')
        self.check_static(input, expect)

    def test_use_func_as_id(self):
        """Declare a function and use it as identifier"""
        input = Program(
            [
                FuncDecl(Id('foo'), [], ([], [])),
                FuncDecl(Id('main'), [], ([], [Return(Id('foo'))])),
            ]
        )
        expect = Undeclared(Identifier(), 'foo')
        self.check_static(input, expect)

    def test_use_func_as_id2(self):
        """Use an undeclared function as identifier"""
        input = Program(
            [
                FuncDecl(Id('main'), [], ([], [Return(Id('foo'))])),
                FuncDecl(Id('foo'), [], ([], [])),
            ]
        )
        expect = Undeclared(Identifier(), 'foo')
        self.check_static(input, expect)

    def test_use_builtin_func_as_id(self):
        input = FuncDecl(Id('main'), [], ([], [Return(Id('read'))]))
        expect = Undeclared(Identifier(), 'read')
        self.check_static(input, expect)

    def test_pass_func_to_func(self):
        """Pass a function to another function as argument"""
        input = FuncDecl(Id('main'), [], ([], [CallStmt(Id('print'), [Id('read')])]))
        expect = Undeclared(Identifier(), 'read')
        self.check_static(input, expect)

    def test_scope_of_if_else_stmt(self):
        """Each body of if/else statement has different scope"""
        input = FuncDecl(
            Id('main'),
            [],
            (
                [],
                [
                    If(
                        [
                            (BooleanLiteral(True), [VarDecl(Id('x'), [], None)], []),
                            (BooleanLiteral(True), [], [Return(Id('x'))]),
                        ],
                        ([], []),
                    )
                ],
            ),
        )
        expect = Undeclared(Identifier(), 'x')
        self.check_static(input, expect)


class TestTypeMismatch(TestChecker):
    def test_int_arith_op(self):
        input = BinaryOp('+', IntLiteral(0), FloatLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_unary_not(self):
        input = UnaryOp('!', IntLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_float_arith_op(self):
        input = BinaryOp('+.', IntLiteral(0), FloatLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_logical_op(self):
        input = BinaryOp('&&', IntLiteral(0), FloatLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_int_rel_op(self):
        input = BinaryOp('<', IntLiteral(0), FloatLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_float_rel_op(self):
        input = BinaryOp('<.', IntLiteral(0), FloatLiteral(0))
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_if_stmt(self):
        """Type mismatch in If condition expression"""
        input = If([(IntLiteral(0), [], [])], ([], []))
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_if_stmt2(self):
        """Type mismatch in ElseIf condition expression"""
        input = If([(BooleanLiteral(False), [], []), (IntLiteral(0), [], [])], ([], []))
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_if_stmt3(self):
        """Type mismatch in both If and ElseIf condition expression"""
        input = If([(IntLiteral(0), [], []), (IntLiteral(0), [], [])], ([], []))
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_for_stmt(self):
        """Type mismatch in For statement"""
        stmt = For(
            Id('i'), FloatLiteral(0), BooleanLiteral(True), IntLiteral(1), ([], [])
        )
        input = Program(
            [FuncDecl(Id('main'), [VarDecl(Id('i'), [], None)], ([], [stmt]))]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_for_stmt_idx_var(self):
        """Index variable in for statement is not integer type"""
        stmt = For(
            Id('i'), IntLiteral(0), BooleanLiteral(True), IntLiteral(1), ([], [])
        )
        input = Program(
            [
                FuncDecl(
                    Id('main'), [], ([VarDecl(Id('i'), [], FloatLiteral(0))], [stmt])
                )
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_while_stmt(self):
        input = While(IntLiteral(0), ([], []))
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_call_stmt(self):
        """Call statement with non-void return type"""
        input = CallStmt(Id('read'), [])
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_decl_array(self):
        """Call function with scalar parameter and composite argument"""
        stmt = CallStmt(Id('printStrLn'), [Id('x')])
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [1], None)], [stmt]))
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_assign_array(self):
        """Assign array cell to wrong type"""
        stmt = Assign(ArrayCell(Id('x'), [IntLiteral(0)]), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))], [stmt]),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_diff_numofparam_expr(self):
        """Call expression with wrong number of arguments"""
        input = CallStmt(Id('printStrLn'), [CallExpr(Id('read'), [IntLiteral(4)])])
        expect = TypeMismatchInExpression(CallExpr(Id('read'), [IntLiteral(4)]))
        self.check_static(stmt_input_ast(input), expect)

    def test_diff_numofparam_stmt(self):
        """Call statement with wrong number of arguments"""
        input = CallStmt(Id('read'), [IntLiteral(4)])
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_void_function2(self):
        """Declare a function with non-void return type, then call it in call statement"""
        error_stmt = CallStmt(Id('foo'), [])
        input = Program(
            [
                FuncDecl(Id('foo'), [], ([], [Return(IntLiteral(0))])),
                FuncDecl(Id('main'), [], ([], [error_stmt])),
            ]
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_assign_in_order(self):
        """Infer function paramter type in left hand side before right hand side"""
        error_expr = CallExpr(Id('foo'), [FloatLiteral(0)])
        input = Program(
            [
                VarDecl(Id('a'), [1], ArrayLiteral([IntLiteral(0)])),
                FuncDecl(
                    Id('foo'), [VarDecl(Id('x'), [], None)], ([], [Return(Id('a'))])
                ),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [],
                        [
                            Assign(
                                ArrayCell(
                                    CallExpr(Id('foo'), [IntLiteral(0)]),
                                    [IntLiteral(0)],
                                ),
                                ArrayCell(error_expr, [IntLiteral(0)]),
                            )
                        ],
                    ),
                ),
            ]
        )
        expect = TypeMismatchInExpression(error_expr)
        self.check_static(input, expect)

    def test_assign_with_void_type(self):
        """Assign statement with right hand side is void type"""
        error_stmt = Assign(Id('x'), CallExpr(Id('printLn'), []))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [error_stmt],
            ),
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_if_else_scope(self):
        """Different variable scope in if clause and else clause"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], IntLiteral(0))],
                [
                    If(
                        [
                            (
                                BooleanLiteral(True),
                                [VarDecl(Id('x'), [], FloatLiteral(0))],
                                [],
                            )
                        ],
                        ([], [stmt]),
                    )
                ],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_call_expr_wrong_arg(self):
        """Call expression with wrong argument type"""
        input = CallExpr(Id('string_of_int'), [FloatLiteral(0)])
        expect = TypeMismatchInExpression(input)
        self.check_static(expr_input_ast(input), expect)

    def test_call_stmt_wrong_arg(self):
        """Call statement with wrong argument type"""
        input = CallStmt(Id('print'), [IntLiteral(0)])
        expect = TypeMismatchInStatement(input)
        self.check_static(stmt_input_ast(input), expect)

    def test_array_dim_mismatch(self):
        """ArrayCell with wrong number of dimensions"""
        expr = ArrayCell(Id('x'), [IntLiteral(0), IntLiteral(0)])
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))],
                [Assign(expr, IntLiteral(0))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_array_dim_mismatch_with_func(self):
        """ArrayCell of function with wrong number of dimensions"""
        expr = ArrayCell(CallExpr(Id('foo'), []), [IntLiteral(0)])
        input = Program(
            [
                FuncDecl(
                    Id('foo'),
                    [],
                    (
                        [
                            VarDecl(
                                Id('x'),
                                [1, 1],
                                ArrayLiteral([ArrayLiteral([IntLiteral(0)])]),
                            )
                        ],
                        [Return(Id('x'))],
                    ),
                ),
                FuncDecl(Id('main'), [], ([], [Return(expr)])),
            ]
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_array_wrong_index_type(self):
        """Index expression with non-integer index"""
        expr = ArrayCell(Id('x'), [BooleanLiteral(True)])
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))], [Return(expr)]),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_array_wrong_expr(self):
        """Array cell of non-array expression"""
        input = ArrayCell(IntLiteral(0), [IntLiteral(0)])
        expect = TypeMismatchInExpression(input)
        self.check_static(input, expect)

    def test_assign_func_to_var(self):
        """Assign variable to declared function"""
        input = Program(
            [
                FuncDecl(Id('foo'), [], ([], [Return(IntLiteral(0))])),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [VarDecl(Id('x'), [], None)],
                        [Assign(Id('x'), Id('foo'))],
                    ),
                ),
            ]
        )
        expect = Undeclared(Identifier(), 'foo')
        self.check_static(input, expect)

    def test_assign_func_to_var2(self):
        """Assign variable to undeclared function"""
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [VarDecl(Id('x'), [], None)],
                        [Assign(Id('x'), Id('foo'))],
                    ),
                ),
                FuncDecl(Id('foo'), [], ([], [Return(IntLiteral(0))])),
            ]
        )
        expect = Undeclared(Identifier(), 'foo')
        self.check_static(input, expect)


class TestTypeInference(TestChecker):
    def test_func_param_infer(self):
        """Infer parameter type in declaration"""
        error_expr = CallExpr(Id('foo'), [FloatLiteral(0)])
        input = Program(
            [
                FuncDecl(
                    Id('foo'),
                    [VarDecl(Id('x'), [], None)],
                    ([], [Return(UnaryOp('-', Id('x')))]),
                ),
                FuncDecl(Id('main'), [], ([], [Return(error_expr)])),
            ]
        )
        expect = TypeMismatchInExpression(error_expr)
        self.check_static(input, expect)

    def test_func_param_infer2(self):
        """Infer parameter type in declaration (more tricky)"""
        stmt = CallStmt(Id('foo'), [FloatLiteral(0), FloatLiteral(0)])
        input = Program(
            [
                FuncDecl(
                    Id('foo'),
                    [VarDecl(Id('x'), [], None), VarDecl(Id('y'), [], None)],
                    (
                        [],
                        [
                            Assign(Id('x'), IntLiteral(0)),
                            CallStmt(Id('foo'), [Id('y'), Id('x')]),
                            Return(None),
                        ],
                    ),
                ),
                FuncDecl(Id('main'), [], ([], [stmt])),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_func_param_infer3(self):
        """Infer parameter type in declaration (even more tricky)"""
        # stmt = CallStmt(Id('foo'), [FloatLiteral(0), FloatLiteral(0)])
        input = FuncDecl(
            Id('foo'),
            [VarDecl(Id('x'), [], None), VarDecl(Id('y'), [], None)],
            (
                [VarDecl(Id('z'), [], None)],
                [
                    Assign(
                        Id('z'),
                        CallExpr(
                            Id('foo'),
                            [
                                IntLiteral(0),
                                CallExpr(Id('foo'), [Id('x'), BooleanLiteral(True)]),
                            ],
                        ),
                    )
                ],
            ),
        )
        expect = ''
        self.check_static(input, expect)

    def test_call_stmt_infer_in_order(self):
        """Infer function return type before check parameter in call statement"""
        expr = BinaryOp('+', CallExpr(Id('main'), [IntLiteral(0)]), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            ([], [CallStmt(Id('main'), [expr])]),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_call_expr_infer_in_order(self):
        """Infer function return type before check parameter in call expression"""
        expr = BinaryOp('+', CallExpr(Id('main'), [IntLiteral(0)]), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            ([], [CallStmt(Id('main'), [expr])]),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_func_param_infer_from_first_call(self):
        """Infer parameter type from first call"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = Program(
            [
                FuncDecl(Id('main'), [], ([], [CallStmt(Id('foo'), [IntLiteral(0)])])),
                FuncDecl(
                    Id('foo'),
                    [VarDecl(Id('x'), [], None)],
                    ([], [stmt, Return(None)]),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_var_type_scope(self):
        """Infer variable in inner scope, keep it to outer scope"""
        error_stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    If(
                        [
                            (
                                BooleanLiteral(True),
                                [],
                                [Assign(Id('x'), IntLiteral(0))],
                            )
                        ],
                        ([], []),
                    ),
                    error_stmt,
                ],
            ),
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_infer_on_first_usage(self):
        """Infer variable type on first usage"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [], None)], [Assign(Id('x'), IntLiteral(0)), stmt]),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_var_in_assignment(self):
        """Infer left hand side type from right hand side type"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None), VarDecl(Id('y'), [], IntLiteral(0))],
                [Assign(Id('x'), Id('y')), stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_var_in_assignment2(self):
        """Infer right hand side type from left hand side type"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None), VarDecl(Id('y'), [], IntLiteral(0))],
                [Assign(Id('y'), Id('x')), stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_type_inner_scope(self):
        """Infer variable type in inner scope"""
        error_stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    If(
                        [
                            (
                                BooleanLiteral(True),
                                [],
                                [Assign(Id('x'), IntLiteral(0))],
                            )
                        ],
                        ([], []),
                    ),
                    error_stmt,
                ],
            ),
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_infer_assign(self):
        """Assign an unknown-type variable to itself"""
        error_stmt = Assign(Id('x'), Id('x'))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [error_stmt]))
        expect = TypeCannotBeInferred(error_stmt)
        self.check_static(input, expect)

    def test_infer_assign2(self):
        """Assign unknown-typed function to variable"""
        error_stmt = Assign(Id('x'), CallExpr(Id('foo'), [Id('x')]))
        input = Program(
            [
                FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [error_stmt])),
                FuncDecl(Id('foo'), [VarDecl('x', [], None)], ([], [])),
            ]
        )
        expect = TypeCannotBeInferred(error_stmt)
        self.check_static(input, expect)

    def test_do_while_infer_order(self):
        """Check do while statement's body before condition"""
        error_stmt = Dowhile(([], [Assign(Id('x'), IntLiteral(0))]), Id('x'))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [error_stmt]))
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_while_infer_order(self):
        """Check while statement's body after condition"""
        stmt = Assign(Id('x'), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [], None)], [While(Id('x'), ([], [stmt]))]),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_if_infer_order(self):
        """Check if statement's body after condition"""
        stmt = Assign(Id('x'), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            ([VarDecl(Id('x'), [], None)], [If([(Id('x'), [], [stmt])], ([], []))]),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_else_if_infer_order(self):
        """Check ElseIf condition after If condition"""
        expr = BinaryOp('>', Id('x'), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [If([(Id('x'), [], []), (expr, [], [])], ([], []))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_else_if_infer_order2(self):
        """Check ElseIf condition after If body"""
        expr = BinaryOp('>', Id('x'), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    If(
                        [
                            (
                                BooleanLiteral(True),
                                [],
                                [Assign(Id('x'), BooleanLiteral(True))],
                            ),
                            (expr, [], []),
                        ],
                        ([], []),
                    )
                ],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_else_if_infer_order3(self):
        """Check Else body after If body"""
        expr = BinaryOp('>', Id('x'), IntLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    If(
                        [
                            (
                                BooleanLiteral(True),
                                [],
                                [Assign(Id('x'), BooleanLiteral(True))],
                            ),
                        ],
                        ([], [Return(expr)]),
                    )
                ],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_arity(self):
        """Call a function and then declare it with different number of parameters"""
        error_stmt = CallStmt(Id('foo'), [])
        input = Program(
            [
                FuncDecl(Id('main'), [], ([], [error_stmt])),
                FuncDecl(Id('foo'), [VarDecl(Id('x'), [], None)], ([], [])),
            ]
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_diff_numofparam_expr2(self):
        """Declare a function and then call it with different number of parameters"""
        error_stmt = CallStmt(Id('foo'), [IntLiteral(0), IntLiteral(0)])
        input = Program(
            [
                FuncDecl(Id('foo'), [VarDecl(Id('x'), [], None)], ([], [])),
                FuncDecl(Id('main'), [], ([], [error_stmt])),
            ]
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_infer_func_param_in_nested(self):
        stmt = CallStmt(Id('main'), [CallExpr(Id('main'), [IntLiteral(0)])])
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            (
                [],
                [stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_array_type(self):
        """Infer type for array variable"""
        stmt = Assign(ArrayCell(Id('x'), [IntLiteral(0)]), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [1], None)],
                [Assign(ArrayCell(Id('x'), [IntLiteral(0)]), IntLiteral(0)), stmt],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_param_array_type(self):
        """Infer array type for parameter"""
        stmt = CallStmt(Id('foo'), [FloatLiteral(0)])
        input = Program(
            [
                FuncDecl(
                    Id('foo'), [VarDecl(Id('x'), [1], None)], ([], [Return(None)])
                ),
                FuncDecl(
                    Id('main'),
                    [],
                    ([], [CallStmt(Id('foo'), [ArrayLiteral([IntLiteral(0)])]), stmt]),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_param_array_dim_mismatch(self):
        stmt = CallStmt(Id('foo'), [Id('a')])
        input = Program(
            [
                FuncDecl(
                    Id('foo'), [VarDecl(Id('x'), [5], None)], ([], [Return(None)])
                ),
                FuncDecl(
                    Id('main'),
                    [],
                    ([VarDecl(Id('a'), [1], ArrayLiteral([IntLiteral(0)]))], [stmt]),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_call_by_reference(self):
        stmt = CallStmt(Id('f'), [Id('x')])
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [],
                    ([VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))], [stmt]),
                ),
                FuncDecl(
                    Id('f'),
                    [VarDecl(Id('x'), [1], None)],
                    ([], [Assign(ArrayCell(Id('x'), [IntLiteral(0)]), IntLiteral(1))]),
                ),
            ]
        )
        expect = ''
        self.check_static(input, expect)

    def test_infer_int_type_in_for_stmt(self):
        """Infer index variable type in for statement"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    For(
                        Id('x'),
                        IntLiteral(0),
                        BooleanLiteral(True),
                        IntLiteral(0),
                        ([], [stmt]),
                    )
                ],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_expr_from_left_to_right(self):
        """Infer type from left to right of an expression"""
        expr = BinaryOp('>.', Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [Return(BinaryOp('&&', BinaryOp('>', Id('x'), IntLiteral(0)), expr))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_var_type_in_rhs(self):
        stmt = Assign(Id('x'), BinaryOp('>', Id('x'), IntLiteral(0)))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [stmt]))
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_array_return_type(self):
        """Infer function return type as array"""
        stmt = CallStmt(Id('foo'), [])
        input = Program(
            [
                FuncDecl(Id('foo'), [], ([], [])),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))],
                        [Assign(Id('x'), CallExpr(Id('foo'), [])), stmt],
                    ),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_array_param_and_return_type(self):
        """Infer function parameter and return type as array"""
        stmt = CallStmt(Id('foo'), [Id('x')])
        input = Program(
            [
                FuncDecl(Id('foo'), [VarDecl(Id('x'), [1], None)], ([], [])),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))],
                        [Assign(Id('x'), CallExpr(Id('foo'), [Id('x')])), stmt],
                    ),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_mismatch_in_diff_func(self):
        """Infer variable type in a function and type mismatch in another function"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = Program(
            [
                VarDecl(Id('x'), [], None),
                FuncDecl(Id('foo'), [], ([], [Assign(Id('x'), IntLiteral(0))])),
                FuncDecl(Id('main'), [], ([], [stmt])),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_var_in_for_cond(self):
        """Same variable for all For condition"""
        stmt = For(Id('x'), Id('x'), Id('x'), Id('x'), ([], []))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [stmt]))
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_for_in_order(self):
        """Infer type in For count-controlled condition from left to right"""
        expr = BinaryOp('>.', Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [For(Id('x'), IntLiteral(0), expr, IntLiteral(0), ([], []))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_for_in_order2(self):
        """Infer type in For count-controlled condition before body"""
        stmt = Assign(Id('x'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [], None)],
                [
                    For(
                        Id('x'),
                        IntLiteral(0),
                        BooleanLiteral(True),
                        IntLiteral(0),
                        ([], [stmt]),
                    )
                ],
            ),
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_cannot_infer_in_if_stmt(self):
        """Cannot infer type in If statement condition"""
        stmt = If([(CallExpr(Id('foo'), [Id('x')]), [], [])], ([], []))
        input = FuncDecl(Id('main'), [], ([VarDecl(Id('x'), [], None)], [stmt]))
        expect = TypeCannotBeInferred(stmt)
        self.check_static(input, expect)

    def test_void_function(self):
        """Call a function, infer void type and then declare it with different return type"""
        error_stmt = Return(IntLiteral(0))
        input = Program(
            [
                FuncDecl(Id('main'), [], ([], [CallStmt(Id('foo'), [])])),
                FuncDecl(Id('foo'), [], ([], [error_stmt])),
            ]
        )
        expect = TypeMismatchInStatement(error_stmt)
        self.check_static(input, expect)

    def test_infer_ret_type(self):
        """Infer return type then declare return another type"""
        stmt = Return(FloatLiteral(0))
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [],
                        [Return(BinaryOp('+', CallExpr(Id('foo'), []), IntLiteral(0)))],
                    ),
                ),
                FuncDecl(Id('foo'), [], ([], [stmt])),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_infer_type_from_array_index_in_order(self):
        """Check type of index in array cell from left to right"""
        expr = BinaryOp('+.', Id('y'), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [],
            (
                [VarDecl(Id('x'), [1, 1], None), VarDecl(Id('y'), [], None)],
                [Return(ArrayCell(Id('x'), [Id('y'), expr]))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_type_from_array_index_in_order2(self):
        """Check type of index in array cell from left to right"""
        input = FuncDecl(
            Id('main'),
            [],
            (
                [
                    VarDecl(
                        Id('x'), [1, 1], ArrayLiteral([ArrayLiteral([IntLiteral(0)])])
                    )
                ],
                [
                    Return(
                        ArrayCell(
                            Id('x'),
                            [
                                BinaryOp('+', CallExpr(Id('foo'), []), IntLiteral(0)),
                                CallExpr(Id('foo'), []),
                            ],
                        )
                    )
                ],
            ),
        )
        expect = ''
        self.check_static(input, expect)

    def test_infer_func_hard(self):
        """Infer type for complicated function"""
        expr = CallExpr(Id('main'), [FloatLiteral(0)])
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            (
                [VarDecl(Id('y'), [], None)],
                [
                    Assign(
                        Id('y'),
                        CallExpr(
                            Id('main'),
                            [
                                BinaryOp(
                                    '+',
                                    CallExpr(Id('main'), [IntLiteral(0)]),
                                    IntLiteral(0),
                                )
                            ],
                        ),
                    ),
                    Return(expr),
                ],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_func_hard2(self):
        """Infer type for complicated function"""
        expr = BinaryOp('+.', CallExpr(Id('main'), [FloatLiteral(0)]), FloatLiteral(0))
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            (
                [],
                [Return(BinaryOp('+', CallExpr(Id('main'), [expr]), IntLiteral(0)))],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_func_hard3(self):
        """Infer type for complicated function"""
        expr = CallExpr(
            Id('main'),
            [BinaryOp('+', CallExpr(Id('main'), [FloatLiteral(0)]), IntLiteral(0))],
        )
        input = FuncDecl(
            Id('main'),
            [VarDecl(Id('x'), [], None)],
            (
                [],
                [
                    Return(
                        BinaryOp(
                            '+',
                            expr,
                            IntLiteral(0),
                        )
                    )
                ],
            ),
        )
        expect = TypeMismatchInExpression(expr)
        self.check_static(input, expect)

    def test_infer_param_type_from_array(self):
        """Infer function element of return type from array cell"""
        stmt = CallStmt(Id('foo'), [Id('y')])
        input = Program(
            [
                FuncDecl(
                    Id('foo'),
                    [VarDecl(Id('x'), [1], None)],
                    (
                        [],
                        [Return(None)],
                    ),
                ),
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [
                            VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)])),
                            VarDecl(Id('y'), [1], ArrayLiteral([FloatLiteral(0)])),
                        ],
                        [
                            CallStmt(Id('foo'), [Id('x')]),
                            stmt,
                        ],
                    ),
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        # expect = ''
        self.check_static(input, expect)

    def test_infer_ret_type_from_array2(self):
        """Infer function element of return type from array cell before declaration"""
        # expr = ArrayCell(CallExpr(Id('foo'), []), [IntLiteral(0)])
        input = Program(
            [
                FuncDecl(
                    Id('main'),
                    [],
                    (
                        [VarDecl(Id('x'), [1], ArrayLiteral([IntLiteral(0)]))],
                        [
                            Assign(Id('x'), CallExpr(Id('foo'), [])),
                        ],
                    ),
                ),
                FuncDecl(
                    Id('foo'),
                    [],
                    (
                        [VarDecl(Id('x'), [1], None)],
                        [
                            Assign(ArrayCell(Id('x'), [IntLiteral(0)]), IntLiteral(0)),
                            Return(Id('x')),
                        ],
                    ),
                ),
            ]
        )
        # expect = TypeMismatchInExpression(expr)
        expect = ''
        self.check_static(input, expect)

    def test_infer_ret_type_from_array3(self):
        """Infer function element of return type from array cell before declaration"""
        # expr = ArrayCell(CallExpr(Id('foo'), []), [IntLiteral(0)])
        stmt = Assign(
            ArrayCell(CallExpr(Id('foo'), []), [IntLiteral(0)]), IntLiteral(0)
        )
        input = FuncDecl(Id('main'), [], ([], [stmt]))
        # expect = TypeMismatchInExpression(expr)
        expect = TypeCannotBeInferred(stmt)
        self.check_static(input, expect)

    def test_infer_identity_func(self):
        stmt = Return(Id('x'))
        input = FuncDecl(Id('main'), [VarDecl(Id('x'), [], None)], ([], [stmt]))
        expect = TypeCannotBeInferred(stmt)
        self.check_static(input, expect)

    def test_infer_array_func(self):
        stmt = Return(Id('x'))
        input = FuncDecl(Id('main'), [VarDecl(Id('x'), [1], None)], ([], [stmt]))
        expect = TypeCannotBeInferred(stmt)
        self.check_static(input, expect)

    def test_infer_array_func2(self):
        stmt = Return(ArrayCell(Id('x'), [IntLiteral(0)]))
        input = FuncDecl(Id('main'), [VarDecl(Id('x'), [1], None)], ([], [stmt]))
        expect = TypeCannotBeInferred(stmt)
        self.check_static(input, expect)

    def test_func_return_global_var(self):
        stmt = Assign(Id('x'), CallExpr(Id('foo'), []))
        input = Program(
            [
                VarDecl(Id('a'), [], None),
                FuncDecl(
                    Id('bar'),
                    [],
                    (
                        [],
                        [Return(BinaryOp('+', CallExpr(Id('foo'), []), IntLiteral(0)))],
                    ),
                ),
                FuncDecl(Id('foo'), [], ([], [Return(Id('a'))])),
                FuncDecl(
                    Id('main'), [], ([VarDecl(Id('x'), [], FloatLiteral(0))], [stmt])
                ),
            ]
        )
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)

    def test_call_stmt_and_expr(self):
        stmt = CallStmt(Id('foo'), [CallExpr(Id('foo'), [IntLiteral(0)])])
        input = FuncDecl(Id('main'), [], ([], [stmt]))
        expect = TypeMismatchInStatement(stmt)
        self.check_static(input, expect)


class TestMisc(TestChecker):
    def test_no_entry_point(self):
        """Declare a variable name `main`"""
        input = Program([VarDecl(Id('main'), [], None)])
        expect = NoEntryPoint()
        self.check_static(input, expect)

    def test_no_entry_point2(self):
        """Not declare a function name `main`"""
        input = Program([FuncDecl(Id('foo'), [], ([], []))])
        expect = NoEntryPoint()
        self.check_static(input, expect)
