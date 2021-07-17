from aenum import Enum as aenum
import re
from collections import namedtuple as named_tuple


class Enum(str, aenum):
    """A super-class used to give methods to very enum in the application."""
    @classmethod
    def values(cls):
        """Returns a list of all the values of the Enum."""
        return list(map(lambda c: c.value, cls))


class VAR_TYPES(Enum):
    DECIMAL = 'dec'
    INT = 'int'
    STR = 'str'
    LIST = 'list'
    DICT = 'dict'

# The characters that a valid control sequence can have
CMND_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"

class TT(Enum):
    """Token Types"""
    #OPAREN = 'OPENNING PARENTHESIS' # r'('
    #CPAREN = 'CLOSING PARENTHESIS'  # r')'
    #OBRACE = 'OPENING BRACE'        # r'['
    #CBRACE = 'CLOSING BRACE'        # r']'
    #BACKSLASH = 'BACKSLASH'         # r'\'
    OCBRACE = 'OPENING CURLY BRACE'  # r'{'
    CCBRACE = 'CLOSING CURLY BRACE'  # r'}'
    EQUAL_SIGN = 'EQUALS SIGN'       # r'='

    EXEC_PYTH1 = 'PYTHON EXEC FIRST PASS'
    EVAL_PYTH1 = 'PYTHON EVAL FOR FIRST PASS'
    EXEC_PYTH2 = 'PYTHON EXEC SECOND PASS'
    EVAL_PYTH2 = 'PYTHON EVAL FOR SECOND PASS'

    PARAGRAPH_BREAK = 'PARAGRAPH BREAK'

    CMND_NAME = 'COMMAND NAME'

    FILE_START = 'FILE START'
    FILE_END = 'FILE END'

    WORD = 'WORD'

END_LINE_CHARS = ('\r\n', '\n')

def match(match_terms):
    """
    Compiles a list of strings into a match object.
    """
    #regex_str = '(' + '|'.join(match_terms) + ')'
    return match_terms

def nl(*args):
    """
    Adds newlines to the given terms and returns them
    """
    new_terms = []
    for term in args:
        new_terms.append(term + '\r\n')
        new_terms.append(term + '\n')
        new_terms.append(term)

    return new_terms

class TT_M:
    """
    What the more complex tokens should each match.
    """
    # PYTHON CODE IDENTIFIERS
    #   FIRST PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_1PASS_EXEC_START =    match(['\\1>'])
    ONE_LINE_PYTH_1PASS_EXEC_END =      match([*nl('<\\', '<1\\'), *END_LINE_CHARS])
    MULTI_LINE_PYTH_1PASS_EXEC_START =  match(['\\1->'])
    MULTI_LINE_PYTH_1PASS_EXEC_END =    match([*nl('<-\\', '<-1\\')])

    #       EVAL PYTHON
    ONE_LINE_PYTH_1PASS_EVAL_START =    match(['\\1?>'])
    ONE_LINE_PYTH_1PASS_EVAL_END =      match([*nl('<\\', '<?\\', '<?1\\'), *END_LINE_CHARS])
    MULTI_LINE_PYTH_1PASS_EVAL_START =  match(['\\1?->'])
    MULTI_LINE_PYTH_1PASS_EVAL_END =    match([*nl('<-\\', '<-?1\\')])

    #   SECOND PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_2PASS_EXEC_START =    match(['\\>', '\\2>'])
    ONE_LINE_PYTH_2PASS_EXEC_END =      match([*nl('<\\', '<2\\'), *END_LINE_CHARS])
    MULTI_LINE_PYTH_2PASS_EXEC_START =  match(['\\->', '\\2->'])
    MULTI_LINE_PYTH_2PASS_EXEC_END =    match([*nl('<-2\\')])

    #       EVAL PYTHON
    ONE_LINE_PYTH_2PASS_EVAL_START =    match(['\\?>', '\\2?>'])
    ONE_LINE_PYTH_2PASS_EVAL_END =      match([*nl('<\\', '<?\\', '<?2\\'), *END_LINE_CHARS])
    MULTI_LINE_PYTH_2PASS_EVAL_START =  match(['\\?->'])
    MULTI_LINE_PYTH_2PASS_EVAL_END =    match([*nl('<-?\\')])

del nl

# -----------------------------------------------------------------------------
# API Constants (Constants that people compiling their pdf might actually see)

class ALIGN(Enum):
    # NOTE: The values must be the same as the how you get them. I.E. ALIGN.LEFT must have value 'left', 'LeFt', 'LEFT', etc.
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    JUSTIFIED = 'justified'
