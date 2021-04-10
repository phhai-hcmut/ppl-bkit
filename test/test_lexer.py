import unittest

from antlr4 import InputStream, Token
from bkit.parser import BKITLexer
from bkit.parser.lexererr import LexerError


# def check_lexeme(input,expect,num):
#     inputfile = make_source(input,num)
#     dest = open("./test/solutions/" + str(num) + ".txt","w")
#     lexer = BKITLexer(inputfile)
#     try:
#         lexemes = lexer.getAllTokens()
#     except LexerError as err:
#         return err.message
#     finally:
#         dest.close()
#     dest = open("./test/solutions/" + str(num) + ".txt","r")
#     line = dest.read()
#     return line == expect


def print_lexeme(lexer):
    try:
        tok = lexer.nextToken()
    except LexerError as err:
        return err.message
    else:
        if tok.type == Token.EOF:
            return "<EOF>"
        else:
            return tok.text + ',' + print_lexeme(lexer)


class TestLexer(unittest.TestCase):
    def check_lexeme(self, input, expect):
        lexer = BKITLexer(InputStream(input))
        # try:
        #     lexemes = lexer.getAllTokens()
        # except LexerError as err:
        #     result = err.message
        # else:
        #     result = ','.join([l.text for l in lexemes]) + ",<EOF>"
        result = print_lexeme(lexer)
        # err_msg = f"Input: {input}\nResult: {result}\nExpect: {expect}"
        self.assertEqual(result, expect, f"Input: {input}")


##
class TestToken(TestLexer):
    def test_wrong_token(self):
        self.check_lexeme("ab?svn", "ab,Error Token ?")

    def test_separators(self):
        self.check_lexeme("( ) [ ] : . , ; { }", "(,),[,],:,.,,,;,{,},<EOF>")


class TestIdentifier(TestLexer):
    def test_simple_id(self):
        self.check_lexeme("a", "a,<EOF>")

    def test_lower_identifier(self):
        """Test identifier contain multiple letters."""
        self.check_lexeme("abc", "abc,<EOF>")

    def test_lower_upper_id(self):
        """Test identifier contains lowercase and uppercase letters."""
        self.check_lexeme("aA", "aA,<EOF>")

    def test_underscore_identifier(self):
        """Test identifier with underscore."""
        self.check_lexeme("ab_c", "ab_c,<EOF>")

    def test_id_contain_digit(self):
        self.check_lexeme("a9", "a9,<EOF>")

    def test_complex_id(self):
        """Test identifier contains letter, digit and underscore."""
        self.check_lexeme("he110_w0r1d", "he110_w0r1d,<EOF>")

    def test_multiple_ids(self):
        self.check_lexeme("a b", "a,b,<EOF>")

    def test_id_begin_with_digit(self):
        self.check_lexeme("2two", "2,two,<EOF>")

    def test_id_begin_with_underscore(self):
        self.check_lexeme("_var", "Error Token _")

    def test_id_begin_with_uppercase(self):
        """Test identifier begins with uppercase letter."""
        self.check_lexeme("Aar", "Error Token A")


class TestString(TestLexer):
    def test_simple_string(self):
        self.check_lexeme("\"a\"", "a,<EOF>")

    def test_normal_string(self):
        self.check_lexeme("\"abc\"", "abc,<EOF>")

    def test_double_string(self):
        self.check_lexeme(""" "a" "b" """, "a,b,<EOF>")

    def test_empty_string(self):
        self.check_lexeme(""" "" """, ",<EOF>")

    def test_string_with_quote(self):
        self.check_lexeme(""" "a'"b" """, "a'\"b,<EOF>")

    def test_normal_string_with_escape(self):
        """Test string with escape sequence."""
        self.check_lexeme(""" "abc\\n def"  """, """abc\\n def,<EOF>""")

    def test_normal_string_with_escape2(self):
        """Test string with escape sequence and double quote."""
        self.check_lexeme(""" "ab'"c\\n def"  """, """ab'"c\\n def,<EOF>""")

    def test_illegal_escape(self):
        self.check_lexeme(""" "abc\\h def"  """, """Illegal Escape In String: abc\\h""")

    def test_illegal_escape2(self):
        """Test unterminated string with illegal escape."""
        self.check_lexeme(""" "abc\\h def\n  """, """Illegal Escape In String: abc\\h""")

    def test_unterminated_string(self):
        self.check_lexeme(""" "abc def  """, """Unclosed String: abc def  """)

    def test_unterminated_string2(self):
        """Test unclosed string conains newline."""
        self.check_lexeme(""" "abc def\n  """, """Unclosed String: abc def\n""")

    def test_special_string(self):
        """Test string contains special characters."""
        self.check_lexeme(""" "a\bb\fc\td"  """, """a\bb\fc\td,<EOF>""")

    # http://e-learning.hcmut.edu.vn/mod/forum/discuss.php?d=127488#p422533
    def test_string_with_standalone_single_quote(self):
        self.check_lexeme(""" "a'b" """, "Illegal Escape In String: a'b")

    def test_string_contain_comment(self):
        self.check_lexeme("\" **comment** string\"", " **comment** string,<EOF>")


