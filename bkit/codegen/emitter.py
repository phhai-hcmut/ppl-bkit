"""Helper module for generating Jasmin code"""
from dataclasses import dataclass
from typing import Iterator, Optional, Union, cast

from ..utils.type import *
from .exceptions import IllegalOperandException
from .frame import Frame
from .machine_code import JasminCode

CName = str
Index = int


@dataclass
class Symbol:
    type: Union[Type, MType]
    val: Union[Index, CName]


Emitter = Iterator[str]


_jvm = JasminCode()


def _get_jvm_type(typ: Type) -> str:
    if isinstance(typ, ArrayType):
        return ('[' * len(typ.dim)) + _get_jvm_type(typ.elem_type)
    elif isinstance(typ, MType):
        param_types = ''.join(map(_get_jvm_type, typ.partype))
        return_type = _get_jvm_type(typ.rettype)
        return f'({param_types}){return_type}'
    elif isinstance(typ, ClassType):
        return 'L' + typ.cname + ';'
    else:
        jvm_types = {
            VoidType: 'V',
            BoolType: 'Z',
            IntType: 'I',
            FloatType: 'F',
            StringType: 'Ljava/lang/String;',
        }
        return jvm_types[type(typ)]


def _get_full_type(typ: Prim) -> str:
    full_types = {
        VoidType: 'void',
        BoolType: 'boolean',
        IntType: 'int',
        FloatType: 'float',
        StringType: 'java/lang/String',
    }
    return full_types[type(typ)]


################################################################################
# Directives
################################################################################

def emit_header(name: CName, parent: Optional[str] = None) -> Emitter:
    """Generate some starting directives for a class.

    .source MPC.CLASSNAME.java
    .class public MPC.CLASSNAME
    .super java/lang/Object
    """
    yield _jvm.emitSOURCE(name + '.java')
    yield _jvm.emitCLASS('public ' + name)
    yield _jvm.emitSUPER(parent if parent else 'java/lang/Object')


def emit_field(lexeme: str, typ: Type) -> Emitter:
    """Generate the field (static) directive for a class mutable or immutable attribute.

    lexeme -- the name of the attribute.
    in -- the type of the attribute.
    isFinal -- true in case of constant; false otherwise
    """
    yield _jvm.emitSTATICFIELD(lexeme, _get_jvm_type(typ), False)


def emit_method(name: str, typ: Type, is_static: bool = True) -> Emitter:
    """method directive for a function"""
    yield _jvm.emitMETHOD(name, _get_jvm_type(typ), is_static)


def emit_end_method(frame: Frame) -> Emitter:
    """End directives for a function"""
    yield _jvm.emitLIMITSTACK(frame.getMaxOpStackSize())
    yield _jvm.emitLIMITLOCAL(frame.getMaxIndex())
    yield _jvm.emitENDMETHOD()


def emit_var(var_name: str, sym: Symbol, frame: Frame) -> Emitter:
    """var directive for a local variable"""
    index = cast(Index, sym.val)
    typ = cast(Type, sym.type)
    yield _jvm.emitVAR(
        index,
        var_name,
        _get_jvm_type(typ),
        frame.getStartLabel(),
        frame.getEndLabel(),
    )


################################################################################
# Control Flow Instructions
################################################################################

def emit_label(label: int) -> Emitter:
    """Generate code that represents a label"""
    yield _jvm.emitLABEL(label)


def emit_goto(label: int) -> Emitter:
    """Generate code to jump to a label"""
    yield _jvm.emitGOTO(label)


def emit_if_true(label: int, frame: Frame) -> Emitter:
    """Jump to label if the value on top of operand stack is true."""
    frame.pop()
    yield _jvm.emitIFGT(label)


def emit_if_false(label: int, frame: Frame) -> Emitter:
    """Jump to label if the value on top of operand stack is false."""
    frame.pop()
    yield _jvm.emitIFLE(label)


def emit_invoke_special(frame):
    frame.pop()
    yield _jvm.emitINVOKESPECIAL()


def emit_invoke_static(method_name: str, sym: Symbol, frame) -> Emitter:
    """Invoke a class (static) method

    Operand Stack:
    ..., *args -> ...
    """
    typ = sym.type
    if not isinstance(typ, MType):
        raise IllegalOperandException(f"'{method_name}' must be a method")

    for _ in typ.partype:
        frame.pop()
    if type(typ.rettype) is not VoidType:
        frame.push()
    class_name = cast(CName, sym.val)
    lexeme = class_name + '/' + method_name
    yield _jvm.emitINVOKESTATIC(lexeme, _get_jvm_type(typ))


