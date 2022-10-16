from .type import (
    BOOL_TYPE,
    FLOAT_TYPE,
    INT_TYPE,
    STRING_TYPE,
    VOID_TYPE,
    FuncType,
    Prim,
)


def get_operator_type(op: str) -> tuple[Prim, Prim]:
    match op:
        case "+" | "-" | "*" | "\\" | "%":
            return INT_TYPE, INT_TYPE
        case "+." | "-." | "*." | "\\.":
            return FLOAT_TYPE, FLOAT_TYPE
        case "!" | "&&" | "||":
            return BOOL_TYPE, BOOL_TYPE
        case "==" | "!=" | "<" | ">" | "<=" | ">=":
            return INT_TYPE, BOOL_TYPE
        case "=/=" | "<." | ">." | "<=." | ">=.":
            return FLOAT_TYPE, BOOL_TYPE
        case _:
            raise ValueError("Not an operator")


BUILTIN_FUNCS = {
    "int_of_float": FuncType([FLOAT_TYPE], INT_TYPE),
    "float_to_int": FuncType([INT_TYPE], FLOAT_TYPE),
    "int_of_string": FuncType([STRING_TYPE], INT_TYPE),
    "string_of_int": FuncType([INT_TYPE], STRING_TYPE),
    "float_of_string": FuncType([STRING_TYPE], FLOAT_TYPE),
    "string_of_float": FuncType([FLOAT_TYPE], STRING_TYPE),
    "bool_of_string": FuncType([STRING_TYPE], BOOL_TYPE),
    "string_of_bool": FuncType([BOOL_TYPE], STRING_TYPE),
    "read": FuncType([], STRING_TYPE),
    "printLn": FuncType([], VOID_TYPE),
    "print": FuncType([STRING_TYPE], VOID_TYPE),
    "printStrLn": FuncType([STRING_TYPE], VOID_TYPE),
}