class TestInteger(TestLexer):
    def test_simple_integer(self):
        self.check_lexeme("1", "1,<EOF>")

    def test_integer(self):
        self.check_lexeme("12", "12,<EOF>")

    def test_minus_decimal(self):
        self.check_lexeme("-1", "-,1,<EOF>")

    def test_integer_begin_with_zero(self):
        self.check_lexeme("012", "0,12,<EOF>")

    def test_simple_hex(self):
        self.check_lexeme(" 0x2 ", "0x2,<EOF>")

    def test_simple_hex2(self):
        self.check_lexeme(" 0X2 ", "0X2,<EOF>")

    def test_hex_integer(self):
        self.check_lexeme(" 0x2F ", "0x2F,<EOF>")

    def test_hex_integer2(self):
        self.check_lexeme(" 0X2F ", "0X2F,<EOF>")

    def test_hex_with_lowercase(self):
        self.check_lexeme(" 0x1a ", "0x1,a,<EOF>")

    def test_hex_with_keyword(self):
        self.check_lexeme("0x1End", "0x1E,nd,<EOF>")

    def test_hex_begin_with_zero(self):
        self.check_lexeme("0x012", "0,x012,<EOF>")

    def test_hex_begin_with_zero2(self):
        self.check_lexeme("0X012", "0,Error Token X")

    def test_minus_hex(self):
        self.check_lexeme("-0x2", "-,0x2,<EOF>")

    def test_simple_octal(self):
        self.check_lexeme("0o1", "0o1,<EOF>")

    def test_simple_octal2(self):
        self.check_lexeme("0O1", "0O1,<EOF>")

    def test_octal(self):
        self.check_lexeme("0o21", "0o21,<EOF>")

    def test_octal2(self):
        self.check_lexeme("0O21", "0O21,<EOF>")

    def test_octal_with_invalid_digit(self):
        self.check_lexeme("0o29", "0o2,9,<EOF>")

    def test_octal_begin_with_zero(self):
        self.check_lexeme("0O012", "0,Error Token O")

    def test_minus_octal(self):
        self.check_lexeme("-0o1", "-,0o1,<EOF>")


class TestFloat(TestLexer):
    def test_float_with_decimal(self):
        self.check_lexeme("1.2", "1.2,<EOF>")

    def test_float_with_decimal2(self):
        self.check_lexeme("1.", "1.,<EOF>")

    def test_float_with_decimal3(self):
        self.check_lexeme("1.00", "1.00,<EOF>")

    def test_float_with_exponent(self):
        self.check_lexeme("1e2", "1e2,<EOF>")

    def test_float_with_exponent2(self):
        self.check_lexeme("1e20", "1e20,<EOF>")

    def test_float_with_negative_exponent(self):
        self.check_lexeme("1e-2", "1e-2,<EOF>")

    def test_full_float(self):
        self.check_lexeme("1.0e2", "1.0e2,<EOF>")

    def test_full_float2(self):
        self.check_lexeme("1.0e-2", "1.0e-2,<EOF>")

    def test_full_float3(self):
        self.check_lexeme("10.0e22", "10.0e22,<EOF>")

    def test_float_missing_integer_part(self):
        """Test float with decimal part but no integer part."""
        self.check_lexeme(".5", ".,5,<EOF>")

    def test_float_missing_integer_part2(self):
        """Test float with decimal and exponent part but no integer part."""
        self.check_lexeme(".5e3", ".,5e3,<EOF>")

    def test_float_with_invalid_exponent(self):
        self.check_lexeme("2e-+2", "2,e,-,+,2,<EOF>")

    def test_float_with_real_exponent(self):
        self.check_lexeme("1e3.4", "1e3,.,4,<EOF>")

    def test_float_begin_with_zero(self):
        self.check_lexeme("0.12", "0.12,<EOF>")

    def test_minus_float(self):
        self.check_lexeme("-0.1", "-,0.1,<EOF>")

    def test_minus_float2(self):
        self.check_lexeme("-1e1", "-,1e1,<EOF>")

    def test_minus_float3(self):
        self.check_lexeme("-1.0e1", "-,1.0e1,<EOF>")


