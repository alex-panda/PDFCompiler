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
        if isinstance(obj, (str, cls)) and (trimmed(obj.lower()) in cls.values()):
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

class FontFamily:
    __slots__ = ['norm', 'bold', 'italics', 'bold_italics']
    def __init__(self, norm_font_name, bold_font_name, italics_font_name, bold_italics_font_name):
        self.norm = norm_font_name
        self.bold = bold_font_name
        self.italics = italics_font_name
        self.bold_italics = bold_italics_font_name

    def font(self, bold:bool, italics:bool):
        """
        Returns the font name for the font that corresponds to the given
            combination of bold and italics.
        """
        if bold and italics:
            return self.bold_italics
        elif bold:
            return self.bold
        elif italics:
            return self.italics
        else:
            return self.norm

FONT_FAMILIES = {
    'Times': FontFamily('Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic'),
    'Courier': FontFamily('Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique'),
    'Helvetica': FontFamily('Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique'),
    'Symbol': FontFamily('Symbol', 'Symbol', 'Symbol', 'Symbol'),
    'ZapfDingbats': FontFamily('ZapfDingbats', 'ZapfDingbats', 'ZapfDingbats', 'ZapfDingbats')
}

# The fonts found on the operating system are not always named the same as they
# were asked for by the user. This Dictionary will save the name the user asked
# for with the name of the actual font on the system in key:value pairs.
# This dictionary is specifically for the fonts imported that are not in a font
# family and are, instead, standalone fonts
FONT_NAMES = {}

# Registered font names because the ones registered by reportlab are sorted
#   when you try to retrieve them which is causing errors
REGISTERED_FONTS = set(['Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic',
        'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique',
        'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique',
        'Symbol', 'ZapfDingbats'])

# -----------------------------------------------------------------------------
# API Constants (Constants that people compiling their pdf might actually see)

# NOTE: The values of these must be both lower case and the same as what you
#   want the user to type in to get them.

