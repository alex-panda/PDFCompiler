"""
A module providing a ToolBox for the users of the compiler to use.
"""
from collections import namedtuple as named_tuple
from decimal import Decimal

from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes as pagesizes

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
    def color_for_str(color_name_str):
        trimmed = trimmed(color_name_str)
        lowered = trimmed.lower()

        if lowered in _colors_dict:
            return _colors_dict[lowered]

        raise Exception(f'{color_name_str} is not a valid name for a color.')

    @staticmethod
    def page_size_for_str(page_size_str):
        return _page_sizes_dict[trimmed(page_size_str).upper()]
        raise Exception(f'{page_size_str} is not a valid page size.')

    @staticmethod
    def unit_for_str(unit_name_str):
        return _units_dict[trimmed(unit_name_str).lower()]
        raise Exception(f'{unit_name_str} is not a valid unit.')

    @staticmethod
    def alignment_for_str(alignment_name):
        return ALIGNMENT.validate(alignment_name)

    @staticmethod
    def script_for_str(script_name):
        return SCRIPT.validate(script_name)

    @staticmethod
    def strike_through_for_str(script_name):
        return STRIKE_THROUGH.validate(script_name)

    @staticmethod
    def underline_for_str(script_name):
        return UNDERLINE.validate(script_name)

    @staticmethod
    def length_for_str(length_as_str):
        """
        Takes a length as a string, such as '4pica' or '4mm' and converts it
            into a Decimal of the specified size.
        """
        return assure_decimal(toLength(length_as_str))

    # ---------------------------------
    # Other Helpful Methods

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
