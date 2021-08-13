"""
A module providing a ToolBox for the users of the compiler to use.
"""
import os
from collections import namedtuple as named_tuple
from decimal import Decimal

from reportlab import rl_config
from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes
from reportlab.pdfbase.pdfmetrics import getFont, getRegisteredFontNames, standardFonts, registerFont
from reportlab.pdfbase.ttfonts import TTFont

from tools import assure_decimal, trimmed
from constants import ALIGNMENT, SCRIPT, STRIKE_THROUGH, UNDERLINE

PAGE_SIZES = ( \
        'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10',
        'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10',
        'C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10',
        'LETTER', 'LEGAL', 'ELEVENSEVENTEEN', 'JUNIOR_LEGAL', 'HALF_LETTER',
        'GOV_LETTER', 'GOV_LEGAL', 'TABLOID', 'LEDGER'
    )

UNITS = ('inch', 'cm', 'mm', 'pica')

COLORS = ('transparent', 'aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure',
'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 'blueviolet', 'brown',
'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan', 'darkgoldenrod',
'darkgray', 'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen',
'darkorange', 'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue',
'darkslategray', 'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink',
'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite',
'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray',
'grey', 'green', 'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo',
'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon',
'lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgreen',
'lightgrey', 'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue',
'lightslategray', 'lightslategrey', 'lightsteelblue', 'lightyellow', 'lime',
'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue',
'mediumorchid', 'mediumpurple', 'mediumseagreen', 'mediumslateblue',
'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue',
'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace',
'olive', 'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod',
'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff',
'peru', 'pink', 'plum', 'powderblue', 'purple', 'red', 'rosybrown', 'royalblue',
'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue',
'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'white', 'whitesmoke',
'yellow', 'yellowgreen', 'fidblue', 'fidred', 'fidlightblue')

_page_sizes = [getattr(pagesizes, page_size) for page_size in PAGE_SIZES]
_page_sizes = named_tuple('PageSizes', PAGE_SIZES)(*[(Decimal(h), Decimal(w)) for h, w in _page_sizes])
_page_sizes_dict = {page_size:getattr(_page_sizes, page_size) for page_size in PAGE_SIZES}

_units = named_tuple('Units', UNITS)(*[Decimal(getattr(units, unit)) for unit in UNITS])
_units_dict = {unit:getattr(units, unit) for unit in UNITS}

_colors = named_tuple('Colors', COLORS)(*[getattr(colors, color) for color in COLORS])
_colors_dict = {color:getattr(colors, color) for color in COLORS}

class ToolBox:
    """
    A toolbox of various useful things like Constants and whatnot
    """
    # ---------------------------------
    # Constants made available for coders coding in python in their pdfo files

    @staticmethod
    def colors():
        return _colors

    @staticmethod
    def page_sizes():
        return _page_sizes

    @staticmethod
    def units():
        return _units

    @staticmethod
    def alignment():
        return ALIGNMENT

    @staticmethod
    def script():
        return SCRIPT

    @staticmethod
    def strike_through():
        return STRIKE_THROUGH

    @staticmethod
    def underline():
        return UNDERLINE

    # ---------------------------------
    # Methods that allow a standard way for users to get constants from commands

    @staticmethod
    def color_from_str(color_name_str):
        trimmed = trimmed(color_name_str)
        lowered = trimmed.lower()

        if lowered in _colors_dict:
            return _colors_dict[lowered]

        raise AssertionError(f'{color_name_str} is not a valid name for a color.')

    @staticmethod
    def page_size_from_str(page_size_str):
        return _page_sizes_dict[trimmed(page_size_str).upper()]
        raise AssertionError(f'{page_size_str} is not a valid page size.')

    @staticmethod
    def unit_from_str(unit_name_str):
        return _units_dict[trimmed(unit_name_str).lower()]
        raise AssertionError(f'{unit_name_str} is not a valid unit.')

    @staticmethod
    def alignment_from_str(alignment_name):
        return ALIGNMENT.validate(alignment_name)

    @staticmethod
    def script_from_str(script_name):
        return SCRIPT.validate(script_name)

    @staticmethod
    def strike_through_from_str(script_name):
        return STRIKE_THROUGH.validate(script_name)

    @staticmethod
    def underline_from_str(script_name):
        return UNDERLINE.validate(script_name)

    @staticmethod
    def length_from_str(length_as_str):
        """
        Takes a length as a string, such as '4pica' or '4mm' and converts it
            into a Decimal of the specified size.
        """
        return assure_decimal(toLength(length_as_str))

    # ---------------------------------
    # Other Helpful Methods

    @staticmethod
    def validate_font(font_name, return_false=False):
        """
        Raises an assertion error by default and returns False if return_false is True
            if the given font_name is not available/has not yet been registered.

        Returns True if the font is available.
        """
        getFont(font_name)

    @staticmethod
    def standard_fonts():
        return standardFonts()

    @staticmethod
    def registered_fonts():
        """
        Returns a list of all registered fonts i.e. every font name that can be
            currently used. If you want more, then you need to register the new
            font.

        returns: a list of strings representing font names
        """
        return getRegisteredFontNames()

    @staticmethod
    def assure_landscape(page_size):
        """
        Returns a tuple of the given page_size in landscape orientation, even
            if it is already/given in landscape orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.landscape(page_size)
        return (assure_decimal(h), assure_decimal(w))

    @staticmethod
    def assure_portrait(page_size):
        """
        Returns a tuple of the given page_size in portrait orientation, even
            if it is already/given in portrait orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.portrait(page_size)
        return (assure_decimal(h), assure_decimal(w))

    @staticmethod
    def string_size(string, text_info):
        """
        Returns the (width, height) of the given string based on the given
            text_info object.
        """
        from reportlab.pdfbase.pdfmetrics import stringWidth

        font_name = text_info.font_name()
        font_size = text_info.font_size()

        assert isinstance(font_name, str), f'The font_name of the given text_info must be of type str, not {font_name}'
        assert isinstance(font_size, (int, float, Decimal)), f'The font_size of the given text_info must be of type int, float, or Decimal, not {font_name}'

        return stringWidth(string, font_name, font_size), font_size

