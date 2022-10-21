import antlr4

from .BKITLexer import BKITLexer
from .BKITParser import BKITParser

try:
    from .BKITVisitor import BKITVisitor
except ImportError:
    pass


def parse_source(source: antlr4.InputStream) -> BKITParser.ProgramContext:
    """Convenient function to parse BKIT program"""
    lexer = BKITLexer(source)
    tokens = antlr4.CommonTokenStream(lexer)
    parser = BKITParser(tokens)
    return parser.program()