class TestOperator(TestLexer):
    def test_int_arithemic_op(self):
        self.check_lexeme("+ - * \\ %", "+,-,*,\\,%,<EOF>")

    def test_float_arithemic_op(self):
        self.check_lexeme("+. -. *. \\.", "+.,-.,*.,\\.,<EOF>")

    def test_int_rel_op(self):
        self.check_lexeme("== != < > <= >=", "==,!=,<,>,<=,>=,<EOF>")

    def test_float_rel_op(self):
        self.check_lexeme("=/= <. >. <=. >=.", "=/=,<.,>.,<=.,>=.,<EOF>")

    def test_bool_op(self):
        self.check_lexeme("! && ||", "!,&&,||,<EOF>")


class TestComment(TestLexer):
    def test_normal_comment(self):
        self.check_lexeme("** this is comment ** abc", "abc,<EOF>")

    def test_empty_comment(self):
        self.check_lexeme("**** abc", "abc,<EOF>")

    def test_multiline_comment(self):
        self.check_lexeme("** multiline\n comment ** abc", "abc,<EOF>")

    def test_unterminated_comment(self):
        self.check_lexeme("** this is comment ", "Unterminated Comment")

    def test_unterminated_comment2(self):
        """Test unterminated comment that also contain unclosed string."""
        self.check_lexeme("** \"this is comment ", "Unterminated Comment")

    def test_double_comments(self):
        self.check_lexeme(" **comment1** a **comment2** ", "a,<EOF>")

    def test_comment2(self):
        self.check_lexeme(" **comment1***", "*,<EOF>")

    def test_comment_contain_string(self):
        self.check_lexeme("** \"comment\" **", "<EOF>")


class TestKeyword(TestLexer):
    def test_break(self):
        self.check_lexeme("Break", "Break,<EOF>")

    def test_continue(self):
        self.check_lexeme("Continue", "Continue,<EOF>")

    def test_do(self):
        self.check_lexeme("Do", "Do,<EOF>")

    def test_end_do(self):
        self.check_lexeme("EndDo", "EndDo,<EOF>")

    def test_if(self):
        self.check_lexeme("If", "If,<EOF>")

    def test_then(self):
        self.check_lexeme("Then", "Then,<EOF>")

    def test_else_if(self):
        self.check_lexeme("ElseIf", "ElseIf,<EOF>")

    def test_else(self):
        self.check_lexeme("Else", "Else,<EOF>")

    def test_end_if(self):
        self.check_lexeme("EndIf", "EndIf,<EOF>")

    def test_for(self):
        self.check_lexeme("For", "For,<EOF>")

    def test_end_for(self):
        self.check_lexeme("EndFor", "EndFor,<EOF>")

    def test_function(self):
        self.check_lexeme("Function", "Function,<EOF>")

    def test_parameter(self):
        self.check_lexeme("Parameter", "Parameter,<EOF>")

    def test_body(self):
        self.check_lexeme("Body", "Body,<EOF>")

    def test_return(self):
        self.check_lexeme("Return", "Return,<EOF>")

    def test_end_body(self):
        self.check_lexeme("EndBody", "EndBody,<EOF>")

    def test_var(self):
        self.check_lexeme("Var", "Var,<EOF>")

    def test_while(self):
        self.check_lexeme("While", "While,<EOF>")

    def test_end_while(self):
        self.check_lexeme("EndWhile", "EndWhile,<EOF>")


class TestArrayLiteral(TestLexer):
    def test_simple_array(self):
        self.check_lexeme("{0}", "{,0,},<EOF>")

    def test_array_contain_whitespace(self):
        self.check_lexeme("{ 0 }", "{,0,},<EOF>")

    def test_array_contain_comment(self):
        self.check_lexeme("{1, **second elem** 2}", "{,1,,,2,},<EOF>")

    def test_multiple_array(self):
        self.check_lexeme("{1} {2}", "{,1,},{,2,},<EOF>")

    def test_nested_array(self):
        self.check_lexeme("{1, {2} }", "{,1,,,{,2,},},<EOF>")
