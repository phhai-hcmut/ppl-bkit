from typing import List

from ..utils.type import Type as BKITType, MType
from .exceptions import IllegalRuntimeException


class Frame:
    """Manage stack frame in a method"""
    debug = False

    def __init__(self, name: str, returnType: BKITType):
        self.func_type: MType
        self.name = name
        self.returnType = returnType
        self.currentLabel = 0
        self.currOpStackSize = 0
        self.maxOpStackSize = 0
        self.currIndex: int = 0
        # The maximum index used in generating code for the current method
        self.maxIndex: int = 0
        self.startLabel: List[int] = []
        self.endLabel: List[int] = []
        self.indexLocal: List[int] = []
        self.conLabel: List[int] = []
        self.brkLabel: List[int] = []

    def getNewLabel(self) -> int:
        """Return a new label in the method."""
        tmp = self.currentLabel
        self.currentLabel += 1
        return tmp

    def push(self) -> None:
        """Simulate an instruction that pushes a value onto operand stack."""
        if self.debug:
            print("Push to stack")
        self.currOpStackSize += 1
        if self.maxOpStackSize < self.currOpStackSize:
            self.maxOpStackSize = self.currOpStackSize

    def pop(self) -> None:
        """Simulate an instruction that pops a value out of operand stack."""
        if self.debug:
            print("Pop from stack")
        self.currOpStackSize -= 1
        if self.currOpStackSize < 0:
            raise IllegalRuntimeException("Pop empty stack")

    def getStackSize(self) -> int:
        return self.currOpStackSize

    def getMaxOpStackSize(self) -> int:
        """Return the maximum size of the operand stack that the method needs to use."""
        return self.maxOpStackSize

    def checkOpStack(self) -> None:
        """Check if the operand stack is empty or not.

        Raise IllegalRuntimeException if the operand stack is not empty.
        """
        if self.currOpStackSize != 0:
            raise IllegalRuntimeException("Stack not empty")

    def enterScope(self, isProc: bool) -> None:
        """Invoked when parsing into a new scope inside a method.

        This method will create 2 new labels that represent the starting and
        ending points of the scope. Then, these labels are pushed onto
        corresponding stacks. These labels can be retrieved by getStartLabel()
        and getEndLabel(). In addition, this method also saves the current
        index of local variable.
        """
        start = self.getNewLabel()
        end = self.getNewLabel()
        self.startLabel.append(start)
        self.endLabel.append(end)
        self.indexLocal.append(self.currIndex)
        if isProc:
            self.maxOpStackSize = 0
            self.maxIndex = 0

    def exitScope(self) -> None:
        """Invoked when parsing out of a scope in a method.

        This method will pop the starting and ending labels of this scope and
        restore the current index.
        """
        if not self.startLabel or not self.endLabel or not self.indexLocal:
            raise IllegalRuntimeException("Error when exit scope")
        self.startLabel.pop()
        self.endLabel.pop()
        self.currIndex = self.indexLocal.pop()

    def getStartLabel(self) -> int:
        """Return the starting label of the current scope."""
        if not self.startLabel:
            raise IllegalRuntimeException("None start label")
        return self.startLabel[-1]

    def getEndLabel(self) -> int:
        """Return the ending label of the current scope."""
        if not self.endLabel:
            raise IllegalRuntimeException("None end label")
        return self.endLabel[-1]

    def getNewIndex(self) -> int:
        """Return a new index for a local variable declared in a scope."""
        tmp = self.currIndex
        self.currIndex += 1
        if self.currIndex > self.maxIndex:
            self.maxIndex = self.currIndex
        return tmp

    def getMaxIndex(self):
        return self.maxIndex

    def enterLoop(self) -> None:
        """Invoked when parsing into a loop statement.

        This method creates 2 new labels that represent the starting and ending
        label of the loop. These labels are pushed onto corresponding stacks
        and are retrieved by getBeginLoopLabel() and getEndLoopLabel().
        """
        cont_label = self.getNewLabel()
        break_label = self.getNewLabel()
        self.conLabel.append(cont_label)
        self.brkLabel.append(break_label)

    def exitLoop(self) -> None:
        """Invoked when parsing out of a loop statement.

        This method will take 2 labels representing the starting and ending
        labels of the current loop out of its stacks.
        """
        if not self.conLabel or not self.brkLabel:
            raise IllegalRuntimeException("Error when exit loop")
        self.conLabel.pop()
        self.brkLabel.pop()

    def getContinueLabel(self) -> int:
        """Return an integer representing the continue label

        Return the label of the innest enclosing loop to which continue
        statement would jump.
        """
        if not self.conLabel:
            raise IllegalRuntimeException("None continue label")
        return self.conLabel[-1]

    def getBreakLabel(self) -> int:
        """Return an integer representing the break label

        Return the label of the innest enclosing loop to which break statement
        would jump.
        """
        if not self.brkLabel:
            raise IllegalRuntimeException("None break label")
        return self.brkLabel[-1]
