from abc import ABC
from dataclasses import dataclass
from typing import List


class Type(ABC):
    pass


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
class MType(Type):
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
