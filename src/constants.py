from enum import Enum
import re
from collections import namedtuple as named_tuple


class Enum(str, Enum):
    """A super-class used to give methods to very enum in the application."""

    @classmethod
    def validate(cls, obj, raise_exception=True):
        """
        Validates an object and returns the matching value if it matches a value
            of the Enum and False otherwise.

        If raise_exception, then an exception will be raised if a valid value
            is not given. If it is False, then this method will just return False.
        """
        from marked_up_text import MarkedUpText
        from tools import trimmed
        val = obj
        if isinstance(obj, (str, cls)) and trimmed(obj.lower()) in cls.values():
            return trimmed(obj.lower())
        elif isinstance(obj, MarkedUpText) and trimmed(obj._text.lower()) in cls.values():
            return trimmed(obj._text.lower())

        if raise_exception:
            valid_values = ''

            for i, value in enumerate(cls.values()):
                if i > 0:
                    valid_values += ', '
                valid_values += value.lower()

            raise Exception(f'Value {val} is not a valid {cls.__class__.__name__} value. The valid values are {valid_values}.')
        else:
            return False

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
    BACKSLASH = 'BACKSLASH'          # r'\'

    # --------------------------------------
    # Ones Actually in Use by Tokenizer or Parser
    COMMA = 'COMMA'                  # r','
    OCBRACE = 'OPENING CURLY BRACE'  # r'{'
    CCBRACE = 'CLOSING CURLY BRACE'  # r'}'
    EQUAL_SIGN = 'EQUALS SIGN'       # r'='

    OPAREN = 'OPENNING PARENTHESIS'  # r'('
    CPAREN = 'CLOSING PARENTHESIS'   # r')'
    OBRACE = 'OPENING BRACE'         # r'['
    CBRACE = 'CLOSING BRACE'         # r']'

    EXEC_PYTH1 = 'PYTHON EXEC FIRST PASS'
    EVAL_PYTH1 = 'PYTHON EVAL FIRST PASS'
    EXEC_PYTH2 = 'PYTHON EXEC SECOND PASS'
    EVAL_PYTH2 = 'PYTHON EVAL SECOND PASS'

    PARAGRAPH_BREAK = 'PARAGRAPH BREAK'

    IDENTIFIER = 'IDENTIFIER'

    FILE_START = 'FILE START'
    FILE_END = 'FILE END'

    WORD = 'WORD'

    NONE_LEFT = 'NONE_LEFT' # For Parser when there are no more Tokens to parse

END_LINE_CHARS = ('\r\n', '\r', '\n', '\f') # White space that would start a new line/paragraph
NON_END_LINE_CHARS = (' ', '\t', '\v') # White space that would not start a new line/paragraph
WHITE_SPACE_CHARS = (' ', '\t', '\n', '\r', '\f', '\v') # all white space

# The relative path to the standard library
STD_LIB_FILE_NAME = '__std_lib__'
STD_DIR = './__std__/'
STD_FILE_ENDING = 'pdfo'

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
    # NOTE: the matches must start with \ because of where they are matched in
    #   the Tokenizer

    # PYTHON CODE IDENTIFIERS
    #   FIRST PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_1PASS_EXEC_START =    ['\\>', '\\1>']
    ONE_LINE_PYTH_1PASS_EXEC_END =      [*nl('<\\', '<1\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_1PASS_EXEC_START =  ['\\->', '\\1->']
    MULTI_LINE_PYTH_1PASS_EXEC_END =    [*nl('<-\\', '<-1\\')]

    #       EVAL PYTHON
    ONE_LINE_PYTH_1PASS_EVAL_START =    ['\\?>', '\\1?>']
    ONE_LINE_PYTH_1PASS_EVAL_END =      [*nl('<\\', '<?\\', '<?1\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_1PASS_EVAL_START =  ['\\1?->']
    MULTI_LINE_PYTH_1PASS_EVAL_END =    [*nl('<-\\', '<-?1\\')]

    #   SECOND PASS PYTHON
    #       EXEC PYTHON
    ONE_LINE_PYTH_2PASS_EXEC_START =    ['\\2>']
    ONE_LINE_PYTH_2PASS_EXEC_END =      [*nl('<\\', '<2\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_2PASS_EXEC_START =  ['\\2->']
    MULTI_LINE_PYTH_2PASS_EXEC_END =    [*nl('<-\\', '<-2\\')]

    #       EVAL PYTHON
    ONE_LINE_PYTH_2PASS_EVAL_START =    ['\\2?>']
    ONE_LINE_PYTH_2PASS_EVAL_END =      [*nl('<\\', '<?\\', '<?2\\'), *END_LINE_CHARS]
    MULTI_LINE_PYTH_2PASS_EVAL_START =  ['\\?->']
    MULTI_LINE_PYTH_2PASS_EVAL_END =    [*nl('<-\\', '<-?\\')]

    # COMMENT IDENTIFIERS (NOTE: The start of each one must start with a backslash because of where the matching takes place in the tokenizer)
    SINGLE_LINE_COMMENT_START        = ['\\%', '\\#']
    SINGLE_LINE_COMMENT_END          = [*nl('%\\', '#\\'), *END_LINE_CHARS]
    MULTI_LINE_COMMENT_START         = ['\\%->', '\\#->']
    MULTI_LINE_COMMENT_END           = [*nl('<-\\', '<-%\\', '<-#\\')]

del nl

#Progress Bar Constants
# NOTE: Most of these are given as defaults in the print_progress_bar function
#   located in tools.py and thus are not seen in the rest of the code.
PB_SUFFIX = 'Complete'
PB_NAME_SPACE = 20
PB_PREFIX_SPACE = 10
PB_NUM_DECS = 1 # Number of Decimals in the Percentage
PB_LEN = 30 # How long the bar should be
PB_UNFILL = '-'
PB_FILL = '='
PB_NUM_TABS = 1 # Number of tabs before the printed value


# What tabs should be when being printed to the command line
OUT_TAB = 6 * ' '


# -----------------------------------------------------------------------------
# API Constants (Constants that people compiling their pdf might actually see)

# NOTE: The values of these must be both lower case and the same as what you
#   want the user to type in to get them.

class ALIGNMENT(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    JUSTIFY = 'justify'

class SCRIPT(Enum):
    NORMAL = 'normal'
    SUPER = 'super'
    SUB = 'sub'

class STRIKE_THROUGH(Enum):
    NONE = 'none'
    SINGLE = 'single'
    DOUBLE = 'double'

class UNDERLINE(Enum):
    NONE = 'none'
    SINGLE = 'single'
    DOUBLE = 'double'
    WAVE = 'wave'
    THICK = 'thick'
    DOTTED = 'dotted'
    DASHED = 'dashed'
    DOT_DASHED = 'dot_dashed'
    DOT_DOT_DASHED = 'dot_dot_dashed'

