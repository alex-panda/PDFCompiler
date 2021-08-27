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
    """
    A family of fonts i.e. a group of fonts that, together, allow you to create
        the affect of bolding or italisizing text.

    A FontFamily only holds the names of the fonts that make it up. If you want
        more information on the Font then you should look up the font in the
        FONTS dict
    """
    __slots__ = ['name', 'norm', 'bold', 'italics', 'bold_italics', 'fallback_font']
    def __init__(self, name, norm_font_name:str, bold_font_name:str, italics_font_name:str, bold_italics_font_name:str):
        self.name = name
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

    def fonts(self):
        """
        Returns a list of the fonts of this font family in [norm, bold, italics,
            bold_italics] order
        """
        return [self.font(bold, italics) \
                for bold, italics in \
                ((False, False), (True, False), (False, True), (True, True))]

    def __repr__(self):
        return f'FontFamily(norm={self.norm}, bold={self.bold}, italics={self.italics}, bold_italics={self.bold_italics})'

class Font:
    """
    Holds all the information pertaining to a font. Font Families hold only the
        names of a Font, not Font objects.
    """
    __slots__ = ['family_name', 'full_name', 'bold', 'italics', 'file_path']
    def __init__(self, family_name:str, full_name:str, bold:bool, italics:bool, file_path:str=None):
        self.family_name = family_name
        self.full_name = full_name
        self.bold = bold
        self.italics = italics
        self.file_path = file_path

    def __repr__(self):
        return f'Font(family={self.family_name}, full_name={self.full_name}, bold={self.bold}, italics={self.italics})'

# Dict of all found FontFamilies
FONT_FAMILIES = {
    'Times':        FontFamily('Times', 'Times', 'TimesB', 'TimesI', 'TimesBI'),
    'Courier':      FontFamily('Courier', 'Courier', 'CourierB', 'CourierI', 'CourierBI'),
    'Helvetica':    FontFamily('Helvetica', 'Helvetica', 'HelveticaB', 'HelveticaI', 'HelveticaBI'),
    'Symbol':       FontFamily('Symbol', 'Symbol', 'Symbol', 'Symbol', 'Symbol'),
    'Zapfdingbats': FontFamily('Zapfdingbats', 'Zapfdingbats', 'Zapfdingbats', 'Zapfdingbats', 'Zapfdingbats')
}

# Dict of all found Fonts with their keys being their full names. These are the
#   fonts that make up the font families
FONTS = {
    #Font('Times', 'Times', False, False, None),
}

# Fonts that are standard to all PDFs and do not have to be somewhere on the
#   computer's filesystem
STANDARD_FONTS = set([
        'Times',     'TimesB',     'TimesI',     'TimesBI',
        'Courier',   'CourierB',   'CourierI',   'CourierBI',
        'Helvetica', 'HelveticaB', 'HelveticaI', 'HelveticaBI',
        'Symbol',    'Zapfdingbats'])

# A dictionary of fonts that should be imported with
#   font_name: font_file_path      pairs
FONTS_TO_IMPORT = {}
FONTS_IMPORTED_TO_GLOBAL_FPDF = set()
DIRS_CHECKED_FOR_FONTS = set()

