"""
A module providing a ToolBox for the users of the compiler to use.
"""
import os
from collections import namedtuple as named_tuple
from decimal import Decimal

from reportlab import rl_config
from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes
from reportlab.pdfbase.pdfmetrics import getFont, getRegisteredFontNames, standardFonts, registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fontfinder import FontFinder

from markup import Markup, MarkupStart, MarkupEnd
from tools import assure_decimal, trimmed, assert_instance, assert_subclass
from constants import ALIGNMENT as _ALIGNMENT, STRIKE_THROUGH as _STRIKE_THROUGH, UNDERLINE as _UNDERLINE, FONT_FAMILIES, FONT_NAMES, FontFamily, REGISTERED_FONTS

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

_sys_font_search_paths = set(rl_config.TTFSearchPath)

def _font_from_font_finder(font_finder, font_name, bold_italics_states=((False, False), (True, False), (False, True), (True, True))):
    """
    Tries to get the font with the given font_name from the given font_finder.
        If the font was found, a Font object is returned. Otherwise, None is returned.
    """
    font_name = bytes(font_name, encoding='utf-8')
    fonts_found = []
    for bold_italics in bold_italics_states:
        try:
            font = font_finder.getFont(font_name, *bold_italics)
            fonts_found.append(font)
        except KeyError:
            fonts_found.append(None)

    # Figure out how many fonts were actually found
    font_cnt = 0
    first_font = None
    for font in fonts_found:
        if font is not None:
            font_cnt += 1

            if first_font is None:
                first_font = font

    if font_cnt == 0:
        return None
    elif font_cnt == 1:
        # A single font was in the file
        return first_font
    else:
        # a font family was in the file
        return fonts_found

