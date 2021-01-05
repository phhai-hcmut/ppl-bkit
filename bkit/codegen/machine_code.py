'''
*   @author Dr.Nguyen Hua Phung
*   @version 1.0
*   28/6/2006
*   This class provides facilities for method generation
*
'''
from abc import ABC, abstractmethod
from typing import Optional

from .exceptions import IllegalOperandException


class MachineCode(ABC):
    @abstractmethod
    def emitPUSHNULL(self):
        pass

    @abstractmethod
    def emitICONST(self, i):
        # i: Int
        pass

    @abstractmethod
    def emitBIPUSH(self, i):
        # i: Int
        pass

    @abstractmethod
    def emitSIPUSH(self, i):
        # i: Int
        pass

    @abstractmethod
    def emitLDC(self, in_):
        # in_: String
        pass

    @abstractmethod
    def emitFCONST(self, i):
        # i: String
        pass

    @abstractmethod
    def emitILOAD(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitFLOAD(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitISTORE(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitFSTORE(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitALOAD(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitASTORE(self, in_):
        # in_: Int
        pass

    @abstractmethod
    def emitIASTORE(self):
        pass

    @abstractmethod
    def emitFASTORE(self):
        pass

    @abstractmethod
    def emitBASTORE(self):
        pass

    @abstractmethod
    def emitAASTORE(self):
        pass

    @abstractmethod
    def emitIALOAD(self):
        pass

    @abstractmethod
    def emitFALOAD(self):
        pass

    @abstractmethod
    def emitBALOAD(self):
        pass

    @abstractmethod
    def emitAALOAD(self):
        pass

    @abstractmethod
    def emitGETSTATIC(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitPUTSTATIC(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitGETFIELD(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitPUTFIELD(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitIADD(self):
        pass

    @abstractmethod
    def emitFADD(self):
        pass

    @abstractmethod
    def emitISUB(self):
        pass

    @abstractmethod
    def emitFSUB(self):
        pass

    @abstractmethod
    def emitIMUL(self):
        pass

    @abstractmethod
    def emitFMUL(self):
        pass

    @abstractmethod
    def emitIDIV(self):
        pass

    @abstractmethod
    def emitFDIV(self):
        pass

    @abstractmethod
    def emitIAND(self):
        pass

    @abstractmethod
    def emitIOR(self):
        pass

    @abstractmethod
    def emitIREM(self):
        pass

    @abstractmethod
    def emitIFACMPEQ(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFACMPNE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPEQ(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPNE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPLT(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPLE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPGT(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFICMPGE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFEQ(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFNE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFLT(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFLE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFGT(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitIFGE(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitLABEL(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitGOTO(self, label):
        # label: Int
        pass

    @abstractmethod
    def emitINEG(self):
        pass

    @abstractmethod
    def emitFNEG(self):
        pass

    @abstractmethod
    def emitDUP(self):
        pass

    @abstractmethod
    def emitDUPX2(self):
        pass

    @abstractmethod
    def emitPOP(self):
        pass

    @abstractmethod
    def emitI2F(self):
        pass

    @abstractmethod
    def emitNEW(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitNEWARRAY(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitANEWARRAY(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitMULTIANEWARRAY(self, typ, dimensions):
        # typ: String
        # dimensions: Int
        pass

    @abstractmethod
    def emitINVOKESTATIC(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitINVOKESPECIAL(self, lexeme=None, typ=None):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitINVOKEVIRTUAL(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitI(self):
        pass

    @abstractmethod
    def emitF(self):
        pass

    @abstractmethod
    def emit(self):
        pass

    @abstractmethod
    def emitLIMITSTACK(self, in_):
        # in_: String
        pass

    @abstractmethod
    def emitFCMPL(self):
        pass

    @abstractmethod
    def emitLIMITLOCAL(self, in_):
        # in_: String
        pass

    @abstractmethod
    def emitVAR(self, in_, varName, inType, fromLabel, toLabel):
        # in_: Int
        # varName: String
        # inType: String
        # fromLabel: Int
        # toLabel: Int
        pass

    @abstractmethod
    def emitMETHOD(self, lexeme, typ, isStatic):
        # lexeme: String
        # typ: String
        # isStaic: Boolean
        pass

    @abstractmethod
    def emitENDMETHOD(self):
        pass

    @abstractmethod
    def emitSOURCE(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitCLASS(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitSUPER(self, lexeme):
        # lexeme: String
        pass

    @abstractmethod
    def emitSTATICFIELD(self, lexeme, typ, isFinal):
        # lexeme: String
        # typ: String
        # isFinal: Boolean
        pass

    @abstractmethod
    def emitINSTANCEFIELD(self, lexeme, typ):
        # lexeme: String
        # typ: String
        pass

    @abstractmethod
    def emitRETURN(self):
        pass

    @abstractmethod
    def emitIRETURN(self):
        pass

    @abstractmethod
    def emitFRETURN(self):
        pass

    @abstractmethod
    def emitARETURN(self):
        pass


class JasminCode(MachineCode):
    END = '\n'
    INDENT = '\t'

    def emitPUSHNULL(self) -> str:
        return self.INDENT + 'aconst_null' + self.END

    def emitICONST(self, i: int) -> str:
        if i == -1:
            return self.INDENT + 'iconst_m1' + self.END
        elif 0 <= i <= 5:
            return self.INDENT + f'iconst_{i}' + self.END
        else:
            raise IllegalOperandException(str(i))

    def emitBIPUSH(self, i: int) -> str:
        if -128 <= i < -1 or 5 < i <= 127:
            return self.INDENT + f'bipush {i}' + self.END
        else:
            raise IllegalOperandException(str(i))

    def emitSIPUSH(self, i: int) -> str:
        if -32768 <= i < -128 or 127 < i <= 32767:
            return self.INDENT + f'sipush {i}' + self.END
        else:
            raise IllegalOperandException(str(i))

    def emitLDC(self, in_: str) -> str:
        return self.INDENT + f'ldc {in_}' + self.END

    def emitFCONST(self, i: str) -> str:
        if i == '0.0':
            return self.INDENT + 'fconst_0' + self.END
        elif i == '1.0':
            return self.INDENT + 'fconst_1' + self.END
        elif i == '2.0':
            return self.INDENT + 'fconst_2' + self.END
        else:
            raise IllegalOperandException(i)

    def emitILOAD(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'iload_{in_}' + self.END
        else:
            return self.INDENT + f'iload {in_}' + self.END

    def emitFLOAD(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'fload_{in_}' + self.END
        else:
            return self.INDENT + f'fload {in_}' + self.END

    def emitISTORE(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'istore_{in_}' + self.END
        else:
            return self.INDENT + f'istore {in_}' + self.END

    def emitFSTORE(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'fstore_{in_}' + self.END
        else:
            return self.INDENT + f'fstore {in_}' + self.END

    def emitALOAD(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'aload_{in_}' + self.END
        else:
            return self.INDENT + f'aload {in_}' + self.END

    def emitASTORE(self, in_: int) -> str:
        if 0 <= in_ <= 3:
            return self.INDENT + f'astore_{in_}' + self.END
        else:
            return self.INDENT + f'astore {in_}' + self.END

    def emitIASTORE(self) -> str:
        return self.INDENT + 'iastore' + self.END

    def emitFASTORE(self) -> str:
        return self.INDENT + 'fastore' + self.END

    def emitBASTORE(self) -> str:
        return self.INDENT + 'bastore' + self.END

    def emitAASTORE(self) -> str:
        return self.INDENT + 'aastore' + self.END

    def emitIALOAD(self) -> str:
        return self.INDENT + 'iaload' + self.END

    def emitFALOAD(self) -> str:
        return self.INDENT + 'faload' + self.END

    def emitBALOAD(self) -> str:
        return self.INDENT + 'baload' + self.END

    def emitAALOAD(self) -> str:
        return self.INDENT + 'aaload' + self.END

    def emitGETSTATIC(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'getstatic {lexeme} {typ}' + self.END

    def emitPUTSTATIC(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'putstatic {lexeme} {typ}' + self.END

    def emitGETFIELD(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'getfield {lexeme} {typ}' + self.END

    def emitPUTFIELD(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'putfield {lexeme} {typ}' + self.END

    def emitIADD(self) -> str:
        return self.INDENT + 'iadd' + self.END

    def emitFADD(self) -> str:
        return self.INDENT + 'fadd' + self.END

    def emitISUB(self) -> str:
        return self.INDENT + 'isub' + self.END

    def emitFSUB(self) -> str:
        return self.INDENT + 'fsub' + self.END

    def emitIMUL(self) -> str:
        return self.INDENT + 'imul' + self.END

    def emitFMUL(self) -> str:
        return self.INDENT + 'fmul' + self.END

    def emitIDIV(self) -> str:
        return self.INDENT + 'idiv' + self.END

    def emitFDIV(self) -> str:
        return self.INDENT + 'fdiv' + self.END

    def emitIAND(self) -> str:
        return self.INDENT + 'iand' + self.END

    def emitIOR(self) -> str:
        return self.INDENT + 'ior' + self.END

    def emitIREM(self) -> str:
        return self.INDENT + 'irem' + self.END

    def emitIFACMPEQ(self, label: int) -> str:
        return self.INDENT + f'if_acmpeq Label{label}' + self.END

    def emitIFACMPNE(self, label: int) -> str:
        return self.INDENT + f'if_acmpne Label{label}' + self.END

    def emitIFICMPEQ(self, label: int) -> str:
        return self.INDENT + f'if_icmpeq Label{label}' + self.END

    def emitIFICMPNE(self, label: int) -> str:
        return self.INDENT + f'if_icmpne Label{label}' + self.END

    def emitIFICMPLT(self, label: int) -> str:
        return self.INDENT + f'if_icmplt Label{label}' + self.END

    def emitIFICMPLE(self, label: int) -> str:
        return self.INDENT + f'if_icmple Label{label}' + self.END

    def emitIFICMPGT(self, label: int) -> str:
        return self.INDENT + f'if_icmpgt Label{label}' + self.END

    def emitIFICMPGE(self, label: int) -> str:
        return self.INDENT + f'if_icmpge Label{label}' + self.END

    def emitIFEQ(self, label: int) -> str:
        return self.INDENT + f'ifeq Label{label}' + self.END

    def emitIFNE(self, label: int) -> str:
        return self.INDENT + f'ifne Label{label}' + self.END

    def emitIFLT(self, label: int) -> str:
        return self.INDENT + f'iflt Label{label}' + self.END

    def emitIFLE(self, label: int) -> str:
        return self.INDENT + f'ifle Label{label}' + self.END

    def emitIFGT(self, label: int) -> str:
        return self.INDENT + f'ifgt Label{label}' + self.END

    def emitIFGE(self, label: int) -> str:
        return self.INDENT + f'ifge Label{label}' + self.END

    def emitLABEL(self, label: int) -> str:
        return f'Label{label}:' + self.END

    def emitGOTO(self, label: int) -> str:
        return self.INDENT + f'goto Label{label}' + self.END

    def emitINEG(self) -> str:
        return self.INDENT + 'ineg' + self.END

    def emitFNEG(self) -> str:
        return self.INDENT + 'fneg' + self.END

    def emitDUP(self) -> str:
        return self.INDENT + 'dup' + self.END

    def emitDUPX2(self) -> str:
        return self.INDENT + 'dup_x2' + self.END

    def emitPOP(self) -> str:
        return self.INDENT + 'pop' + self.END

    def emitI2F(self) -> str:
        return self.INDENT + 'i2f' + self.END

    def emitNEW(self, lexeme: str) -> str:
        return self.INDENT + f'new {lexeme}' + self.END

    def emitNEWARRAY(self, lexeme: str) -> str:
        return self.INDENT + f'newarray {lexeme}' + self.END

    def emitANEWARRAY(self, lexeme: str) -> str:
        return self.INDENT + f'anewarray {lexeme}' + self.END

    def emitMULTIANEWARRAY(self, typ: str, dimensions: str) -> str:
        return self.INDENT + f'multianewarray {typ} {dimensions}' + self.END

    def emitINVOKESTATIC(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'invokestatic {lexeme}{typ}' + self.END

    def emitINVOKESPECIAL(
        self, lexeme: Optional[str] = None, typ: Optional[str] = None
    ) -> str:
        if lexeme is None and typ is None:
            code = 'invokespecial java/lang/Object/<init>()V'
        elif lexeme is not None and typ is not None:
            code = f'invokespecial {lexeme}{typ}'
        else:
            raise ValueError('lexeme and typ must both not None or None')
        return self.INDENT + code + self.END

    def emitINVOKEVIRTUAL(self, lexeme: str, typ: str) -> str:
        return self.INDENT + f'invokevirtual {lexeme}{typ}' + self.END

    def emitI(self) -> str:
        return self.INDENT + 'i' + self.END

    def emitF(self) -> str:
        return self.INDENT + 'f' + self.END

    def emit(self) -> str:
        return self.INDENT + '' + self.END

    def emitLIMITSTACK(self, in_: int) -> str:
        return f'.limit stack {in_}' + self.END

    def emitFCMPL(self) -> str:
        return self.INDENT + 'fcmpl' + self.END

    def emitLIMITLOCAL(self, in_: int) -> str:
        return f'.limit locals {in_}' + self.END

    def emitVAR(
        self, in_: int, varName: str, inType: str, fromLabel: int, toLabel: int
    ) -> str:
        code = (
            f'.var {in_} is {varName} {inType} from Label{fromLabel} to Label{toLabel}'
        )
        return code + self.END

    def emitMETHOD(self, lexeme: str, typ: str, isStatic: bool) -> str:
        if isStatic:
            code = f'.method public static {lexeme}{typ}'
        else:
            code = f'.method public {lexeme}{typ}'
        return self.END + code + self.END

    def emitENDMETHOD(self) -> str:
        return '.end method' + self.END

    def emitSOURCE(self, lexeme: str) -> str:
        return f'.source {lexeme}' + self.END

    def emitCLASS(self, lexeme: str) -> str:
        return f'.class {lexeme}' + self.END

    def emitSUPER(self, lexeme: str) -> str:
        return f'.super {lexeme}' + self.END

    def emitSTATICFIELD(self, lexeme: str, typ: str, isFinal: bool) -> str:
        if isFinal:
            code = f'.field static final {lexeme} {typ}'
        else:
            code = f'.field static {lexeme} {typ}'
        return code + self.END

    def emitINSTANCEFIELD(self, lexeme: str, typ: str) -> str:
        return f'.field {lexeme} {typ}' + self.END

    def emitRETURN(self) -> str:
        return self.INDENT + 'return' + self.END

    def emitIRETURN(self) -> str:
        return self.INDENT + 'ireturn' + self.END

    def emitFRETURN(self) -> str:
        return self.INDENT + 'freturn' + self.END

    def emitARETURN(self) -> str:
        return self.INDENT + 'areturn' + self.END