# Used to calculate the widths of strings because you need a FPDF object to do
#   that
from fpdf import FPDF
GLOBAL_FPDF =  FPDF(unit='pt', font_cache_dir=None)

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

    "C0":  (917  * UNIT.MM, 1297 * UNIT.MM),
    "C1":  (648  * UNIT.MM, 917  * UNIT.MM),
    "C2":  (458  * UNIT.MM, 648  * UNIT.MM),
    "C3":  (324  * UNIT.MM, 458  * UNIT.MM),
    "C4":  (229  * UNIT.MM, 324  * UNIT.MM),
    "C5":  (162  * UNIT.MM, 229  * UNIT.MM),
    "C6":  (114  * UNIT.MM, 162  * UNIT.MM),
    "C7":  (81   * UNIT.MM, 114  * UNIT.MM),
    "C8":  (57   * UNIT.MM, 81   * UNIT.MM),
    "C9":  (40   * UNIT.MM, 57   * UNIT.MM),
    "C10": (28   * UNIT.MM, 40   * UNIT.MM),

    "D0":  (771  * UNIT.MM, 1090 * UNIT.MM),
    "D1":  (545  * UNIT.MM, 771  * UNIT.MM),
    "D2":  (385  * UNIT.MM, 545  * UNIT.MM),
    "D3":  (272  * UNIT.MM, 385  * UNIT.MM),
    "D4":  (192  * UNIT.MM, 272  * UNIT.MM),
    "D5":  (136  * UNIT.MM, 192  * UNIT.MM),
    "D6":  (96   * UNIT.MM, 136  * UNIT.MM),
    "D7":  (68   * UNIT.MM, 96   * UNIT.MM),
    "D8":  (48   * UNIT.MM, 68   * UNIT.MM),
}


