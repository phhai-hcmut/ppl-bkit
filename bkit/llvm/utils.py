from functools import reduce

from llvmlite import ir

from bkit.utils import type as bkit


def get_successors(inst: ir.Terminator) -> list[ir.Block]:
    match inst:
        case ir.Branch(operands=[target]):
            return [target]  # type: ignore
        case ir.ConditionalBranch(operands=[_, true_block, false_block]):
            return [true_block, false_block]  # type: ignore
        case _:
            return []


def is_block_reachable(func: ir.Function, block: ir.Block) -> bool:
    visited_blocks: set[int] = set()

    def reachable_from(current_block: ir.Block) -> bool:
        if current_block is block:
            return True
        if id(current_block) in visited_blocks:
            return False
        else:
            visited_blocks.add(id(current_block))

        for succ in get_successors(current_block.terminator):
            if reachable_from(succ):
                return True
        return False

    return reachable_from(func.entry_basic_block)


LLVM_BYTE_TYPE = ir.IntType(8)
LLVM_INT_TYPE = ir.IntType(32)
_LLVM_TYPES = {
    bkit.VoidType: ir.VoidType(),
    bkit.BoolType: ir.IntType(1),
    bkit.IntType: ir.IntType(32),
    bkit.FloatType: ir.FloatType(),
    bkit.StringType: LLVM_BYTE_TYPE.as_pointer(),
}


def get_llvm_type(bkit_type: bkit.Type) -> ir.Type:
    match bkit_type:
        case bkit.FuncType(intype=intype, restype=restype):
            args_type = [get_llvm_type(t) for t in intype]
            return ir.FunctionType(get_llvm_type(restype), args_type)
        case bkit.ArrayType(dim=dim, elem_type=elem_type):
            return reduce(ir.ArrayType, dim, get_llvm_type(elem_type)).as_pointer()
        case _:
            return _LLVM_TYPES[type(bkit_type)]