def emit_return(frame: Frame) -> Emitter:
    """Return value from method

    Operand Stack:
    ..., value -> [empty]
    """
    typ = frame.func_type.rettype

    if type(typ) is not VoidType:
        frame.pop()

    if isinstance(typ, (IntType, BoolType)):
        yield _jvm.emitIRETURN()
    if isinstance(typ, FloatType):
        yield _jvm.emitFRETURN()
    if isinstance(typ, (StringType, ArrayType)):
        yield _jvm.emitARETURN()
    if type(typ) is VoidType:
        yield _jvm.emitRETURN()


################################################################################
# Load/store Instructions
################################################################################

def emit_read_var(name: str, sym: Symbol, frame: Frame) -> Emitter:
    """Load value from a variable

    Operand Stack:
    ... -> ..., value
    """
    frame.push()
    if isinstance(sym.val, Index):
        # Local variable
        index = sym.val
        if isinstance(sym.type, (BoolType, IntType)):
            yield _jvm.emitILOAD(index)
        elif isinstance(sym.type, FloatType):
            yield _jvm.emitFLOAD(index)
        elif isinstance(sym.type, (StringType, ArrayType, ClassType)):
            yield _jvm.emitALOAD(index)
        else:
            msg = f"Local variable {name} has wrong type {sym.type}"
            raise IllegalOperandException(msg)
    else:
        # Global variable
        cname = sym.val
        field_spec = cname + '/' + name
        yield _jvm.emitGETSTATIC(field_spec, _get_jvm_type(sym.type))


def emit_write_var(name: str, sym: Symbol, frame: Frame) -> Emitter:
    """Pop the top value from the operand stack and store it into variable.

    Operand Stack:
    ..., value -> ...
    """
    frame.pop()

    if isinstance(sym.val, Index):
        # Local variable
        index = sym.val
        if isinstance(sym.type, (BoolType, IntType)):
            yield _jvm.emitISTORE(index)
        elif isinstance(sym.type, FloatType):
            yield _jvm.emitFSTORE(index)
        elif isinstance(sym.type, (ArrayType, ClassType, StringType)):
            yield _jvm.emitASTORE(index)
        else:
            msg = f"Local variable {name} has wrong type {sym.type}"
            raise IllegalOperandException(msg)
    else:
        # Global variable
        cname = sym.val
        field_spec = cname + '/' + name
        yield _jvm.emitPUTSTATIC(field_spec, _get_jvm_type(sym.type))


def emit_aload(typ: Prim, frame: Frame) -> Emitter:
    """Load primitive type from array

    Operand Stack:
    ..., arrayref, index -> ..., value
    """
    frame.pop()
    emit = {
        BoolType: _jvm.emitBALOAD,
        IntType: _jvm.emitIALOAD,
        FloatType: _jvm.emitFALOAD,
        StringType: _jvm.emitAALOAD,
    }
    if type(typ) in emit:
        yield emit[type(typ)]()
    else:
        raise IllegalOperandException(str(typ))


def emit_aaload(frame: Frame) -> Emitter:
    """Load reference from array

    Operand Stack:
    ..., arrayref, index -> ..., value
    """
    frame.pop()
    yield _jvm.emitAALOAD()


def emit_astore(typ: Prim, frame: Frame) -> Emitter:
    """Store into primitive array

    Operand Stack:
    ..., arrayref, index, value -> ...
    """
    frame.pop()
    frame.pop()
    frame.pop()
    emit = {
        BoolType: _jvm.emitBASTORE,
        IntType: _jvm.emitIASTORE,
        FloatType: _jvm.emitFASTORE,
        StringType: _jvm.emitAASTORE,
    }
    if type(typ) in emit:
        yield emit[type(typ)]()
    else:
        raise IllegalOperandException(str(typ))


################################################################################
# Stack Manipulation Instructions
################################################################################

def emit_dup(frame: Frame) -> Emitter:
    """Duplicate the top operand stack value

    Operand Stack:
    ..., value -> ..., value, value
    """
    frame.push()
    yield _jvm.emitDUP()


def emit_pop(frame: Frame) -> Emitter:
    """Pop the top operand stack value"""
    frame.pop()
    yield _jvm.emitPOP()


################################################################################
# Object Creation Instructions
################################################################################

def emit_integer(val: Union[int, bool], frame: Frame) -> Emitter:
    frame.push()
    val = int(val)
    if -1 <= val <= 5:
        yield _jvm.emitICONST(val)
    elif -128 <= val <= 127:
        yield _jvm.emitBIPUSH(val)
    elif -32768 <= val <= 32767:
        yield _jvm.emitSIPUSH(val)
    else:
        yield _jvm.emitLDC(str(val))