# For now, COLORS just contains all the standard Hexidecimal colors in hex form
COLORS = {
    'ALICEBLUE': '#F0F8FF',
    'ANTIQUEWHITE': '#FAEBD7',
    'AQUA': '#00FFFF',
    'AQUAMARINE': '#7FFFD4',
    'AZURE': '#F0FFFF',
    'BEIGE': '#F5F5DC',
    'BISQUE': '#FFE4C4',
    'BLACK': '#000000',
    'BLANCHEDALMOND': '#FFEBCD',
    'BLUE': '#0000FF',
    'BLUEVIOLET': '#8A2BE2',
    'BROWN': '#A52A2A',
    'BURLYWOOD': '#DEB887',
    'CADETBLUE': '#5F9EA0',
    'CHARTREUSE': '#7FFF00',
    'CHOCOLATE': '#D2691E',
    'CORAL': '#FF7F50',
    'CORNFLOWERBLUE': '#6495ED',
    'CORNSILK': '#FFF8DC',
    'CRIMSON': '#DC143C',
    'CYAN': '#00FFFF',
    'DARKBLUE': '#00008B',
    'DARKCYAN': '#008B8B',
    'DARKGOLDENROD': '#B8860B',
    'DARKGRAY': '#A9A9A9',
    'DARKGREY': '#A9A9A9',
    'DARKGREEN': '#006400',
    'DARKKHAKI': '#BDB76B',
    'DARKMAGENTA': '#8B008B',
    'DARKOLIVEGREEN': '#556B2F',
    'DARKORANGE': '#FF8C00',
    'DARKORCHID': '#9932CC',
    'DARKRED': '#8B0000',
    'DARKSALMON': '#E9967A',
    'DARKSEAGREEN': '#8FBC8F',
    'DARKSLATEBLUE': '#483D8B',
    'DARKSLATEGRAY': '#2F4F4F',
    'DARKSLATEGREY': '#2F4F4F',
    'DARKTURQUOISE': '#00CED1',
    'DARKVIOLET': '#9400D3',
    'DEEPPINK': '#FF1493',
    'DEEPSKYBLUE': '#00BFFF',
    'DIMGRAY': '#696969',
    'DIMGREY': '#696969',
    'DODGERBLUE': '#1E90FF',
    'FIREBRICK': '#B22222',
    'FLORALWHITE': '#FFFAF0',
    'FORESTGREEN': '#228B22',
    'FUCHSIA': '#FF00FF',
    'GAINSBORO': '#DCDCDC',
    'GHOSTWHITE': '#F8F8FF',
    'GOLD': '#FFD700',
    'GOLDENROD': '#DAA520',
    'GRAY': '#808080',
    'GREY': '#808080',
    'GREEN': '#008000',
    'GREENYELLOW': '#ADFF2F',
    'HONEYDEW': '#F0FFF0',
    'HOTPINK': '#FF69B4',
    'INDIANRED': '#CD5C5C',
    'INDIGO': '#4B0082',
    'IVORY': '#FFFFF0',
    'KHAKI': '#F0E68C',
    'LAVENDER': '#E6E6FA',
    'LAVENDERBLUSH': '#FFF0F5',
    'LAWNGREEN': '#7CFC00',
    'LEMONCHIFFON': '#FFFACD',
    'LIGHTBLUE': '#ADD8E6',
    'LIGHTCORAL': '#F08080',
    'LIGHTCYAN': '#E0FFFF',
    'LIGHTGOLDENRODYELLOW': '#FAFAD2',
    'LIGHTGRAY': '#D3D3D3',
    'LIGHTGREY': '#D3D3D3',
    'LIGHTGREEN': '#90EE90',
    'LIGHTPINK': '#FFB6C1',
    'LIGHTSALMON': '#FFA07A',
    'LIGHTSEAGREEN': '#20B2AA',
    'LIGHTSKYBLUE': '#87CEFA',
    'LIGHTSLATEGRAY': '#778899',
    'LIGHTSLATEGREY': '#778899',
    'LIGHTSTEELBLUE': '#B0C4DE',
    'LIGHTYELLOW': '#FFFFE0',
    'LIME': '#00FF00',
    'LIMEGREEN': '#32CD32',
    'LINEN': '#FAF0E6',
    'MAGENTA': '#FF00FF',
    'MAROON': '#800000',
    'MEDIUMAQUAMARINE': '#66CDAA',
    'MEDIUMBLUE': '#0000CD',
    'MEDIUMORCHID': '#BA55D3',
    'MEDIUMPURPLE': '#9370DB',
    'MEDIUMSEAGREEN': '#3CB371',
    'MEDIUMSLATEBLUE': '#7B68EE',
    'MEDIUMSPRINGGREEN': '#00FA9A',
    'MEDIUMTURQUOISE': '#48D1CC',
    'MEDIUMVIOLETRED': '#C71585',
    'MIDNIGHTBLUE': '#191970',
    'MINTCREAM': '#F5FFFA',
    'MISTYROSE': '#FFE4E1',
    'MOCCASIN': '#FFE4B5',
    'NAVAJOWHITE': '#FFDEAD',
    'NAVY': '#000080',
    'OLDLACE': '#FDF5E6',
    'OLIVE': '#808000',
    'OLIVEDRAB': '#6B8E23',
    'ORANGE': '#FFA500',
    'ORANGERED': '#FF4500',
    'ORCHID': '#DA70D6',
    'PALEGOLDENROD': '#EEE8AA',
    'PALEGREEN': '#98FB98',
    'PALETURQUOISE': '#AFEEEE',
    'PALEVIOLETRED': '#DB7093',
    'PAPAYAWHIP': '#FFEFD5',
    'PEACHPUFF': '#FFDAB9',
    'PERU': '#CD853F',
    'PINK': '#FFC0CB',
    'PLUM': '#DDA0DD',
    'POWDERBLUE': '#B0E0E6',
    'PURPLE': '#800080',
    'REBECCAPURPLE': '#663399',
    'RED': '#FF0000',
    'ROSYBROWN': '#BC8F8F',
    'ROYALBLUE': '#4169E1',
    'SADDLEBROWN': '#8B4513',
    'SALMON': '#FA8072',
    'SANDYBROWN': '#F4A460',
    'SEAGREEN': '#2E8B57',
    'SEASHELL': '#FFF5EE',
    'SIENNA': '#A0522D',
    'SILVER': '#C0C0C0',
    'SKYBLUE': '#87CEEB',
    'SLATEBLUE': '#6A5ACD',
    'SLATEGRAY': '#708090',
    'SLATEGREY': '#708090',
    'SNOW': '#FFFAFA',
    'SPRINGGREEN': '#00FF7F',
    'STEELBLUE': '#4682B4',
    'TAN': '#D2B48C',
    'TEAL': '#008080',
    'THISTLE': '#D8BFD8',
    'TOMATO': '#FF6347',
    'TURQUOISE': '#40E0D0',
    'VIOLET': '#EE82EE',
    'WHEAT': '#F5DEB3',
    'WHITE': '#FFFFFF',
    'WHITESMOKE': '#F5F5F5',
    'YELLOW': '#FFFF00',
    'YELLOWGREEN': '#9ACD32',
}