class ToolBox:
    """
    A toolbox of various useful things like Constants and whatnot
    """
    def __init__(self, compiler):
        self._compiler = compiler
        self._full_sys_searched_font_finder = None

    # ---------------------------------
    # Provided Classes

    @property
    def Placer(self):
        """
        An ABC class for writing Placers
        """
        from placer import Placer as _Placer
        return _Placer

    @property
    def NaivePlacer(self):
        """
        A Naive implementation ofthe Placer class.
        """
        from placer import NaivePlacer as _NaivePlacer
        return _NaivePlacer

    @property
    def TextInfo(self):
        from placer.templates import TextInfo
        return TextInfo

    @property
    def MarkedUpText(self):
        from marked_up_text import MarkedUpText
        return MarkedUpText

    @property
    def Markup(self):
        from markup import Markup
        return Markup

    # ---------------------------------
    # Constants made available for coders coding in python in their pdfo files

    COLORS = _colors
    PAGE_SIZES = _page_sizes
    UNITS = _units
    ALIGNMENT = _ALIGNMENT
    STRIKE_THROUGH = _STRIKE_THROUGH
    UNDERLINE = _UNDERLINE

    # ---------------------------------
    # Methods that allow a standard way for users to get constants from commands

    @staticmethod
    def color_for_str(color_name_str):
        """
        Returns a color for the given string.
        """
        color_name_str = str(color_name_str)
        trimmed = trimmed(color_name_str)
        lowered = trimmed.lower()

        if lowered in _colors_dict:
            return _colors_dict[lowered]

        raise AssertionError(f'{color_name_str} is not a valid name for a color.')

    @staticmethod
    def page_size_for_str(page_size_str):
        return _page_sizes_dict[trimmed(page_size_str).upper()]
        raise AssertionError(f'{page_size_str} is not a valid page size.')

    @staticmethod
    def unit_for_str(unit_name_str):
        return _units_dict[trimmed(unit_name_str).lower()]
        raise AssertionError(f'{unit_name_str} is not a valid unit.')

    @staticmethod
    def alignment_for_str(alignment_name):
        return _ALIGNMENT.validate(alignment_name)

    @staticmethod
    def strike_through_for_str(script_name):
        return _STRIKE_THROUGH.validate(script_name)

    @staticmethod
    def underline_for_str(script_name):
        return _UNDERLINE.validate(script_name)

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
    def assert_instance(obj, types, var_name=None, or_none=False):
        assert_instance(obj, types, var_name, or_none)

    @staticmethod
    def assert_subclass(obj, types, var_name=None, or_none=False):
        assert_subclass(obj, types, var_name, or_none)

    @staticmethod
    def validate_font_name(font_name, return_false=False):
        """
        Returns True if the given font_name is registered and thus is safe
            to use on the PDF, raises an error (if return_false is False)
            or returns False (if return_false is True) otherwise.
        """
        if (font_name in FONT_FAMILIES) or (font_name in ToolBox.registered_fonts()) \
                or (font_name in ToolBox.standard_fonts()):
            return True

        if return_false:
            return False
        else:
            raise AssertionError(f'"{font_name}" has not been imported and thus cannot be used in the PDFDocument.')

    def register_font(self, font_name, font_file_paths=None):
        """
        Registers a font for use in the PDF. Once a font is registered, you can
            use the font_name to set the canvas to it (you can now do

            some_pdf_component.text_info().setFont(the_font_name_you_gave_this_method)

            and it will work just fine)

        font_name is the name of the font you want to register

        font_file_paths is a string or list of strings containing the possible
            path(s) to a file

        If font_file_paths is None, then a list of default file paths is checked
            for the font with the given font_name.
        """
        font_name = str(font_name)

        if self.validate_font_name(font_name, True):
            # Font has already been registered
            return

        paths_used = []
        font_found = None

        # Since a font_file_path was given, first check it for the requested font
        if font_file_paths is not None:
            if isinstance(font_file_paths, iter):
                paths_used.extend((str(p) for p in font_file_paths))
            else:
                paths_used.append(str(font_file_paths))

            if len(paths_used) > 0:
                # FontFinder raises an error if no directory is specified
                #   i.e. no directories are added

                ff = FontFinder(useCache=False)
                ff.addDirectories(paths_used)
                ff.search()
                font_found = _font_from_font_finder(ff, font_name)

        # If the font was not found (it is still None) search the system for it
        if font_found is None:
            paths_used.extend(_sys_font_search_paths)

            # search the system for the font, or, if possible, use a cached
            #    FontFinder that has already searched the system and has stored
            #    the fonts it found
            if self._full_sys_searched_font_finder is None:
                ff = self._full_sys_searched_font_finder = FontFinder(useCache=False)
                ff.addDirectories(_sys_font_search_paths)
                ff.search()
            else:
                # Cached FontFinder was available, so use it
                ff = self._full_sys_searched_font_finder

            font_found = _font_from_font_finder(ff, font_name)

        assert font_found is not None, f'Font with name "{font_name}" could not be found on this/these path(s):\n{[p for p in paths_used]}\n\n'

        if isinstance(font_found, list):
            # A font family was found, so register it

            # Find the default font (font that will be used to fill in missing fonts)
            default_font = None
            for font in font_found:
                if font is not None:
                    default_font = font
                    break
            else:
                raise AssertionError(f'Font with name "{font_name}" could not be found on this/these path(s):\n{[p for p in paths_used]}\n\n')

            # Now fill in the fonts that are None
            for i in range(len(font_found)):
                if font_found[i] is None:
                    font_found[i] = default_font
                else:
                    font_found_name = font_found[i].name
                    # Register the font with reportlab
                    registerFont(TTFont(font_found_name, font_found[i].fileName))

                    if isinstance(font_found_name, bytes):
                        font_found_name = font_found_name.decode('utf-8')

                    REGISTERED_FONTS.add(font_found_name)

            FONT_FAMILIES[font_name] = FontFamily(*[f.name for f in font_found])
        else:
            # Only one font was found

            # Save the name asked for by the user and the actual name of the
            #   font that needs to be given to reportlab to get the font
            FONT_NAMES[font_name] = font_found.name

            # Register the font with reportlab
            registerFont(TTFont(font_found.name, font_found.fileName))
            font_found_name = font_found.name

            if isinstance(font_found_name, bytes):
                font_found_name = font_found_name.decode('utf-8')

            REGISTERED_FONTS.add(font_found_name)

    def register_font_family(self, family_name, normal_font_name, bold_font_name, italics_font_name, bold_italics_font_name):
        """
        Registers a font family A.K.A. a grouping of fonts that gives the affect
            of Bolding/Italicizing/Bolding and Italicizing text. Once a font
            family is registered, just do

            some_pdf_component.text_info().setFont(your_font_family_name)

            and the pdfo will automatically switch between the different fonts
            as the current font that the document is requesting. i.e., the
            font will become italics/bold/bold and italics as you expect it to.

        NOTE: All fonts used in this font_family must be imported/registered
            BEFORE you pass in their names here.

        NOTE: This method is meant for registering your own custom font families
            made out of other fonts. For example, you could make a family that
            is normally in Times but then switches to courier when you bold it
            and switches to ZapfDingbats when you italicise it and switches
            to Helvetica when you bold and italicise it. Why would you want to
            do that? I don't know. But the option is there if you want to.
        """
        # Validate the fonts so that we know they have already been registered
        self.validate_font_name(normal_font_name)
        self.validate_font_name(bold_font_name)
        self.validate_font_name(italics_font_name)
        self.validate_font_name(bold_italics_font_name)

        if normal_font_name in FONT_FAMILIES:
            normal_font_name = FONT_FAMILIES[normal_font_name].font(False, False)
        elif normal_font_name in FONT_NAMES:
            normal_font_name = FONT_NAMES[normal_font_name]

        if bold_font_name in FONT_FAMILIES:
            bold_font_name = FONT_FAMILIES[bold_font_name].font(True, False)
        elif bold_font_name in FONT_NAMES:
            bold_font_name = FONT_NAMES[bold_font_name]

        if italics_font_name in FONT_FAMILIES:
            italics_font_name = FONT_FAMILIES[italics_font_name].font(False, True)
        elif italics_font_name in FONT_NAMES:
            italics_font_name = FONT_NAMES[italics_font_name]

        if bold_italics_font_name in FONT_FAMILIES:
            bold_italics_font_name = FONT_FAMILIES[bold_italics_font_name].font(True, True)
        elif bold_italics_font_name in FONT_NAMES:
            bold_italics_font_name = FONT_NAMES[bold_italics_font_name]

        FONT_FAMILIES[str(family_name)] = FontFamily(normal_font_name, bold_font_name, italics_font_name, bold_italics_font_name)

    def system_fonts(self):
        """
        Searches your system and returns a list of all the fonts available
        on your system.
        """
        if self._full_sys_searched_font_finder is None:
            ff = FontFinder(useCache=False)
            ff.addDirectories(_sys_font_search_paths)
            ff.search()
            self._full_sys_searched_font_finder = ff
        else:
            ff = self._full_sys_searched_font_finder

        font_names = [f.decode("utf-8") for f in ff.getFamilyNames()]
        return font_names

    @staticmethod
    def standard_fonts():
        """
        Returns a list of strings of the names of fonts that are standard.
        """
        return standardFonts

    @staticmethod
    def registered_fonts():
        """
        Returns a list of all registered fonts i.e. every font name that can be
            currently used. If you want more, then you need to register the new
            font.
        """
        return [p for p in REGISTERED_FONTS]

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
        font_name = text_info.working_font_name()
        font_size = text_info.font_size()

        assert isinstance(font_name, (str, bytes)), f'The font_name of the given text_info must be of type str, not {font_name}'
        assert isinstance(font_size, (int, float, Decimal)), f'The font_size of the given text_info must be of type int, float, or Decimal, not {font_name}'

        return Decimal(stringWidth(string, font_name, font_size)), (font_size)