def emit_float(val: float, frame: Frame) -> Emitter:
    frame.push()
    if val in [0, 1, 2]:
        yield _jvm.emitFCONST(f'{val:.1f}')
    else:
        yield _jvm.emitLDC(str(val))


def emit_string(text: str, frame: Frame) -> Emitter:
    """Push a constant string onto the operand stack."""
    frame.push()
    yield _jvm.emitLDC(f'"{text}"')


def emit_new_array(typ: ArrayType, frame: Frame) -> Emitter:
    """Create new array"""
    if len(typ.dim) == 1:
        yield from emit_integer(typ.dim[0], frame)
        full_type = _get_full_type(typ.elem_type)
        if type(typ.elem_type) is StringType:
            yield _jvm.emitANEWARRAY(full_type)
        else:
            yield _jvm.emitNEWARRAY(full_type)
    else:
        for dim in typ.dim:
            yield from emit_integer(dim, frame)
        for _ in typ.dim:
            frame.pop()
        frame.push()
        yield _jvm.emitMULTIANEWARRAY(_get_jvm_type(typ), str(len(typ.dim)))


################################################################################
# Operator Instructions
################################################################################

def emit_neg(typ: Prim, frame: Frame) -> Emitter:
    """Negate integer or float

    Operand Stack:
    ..., value -> ..., result
    """
    if type(typ) is IntType:
        yield _jvm.emitINEG()
    elif type(typ) is FloatType:
        yield _jvm.emitFNEG()
    else:
        raise IllegalOperandException(f"Not expect operand of type {typ}")


def emit_add(typ: Prim, frame: Frame) -> Emitter:
    """Add integer or float

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    frame.pop()
    if type(typ) is IntType:
        yield _jvm.emitIADD()
    elif type(typ) is FloatType:
        yield _jvm.emitFADD()
    else:
        raise IllegalOperandException(f"Not expect operand of type {typ}")


def emit_sub(typ: Prim, frame: Frame) -> Emitter:
    """Subtract integer or float

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    if type(typ) is IntType:
        yield _jvm.emitISUB()
    elif type(typ) is FloatType:
        yield _jvm.emitFSUB()
    else:
        raise IllegalOperandException(f"Not expect operand of type {typ}")


def emit_mul(typ: Prim, frame: Frame) -> Emitter:
    """Multiply integer or float

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    frame.pop()
    if type(typ) is IntType:
        yield _jvm.emitIMUL()
    elif type(typ) is FloatType:
        yield _jvm.emitFMUL()
    else:
        raise IllegalOperandException(f"Not expect operand of type {typ}")


def emit_div(typ: Prim, frame: Frame) -> Emitter:
    """Divide integer or float

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    frame.pop()
    if type(typ) is IntType:
        yield _jvm.emitIDIV()
    elif type(typ) is FloatType:
        yield _jvm.emitFDIV()
    else:
        raise IllegalOperandException(f"Not expect operand of type {typ}")


def emit_rem(frame: Frame) -> Emitter:
    """Remainder integer

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    frame.pop()
    yield _jvm.emitIREM()


def emit_not(frame: Frame) -> Emitter:
    """Boolean NOT

    Operand Stack:
    ..., value -> ..., result
    """
    yield from emit_integer(True, frame)
    frame.pop()
    yield _jvm.INDENT + 'ixor' + _jvm.END


def emit_cmp(op: str, typ: Prim, frame: Frame) -> Emitter:
    """Compare integer or float

    Operand Stack:
    ..., value1, value2 -> ..., result
    """
    true_label = frame.getNewLabel()
    false_label = frame.getNewLabel()

    frame.pop()
    frame.pop()
    if type(typ) is IntType:
        emit = {
            '==': _jvm.emitIFICMPEQ,
            '!=': _jvm.emitIFICMPNE,
            '<': _jvm.emitIFICMPLT,
            '<=': _jvm.emitIFICMPLE,
            '>': _jvm.emitIFICMPGT,
            '>=': _jvm.emitIFICMPGE,
        }
    else:
        # Comparision with NaN always return False (except not equal)
        if op in ['<.', '<=.']:
            yield _jvm.INDENT + 'fcmpg' + _jvm.END
        else:
            yield _jvm.emitFCMPL()
        emit = {
            '=/=': _jvm.emitIFNE,
            '<.': _jvm.emitIFLT,
            '<=.': _jvm.emitIFLE,
            '>.': _jvm.emitIFGT,
            '>=.': _jvm.emitIFGE,
        }
    yield emit[op](true_label)
    yield from emit_integer(False, frame)
    yield from emit_goto(false_label)
    frame.pop()
    yield from emit_label(true_label)
    yield from emit_integer(True, frame)
    yield from emit_label(false_label)
