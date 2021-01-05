class StaticError(Exception):
    pass


class IllegalOperandException(StaticError):
    # def __init__(self, msg):
    #     # msg:string
    #     self.s = msg

    # def __str__(self):
    #     return "Illegal Operand: " + self.s + "\n"
    pass


class IllegalRuntimeException(StaticError):
    pass
    # def __init__(self, msg):
    #     # msg:string
    #     self.s = msg

    # def __str__(self):
    #     return "Illegal Runtime: " + self.s + "\n"
