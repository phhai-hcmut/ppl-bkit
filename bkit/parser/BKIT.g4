/*
 * Student name: Pham Hoang Hai
 * Student ID: 1852020
 */

grammar BKIT;

@lexer::header {
from lexererr import *
}

@lexer::members {
def emit(self):
    tk = self.type
    result = super().emit()
    if tk == self.UNCLOSE_STRING:
        raise UncloseString(result.text)
    elif tk == self.ILLEGAL_ESCAPE:
        raise IllegalEscape(result.text)
    elif tk == self.ERROR_CHAR:
        raise ErrorToken(result.text)
    elif tk == self.UNTERMINATED_COMMENT:
        raise UnterminatedComment()
    else:
        return result;
}

options{
	language=Python3;
}

// Lexer rules
ID: [a-z][A-Za-z0-9_]* ;

SEMI: ';' ;

COLON: ':' ;

// Keywords
BREAK : 'Break' ;
CONTINUE : 'Continue' ;
DO : 'Do' ;
END_DO : 'EndDo' ;
IF : 'If' ;
THEN : 'Then' ;
ELSE_IF : 'ElseIf' ;
ELSE : 'Else' ;
END_IF : 'EndIf' ;
FOR : 'For' ;
END_FOR : 'EndFor' ;
FUNCTION : 'Function' ;
PARAMETER : 'Parameter' ;
BODY : 'Body' ;
RETURN : 'Return' ;
END_BODY : 'EndBody' ;
VAR : 'Var' ;
WHILE : 'While' ;
END_WHILE : 'EndWhile' ;

WS : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines

COMMENT : '**' .*? '**' -> skip ; // block comment

INT : [0-9]+
	| '0' [Xx] [0-9A-F]+
	| '0' [Oo] [0-7]+
	;

FLOAT : [0-9]+ DECIMAL EXPONENT | [0-9]+ DECIMAL | [0-9]+ EXPONENT ;
fragment
DECIMAL : '.' [0-9]+ ;
fragment
EXPONENT : [Ee][+-]?[0-9]+ ;

BOOL : 'True' | 'False' ;

STRING : '"' (ESC|~[\r\n\\])*? '"' ;
// escape sequences
fragment ESC : '\\b' | '\\f' | '\\r' | '\\r' | '\\n' | '\\t' | '\\\'' | '\\\\' ;

LITERAL : INT | FLOAT | BOOL | STRING ;

ERROR_CHAR: .;
UNCLOSE_STRING: .;
ILLEGAL_ESCAPE: .;
UNTERMINATED_COMMENT: .;

// Parser rules
program  : VAR COLON ID SEMI EOF ;

expr : ;
assign_stat : ID EQ expr SEMI ;
decl_stat : VAR COLON var_list ;
var_list : var_def | var_def COMMA var_list ;
var_def : ID | ID EQ expr ;

if_stat : IF expr THEN stat_list else_clause ENDIF DOT ;
else_clause : ELSE stat_list | ELSE_IF stat_list else_clause ;

func : FUNCTION COLON ID PARAMETER COLON param_list BODY COLON stat_list END_BODY DOT ;
param_list : ID | ID COMMA param_list ;