class ALIGNMENT(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    JUSTIFY = 'justify'

class STRIKE_THROUGH(Enum):
    NONE = 'none'
    SINGLE = 'single'
    DOUBLE = 'double'

class UNDERLINE(Enum):
    NONE = 'none'
    SINGLE = 'single'
    DOUBLE = 'double'
    THICK = 'thick'
    WAVE = 'wave'
    DOTTED = 'dotted'
    DASHED = 'dashed'
    DOT_DASHED = 'dot dashed'
    DOT_DOT_DASHED = 'dot dot dashed'

class UNIT:
    INCH = 72.0
    CM = INCH / 2.54
    MM = CM * 0.1
    PICA = 12.0

# Paper sizes from https://en.wikipedia.org/wiki/Paper_size
PAGE_SIZES_DICT = {
    "LETTER":          (8.5 * UNIT.INCH, 11 * UNIT.INCH),
    "LEGAL":           (8.5 * UNIT.INCH, 14 * UNIT.INCH),
    "ELEVENSEVENTEEN": (11  * UNIT.INCH, 17 * UNIT.INCH),

    "JUNIOR_LEGAL": (5   * UNIT.INCH, 8    * UNIT.INCH),
    "HALF_LETTER":  (5.5 * UNIT.INCH, 8    * UNIT.INCH),
    "GOV_LETTER":   (8   * UNIT.INCH, 10.5 * UNIT.INCH),
    "GOV_LEGAL":    (8.5 * UNIT.INCH, 13   * UNIT.INCH),
    "TABLOID":      (11  * UNIT.INCH, 17   * UNIT.INCH),
    "LEDGER":       (17  * UNIT.INCH, 11   * UNIT.INCH),

    "A0":  (841  * UNIT.MM, 1189 * UNIT.MM),
    "A1":  (594  * UNIT.MM, 841  * UNIT.MM),
    "A2":  (420  * UNIT.MM, 594  * UNIT.MM),
    "A3":  (297  * UNIT.MM, 420  * UNIT.MM),
    "A4":  (210  * UNIT.MM, 297  * UNIT.MM),
    "A5":  (148  * UNIT.MM, 210  * UNIT.MM),
    "A6":  (105  * UNIT.MM, 148  * UNIT.MM),
    "A7":  (74   * UNIT.MM, 105  * UNIT.MM),
    "A8":  (52   * UNIT.MM, 74   * UNIT.MM),
    "A9":  (37   * UNIT.MM, 52   * UNIT.MM),
    "A10": (26   * UNIT.MM, 37   * UNIT.MM),
    "A11": (18   * UNIT.MM, 26   * UNIT.MM),
    "A12": (13   * UNIT.MM, 18   * UNIT.MM),
    "A13": (9    * UNIT.MM, 13   * UNIT.MM),

    "B0":  (1000 * UNIT.MM, 1414 * UNIT.MM),
    "B1":  (707  * UNIT.MM, 1000 * UNIT.MM),
    "B2":  (500  * UNIT.MM, 707  * UNIT.MM),
    "B3":  (353  * UNIT.MM, 500  * UNIT.MM),
    "B4":  (250  * UNIT.MM, 353  * UNIT.MM),
    "B5":  (176  * UNIT.MM, 250  * UNIT.MM),
    "B6":  (125  * UNIT.MM, 176  * UNIT.MM),
    "B7":  (88   * UNIT.MM, 125  * UNIT.MM),
    "B8":  (62   * UNIT.MM, 88   * UNIT.MM),
    "B9":  (44   * UNIT.MM, 62   * UNIT.MM),
    "B10": (31   * UNIT.MM, 44   * UNIT.MM),
    "B11": (22   * UNIT.MM, 31   * UNIT.MM),
    "B12": (15   * UNIT.MM, 22   * UNIT.MM),
    "B13": (11   * UNIT.MM, 15   * UNIT.MM),

    "C0":  (917 * UNIT.MM, 1297 * UNIT.MM),
    "C1":  (648 * UNIT.MM, 917  * UNIT.MM),
    "C2":  (458 * UNIT.MM, 648  * UNIT.MM),
    "C3":  (324 * UNIT.MM, 458  * UNIT.MM),
    "C4":  (229 * UNIT.MM, 324  * UNIT.MM),
    "C5":  (162 * UNIT.MM, 229  * UNIT.MM),
    "C6":  (114 * UNIT.MM, 162  * UNIT.MM),
    "C7":  (81  * UNIT.MM, 114  * UNIT.MM),
    "C8":  (57  * UNIT.MM, 81   * UNIT.MM),
    "C9":  (40  * UNIT.MM, 57   * UNIT.MM),
    "C10": (28  * UNIT.MM, 40   * UNIT.MM),

    "D0":  (771 * UNIT.MM, 1090 * UNIT.MM),
    "D1":  (545 * UNIT.MM, 771  * UNIT.MM),
    "D2":  (385 * UNIT.MM, 545  * UNIT.MM),
    "D3":  (272 * UNIT.MM, 385  * UNIT.MM),
    "D4":  (192 * UNIT.MM, 272  * UNIT.MM),
    "D5":  (136 * UNIT.MM, 192  * UNIT.MM),
    "D6":  (96  * UNIT.MM, 136  * UNIT.MM),
    "D7":  (68  * UNIT.MM, 96   * UNIT.MM),
    "D8":  (48  * UNIT.MM, 68   * UNIT.MM),
}

def landscape(page_size):
    """
    Makes sure that no matter what page size is given, it is returned in
        landscape format, whether it was already in landscap or not.
    """
    a, b = page_size
    if a < b:
        return (b, a)
    else:
        return (a, b)

def portrait(page_size):
    """
    The Page size returned is the given page size in portrait orientation, even
        if it was already in portrait orientation.
    """
    a, b = page_size
    if a >= b:
        return (b, a)
    else:
        return (a, b)
