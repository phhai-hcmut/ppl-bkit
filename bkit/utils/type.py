from abc import ABC
from dataclasses import dataclass
from typing import List


class Type(ABC):
    pass


@dataclass(eq=False, frozen=True)
class Unknown(Type):
    """Unresolved type (monomorph)

    A monomorph is a type which may, through unification, morph into a
    different type later. If `prim` is True, it can only morph into a primitive
    type.
    """

    prim: bool = False

    def __bool__(self):
        return False


@dataclass(frozen=True)
class Prim(Type):
    """Primitive type"""


@dataclass(frozen=True)
class BoolType(Prim):
    pass


@dataclass(frozen=True)
class IntType(Prim):
    pass


@dataclass(frozen=True)
class FloatType(Prim):
    pass


@dataclass(frozen=True)
class StringType(Prim):
    pass


@dataclass(frozen=True)
class VoidType(Type):
    pass


@dataclass
class ArrayType(Type):
    elem_type: Prim
    dim: List[int]

    def __bool__(self):
        return bool(self.elem_type)


@dataclass
class FuncType:
    intype: List[Type]
    restype: Type

    def __bool__(self):
        return not isinstance(self.intype, Unknown) and bool(self.restype)


@dataclass
class OpType:
    """Operator type"""

    op_type: Prim  # operand type
    ret_type: Prim  # result type


@dataclass
class MType:
    partype: List[Type]
    rettype: Type


@dataclass
class ClassType(Type):
    cname: str


VOID_TYPE = VoidType()
BOOL_TYPE = BoolType()
INT_TYPE = IntType()
FLOAT_TYPE = FloatType()
STRING_TYPE = StringType()