import os.path as path

# The default paths to look at for fonts on the system
FONT_SEARCH_PATHS = set([
    # Places for T1 type fonts
    'c:/Program Files/Adobe/Acrobat 9.0/Resource/Font',
    'c:/Program Files/Adobe/Acrobat 8.0/Resource/Font',
    'c:/Program Files/Adobe/Acrobat 7.0/Resource/Font',
    'c:/Program Files/Adobe/Acrobat 6.0/Resource/Font',
    'c:/Program Files/Adobe/Acrobat 5.0/Resource/Font',
    'c:/Program Files/Adobe/Acrobat 4.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 9.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 8.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 7.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 6.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 5.0/Resource/Font',
    'c:/Program Files (x86)/Adobe/Acrobat 4.0/Resource/Font',
    'C:/Program Files (x86)/Adobe/Acrobat Reader DC/Resource/Font',
    '/usr/lib/Acrobat9/Resource/Font',
    '/usr/lib/Acrobat8/Resource/Font',
    '/usr/lib/Acrobat7/Resource/Font',
    '/usr/lib/Acrobat6/Resource/Font',
    '/usr/lib/Acrobat5/Resource/Font',
    '/usr/lib/Acrobat4/Resource/Font',
    '/usr/local/Acrobat9/Resource/Font',
    '/usr/local/Acrobat8/Resource/Font',
    '/usr/local/Acrobat7/Resource/Font',
    '/usr/local/Acrobat6/Resource/Font',
    '/usr/local/Acrobat5/Resource/Font',
    '/usr/local/Acrobat4/Resource/Font',
    '/usr/share/fonts/default/Type1',
    '~/fonts',
    '~/.fonts',
    '~/.local/share/fonts',

    # Places for TT fonts
    'c:/winnt/fonts',
    'c:/windows/fonts',
    '/usr/lib/X11/fonts/TrueType/',
    '/usr/share/fonts/truetype',
    '/usr/share/fonts',
    '/usr/share/fonts/dejavu',
    '~/fonts',
    '~/.fonts',
    '~/.local/share/fonts',

    # The path to the fonts that come with the compiler
    f'{path.normpath(path.join(path.dirname(__file__), "Fonts"))}',

    '~/Library/Fonts',
    '/Library/Fonts',
    '/Network/Library/Fonts',
    '/System/Library/Fonts',

    # Places for CMAP fonts
    '/usr/lib/Acrobat9/Resource/CMap',
    '/usr/lib/Acrobat8/Resource/CMap',
    '/usr/lib/Acrobat7/Resource/CMap',
    '/usr/lib/Acrobat6/Resource/CMap',
    '/usr/lib/Acrobat5/Resource/CMap',
    '/usr/lib/Acrobat4/Resource/CMap',
    '/usr/local/Acrobat9/Resource/CMap',
    '/usr/local/Acrobat8/Resource/CMap',
    '/usr/local/Acrobat7/Resource/CMap',
    '/usr/local/Acrobat6/Resource/CMap',
    '/usr/local/Acrobat5/Resource/CMap',
    '/usr/local/Acrobat4/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 9.0/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 8.0/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 7.0/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 6.0/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 5.0/Resource/CMap',
    'C:/Program Files/Adobe/Acrobat 4.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 9.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 8.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 7.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 6.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 5.0/Resource/CMap',
    'C:/Program Files (x86)/Adobe/Acrobat 4.0/Resource/CMap',
    '~/fonts/CMap',
    '~/.fonts/CMap',
    '~/.local/share/fonts/CMap',
    ]
)
