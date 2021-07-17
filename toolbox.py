"""
A module providing a ToolBox for the users of the compiler to use.
"""
from collections import namedtuple as named_tuple
from decimal import Decimal

from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes as pagesizes

from tools import assure_decimal, is_escaped, is_escaping, exec_python, eval_python, string_with_arrows

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

class ToolBox:
    """
    A toolbox of various useful things like Constants and whatnot
    """
    def __init__(self):
        page_sizes = [getattr(pagesizes, page_size) for page_size in PAGE_SIZES]
        self._page_sizes = named_tuple('PageSizes', PAGE_SIZES)(*[(Decimal(h), Decimal(w)) for h, w in page_sizes])
        self._page_sizes_dict = {page_size:getattr(self._page_sizes, page_size) for page_size in PAGE_SIZES}

        self._units = named_tuple('Units', UNITS)(*[Decimal(getattr(units, unit)) for unit in UNITS])
        self._units_dict = {unit:getattr(self._units, unit) for unit in UNITS}

        self._colors = named_tuple('Units', COLORS)(*[getattr(colors, color) for color in COLORS])
        self._colors_dict = {color:getattr(colors, color) for color in COLORS}

        self._alignments = named_tuple('Units', [val.lower() for val in ALIGN.values()])(*[getattr(ALIGN, alignment.upper()) for alignment in ALIGN.values()])
        self._alignments_dict = {alignment.lower():getattr(self._alignments, alignment.lower()) for alignment in ALIGN.values()}

    def colors(self):
        return self._colors

    def color_by_name(self, color_name_str):
        return self._colors_dict[color_name_str.lower()]

    def page_sizes(self):
        return self._page_sizes

    def page_size_by_name(self, page_size_str):
        return self._page_sizes_dict[page_size_str.upper()]

    def units(self):
        return self._units

    def units_by_name(self, unit_name_str):
        return self._units_dict[unit_name_str.lower()]

    def alignments(self):
        self._alignments

    def alignments_by_name(self, alignment_name):
        return self._alignments_dict[alignment_name.lower()]

    def str_to_length(self, length_as_str):
        """
        Takes a length as a string, such as '4pica' or '4mm' and converts it
            into a Decimal of the specified size.
        """
        return assure_decimal(toLength(length_as_str))

    def assure_landscape(self, page_size):
        """
        Returns a tuple of the given page_size in landscape orientation, even
            if it is already/given in landscape orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.landscape(page_size)
        return (assure_decimal(h), assure_decimal(w))

    def assure_portrait(self, page_size):
        """
        Returns a tuple of the given page_size in portrait orientation, even
            if it is already/given in portrait orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.portrait(page_size)
        return (assure_decimal(h), assure_decimal(w))
