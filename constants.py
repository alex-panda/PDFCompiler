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
    OPAREN = 'OPENNING PARENTHESIS'  # r'('
    CPAREN = 'CLOSING PARENTHESIS'   # r')'
    OBRACE = 'OPENING BRACE'         # r'['
    CBRACE = 'CLOSING BRACE'         # r']'
    BACKSLASH = 'BACKSLASH'          # r'\'

    # --------------------------------------
    # Ones Actually in Use by Tokenizer or Other
    OCBRACE = 'OPENING CURLY BRACE'  # r'{'
    CCBRACE = 'CLOSING CURLY BRACE'  # r'}'
    EQUAL_SIGN = 'EQUALS SIGN'       # r'='

    PASS1EXEC = 'PYTHON FIRST PASS EXEC'
    PASS1EVAL = 'PYTHON FIRST PASS EVAL'
    PASS2EXEC = 'PYTHON SECOND PASS EXEC'
    PASS2EVAL = 'PYTHON SECOND PASS EVAL'

    PARAGRAPH_BREAK = 'PARAGRAPH BREAK'

    CMND_NAME = 'COMMAND NAME'

    FILE_START = 'FILE START'
    FILE_END = 'FILE END'

    WORD = 'WORD'

    NONE_LEFT = 'NONE_LEFT' # For Parser when there are no more Tokens to parse

END_LINE_CHARS = ('\r', '\n', '\f') # White space that would start a new line/paragraph
NON_END_LINE_WHITE_SPACE = (' ', '\t', '\v') # White space that would not start a new line/paragraph
WHITE_SPACE = (' ', '\t', '\n', '\r', '\f', '\v') # all white space

def nl(*args):
    """
    Adds newlines to the given terms and returns them. This is so that they will
        eat the newlines after the given args so that the new lines will not
        affect the rest of the code (would mainly cause paragraph breaks).
    """
    new_terms = []
    for term in args:
        #for end in END_LINE_CHARS:
        #    new_terms.append(term + end)
        new_terms.append(term)

    return new_terms

class TT_M:
    """
    What the more complex tokens should each match.
    """
    # PYTHON CODE IDENTIFIERS (NOTE: The start of each one must start with a backslash because of where the matching takes place in the tokenizer)
    #   FIRST PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_1PASS_EXEC_START   = ['\\1>']
    ONE_LINE_PYTH_1PASS_EXEC_END     = [*nl('<\\', '<1\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_1PASS_EXEC_START = ['\\1->']
    MULTI_LINE_PYTH_1PASS_EXEC_END   = [*nl('<-\\', '<-1\\')]

    #       EVAL PYTHON
    ONE_LINE_PYTH_1PASS_EVAL_START   = ['\\?1>']
    ONE_LINE_PYTH_1PASS_EVAL_END     = [*nl('<\\', '<?\\', '<1?\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_1PASS_EVAL_START = ['\\?1->']
    MULTI_LINE_PYTH_1PASS_EVAL_END   = [*nl('<-\\', '<-1?\\')]

    #   SECOND PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_2PASS_EXEC_START   = ['\\>', '\\2>']
    ONE_LINE_PYTH_2PASS_EXEC_END     = [*nl('<\\', '<2\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_2PASS_EXEC_START = ['\\->', '\\2->']
    MULTI_LINE_PYTH_2PASS_EXEC_END   = [*nl('<-\\', '<-2\\')]

    #       EVAL PYTHON
    ONE_LINE_PYTH_2PASS_EVAL_START   = ['\\?>', '\\?2>']
    ONE_LINE_PYTH_2PASS_EVAL_END     = [*nl('<\\', '<?\\', '<2?\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_2PASS_EVAL_START = ['\\?->', '\\?2->']
    MULTI_LINE_PYTH_2PASS_EVAL_END   = [*nl('<-\\', '<-?\\')]

    # COMMENT IDENTIFIERS (NOTE: The start of each one must start with a backslash because of where the matching takes place in the tokenizer)
    SINGLE_LINE_COMMENT_START        = ['\\%', '\\#']
    SINGLE_LINE_COMMENT_END          = [*nl('%\\', '#\\'), *END_LINE_CHARS]
    MULTI_LINE_COMMENT_START         = ['\\%->', '\\#->']
    MULTI_LINE_COMMENT_END           = [*nl('<-%\\', '<-#\\')]

del nl

# -----------------------------------------------------------------------------
# API Constants (Constants that people compiling their pdf might actually see)

class ALIGN(Enum):
    # NOTE: The values must be the same as the how you get them. I.E. ALIGN.LEFT must have value 'left', 'LeFt', 'LEFT', etc.
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    JUSTIFIED = 'justified'

