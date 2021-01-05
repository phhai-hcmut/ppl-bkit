/*
 * Student name: Pham Hoang Hai
 * Student ID: 1852020
 */

grammar BKIT;

@lexer::header {
from ..lexererr import *
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
        return result
}

options { language=Python3; }

/*
 * Parser rules
 */
program : var_decl_part func_decl* ;

func_decl : FUNCTION ':' ident func_params? func_body ;

func_params : PARAMETER ':' param (',' param)* ;

param : declarator ;

func_body : BODY ':' stmt_list END_BODY '.' ;

stmt_list : var_decl_part other_stmt* ;

var_decl_part : var_decl_stmt* ;

other_stmt
	: assign_stmt
	| if_stmt
	| for_stmt
	| while_stmt
	| do_while_stmt
	| break_stmt
	| cont_stmt
	| call_stmt
	| return_stmt
	;

var_decl_stmt : VAR ':' var_decl (',' var_decl)* ';' ;

var_decl : declarator ('=' literal)?  ;

declarator : ident ('[' integer ']')* ;

assign_stmt : lhs '=' expr ';' ;

lhs : ident | elem_expr ;

if_stmt : IF if_then_stmt (ELSE_IF if_then_stmt)* else_stmt? END_IF '.' ;
if_then_stmt : expr THEN stmt_list ;
else_stmt : ELSE stmt_list ;

for_stmt : FOR '(' for_cond ')' DO stmt_list END_FOR '.' ;
for_cond : ident '=' expr ',' expr ',' expr ;

while_stmt : WHILE expr DO stmt_list END_WHILE '.' ;

do_while_stmt : DO stmt_list WHILE expr END_DO '.' ;

break_stmt : BREAK ';' ;

cont_stmt : CONTINUE ';' ;

call_stmt : func_call ';' ;

return_stmt : RETURN expr? ';' ;

func_call : ident '(' arg_list? ')' ;

arg_list : expr (',' expr)* ;

expr : exprp rel_op exprp #rel_expr | exprp #non_rel_expr ;

exprp
	: primary_expr #other_expr
	| elem_expr #other_expr
	| prefix_op exprp #prefix_expr
	| exprp mul_op exprp #binary_expr
	| exprp add_op exprp #binary_expr
	| exprp logical_op exprp #binary_expr
	;

elem_expr :  primary_expr ('[' expr ']')+ ;

primary_expr : paren_expr | literal | ident | call_expr ;

paren_expr : '(' expr ')' ;

call_expr : func_call ;

prefix_op : NOT | INT_MINUS | FLOAT_MINUS ;

mul_op
	: INT_MUL
	| INT_DIV
	| MODULO
	| FLOAT_MUL
	| FLOAT_DIV
	;

add_op
	: INT_ADD
	| INT_MINUS
	| FLOAT_ADD
	| FLOAT_MINUS
	;

logical_op : AND | OR ;

rel_op
	: EQ
	| INT_NEQ
	| INT_LT
	| INT_GT
	| INT_LEQ
	| INT_GEQ
	| FLOAT_NEQ
	| FLOAT_LT
	| FLOAT_GT
	| FLOAT_LEQ
	| FLOAT_GEQ
	;

ident : ID ;

literal
	: integer #integer_literal
	| FLOAT #float_literal
	| TRUE #true_literal
	| FALSE #false_literal
	| STRING #string_literal
	| '{' literal (',' literal)* '}' #array_literal
	;

integer : DEC_INT #decimal | HEX_INT #hex | OCT_INT #octal ;

/*
 * Lexer rules
 */
// Identifier
ID: [a-z] [A-Za-z0-9_]* ;

// Keywords
BREAK:     'Break' ;
CONTINUE:  'Continue' ;
DO:        'Do' ;
END_DO:    'EndDo' ;
IF:        'If' ;
THEN:      'Then' ;
ELSE_IF:   'ElseIf' ;
ELSE:      'Else' ;
END_IF:    'EndIf' ;
FOR:       'For' ;
END_FOR:   'EndFor' ;
FUNCTION:  'Function' ;
PARAMETER: 'Parameter' ;
BODY:      'Body' ;
RETURN:    'Return' ;
END_BODY:  'EndBody' ;
VAR:       'Var' ;
WHILE:     'While' ;
END_WHILE: 'EndWhile' ;

COMMENT : '**' .*? '**' -> skip ; // block comment

UNTERMINATED_COMMENT: '**' ('*' ~'*' | ~'*')* EOF ;

DEC_INT : '0' | [1-9] [0-9]* ;

HEX_INT : '0' [Xx] [1-9] [0-9A-F]* ;

OCT_INT : '0' [Oo] [1-7] [0-7]* ;

FLOAT
	: [0-9]+ DECIMAL EXPONENT
	| [0-9]+ DECIMAL
	| [0-9]+ EXPONENT
	;

fragment DECIMAL : '.' [0-9]* ;

fragment EXPONENT : [Ee] [+-]? [0-9]+ ;

TRUE : 'True';
FALSE : 'False' ;

ILLEGAL_ESCAPE
	: '"' VALID_CHAR* ('\\' ~[bfrnt'\\] | '\'' ~'"')
	{ self.text = self.text[1:] }
	;
UNCLOSE_STRING
	: '"' VALID_CHAR* ('\n' | EOF)
	{ self.text = self.text[1:] }
	;
STRING
	: '"' VALID_CHAR* '"'
	{ self.text = self.text[1:-1] }
	;

// fragment QUOTE : '"' ;
fragment VALID_CHAR : ~[\n\\'"] | ESC | '\'"' ;
fragment ESC : '\\' [bfrnt'\\] ; // escape sequences

// Arithmetic operator
INT_ADD : '+' ;
INT_MINUS : '-' ;
INT_MUL : '*' ;
INT_DIV : '\\' ;
MODULO : '%' ;

FLOAT_ADD : '+.' ;
FLOAT_MINUS : '-.' ;
FLOAT_MUL : '*.' ;
FLOAT_DIV : '\\.' ;

// Boolean operator
NOT : '!' ;
AND : '&&' ;
OR : '||' ;

// Relational operator
EQ : '==' ;
INT_NEQ : '!=' ;
INT_LT : '<' ;
INT_GT : '>' ;
INT_LEQ : '<=' ;
INT_GEQ : '>=' ;
FLOAT_NEQ : '=/=' ;
FLOAT_LT : '<.' ;
FLOAT_GT : '>.' ;
FLOAT_LEQ : '<=.' ;
FLOAT_GEQ : '>=.' ;

WS : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines

ERROR_CHAR : . ;
