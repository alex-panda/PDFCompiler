"""
A module providing a ToolBox for the users of the compiler to use.
"""
import os
import os.path as path
from collections import namedtuple as named_tuple
from decimal import Decimal

from fpdf import FPDF

from markup import Markup, MarkupStart, MarkupEnd
from tools import assure_decimal, trimmed, assert_instance, assert_subclass
from color import Color
from constants import (ALIGNMENT as _ALIGNMENT, STRIKE_THROUGH as _STRIKE_THROUGH,
        UNDERLINE as _UNDERLINE, FONT_FAMILIES, FONTS, FontFamily, Font,
        PAGE_SIZES_DICT, UNIT as _UNIT, COLORS, FONT_SEARCH_PATHS,
        STANDARD_FONTS, FONTS_TO_IMPORT, GLOBAL_FPDF, FONTS_IMPORTED_TO_GLOBAL_FPDF)


_page_sizes = named_tuple('PageSize', [key for key in PAGE_SIZES_DICT])(*[value for value in PAGE_SIZES_DICT.values()])

_colors = named_tuple('Colors', [key for key in COLORS])(*[Color.from_str(val) for val in COLORS.values()])

def _find_fonts(directories:list=None):
    """
    Checks the given directories for fonts, and puts all the fonts found in them
        into the FONTS constant and all the FontFamilies into the FONT_FAMILIES
        constant

    If directories is None, then the default system directories will be checked
        for fonts.
    """
    if directories is None:
        directories = FONT_SEARCH_PATHS
    elif isinstance(directories, str):
        directories = [directories]

    file_paths = set()
    for directory in directories:
        directory = path.abspath(path.expandvars(path.expanduser(str(directory))))

        # If the directory does not exist or is not actually a directory, then
        #   continue on to check the rest of the directories
        if path.isfile(directory):
            file_paths.add(directory)
            continue
        elif not path.isdir(directory):
            continue

        for root, dirs, files in os.walk(directory, followlinks=True):
            for name in files:
                file_paths.add(path.abspath(path.join(root, name)))

    # We will be using the TTFontFile to test each file to see which ones
    #   can actually be opened and parsed and thus can actually be used by the
    #   compiler
    from fpdf.ttfonts import TTFontFile

    found_fonts = {}
    for file_path in file_paths:
        root, ext = path.splitext(file_path)

        if ext.lower() in ('.ttf', '.ttc'):
            font = TTFontFile()
            try:
                font.getMetrics(file_path)
            except:
                continue

            # Font was successfuly found and parsed

            bold = False; italics = False
            if font.italicAngle != 0:
                italics = True
            if font.flags & (1 << 18):
                bold = True

            fullname = font.fullName

            if isinstance(fullname, bytes):
                fullname = fullname.decode('utf-8')

            fullname = fullname.replace(' ', '')
            family_name = font.familyName.replace(' ', '')

            found_fonts[fullname] = Font(family_name, fullname, bold, italics, file_path)

        else:
            continue

    FONTS.update(found_fonts)

    # Now figure out FontFamilies from the fonts

    def style_of_font(font):
        """
        Figure out what style of font the font is i.e. is it normal, bold,
            italics, or both
        """
        if font.bold and font.italics:
            style = 'bold_italics'
        elif font.bold:
            style = 'bold'
        elif font.italics:
            style = 'italics'
        else:
            style = 'norm'

        return style

    changed_font_fams = set()
    for font in found_fonts.values():

        # Retrieve the corresponding FontFamily for the font

        fam_name = font.family_name

        if fam_name in FONT_FAMILIES:
            fam = FONT_FAMILIES[fam_name]
        else:
            fam = FONT_FAMILIES[fam_name] = FontFamily(fam_name, None, None, None, None)

        # Set the style of the family for this font to this font (FontFamilies
        #   only contain font.full_names, not Font objects)

        setattr(fam, style_of_font(font), font.full_name)

        changed_font_fams.add(fam_name)

    # Go through and make sure that there are no None values left in any of the
    #   font families
    for fam_name in changed_font_fams:
        fam = FONT_FAMILIES[fam_name]

        # Find the default font for the family (the font that we will make all
        #   None values of the family into)
        default_font_name = None
        for font in fam.fonts():

            if font is not None:
                default_font_name = font
                break

        if default_font_name is None:
            # No Font was provided for the Font family so just get rid of the
            #   empty family.
            FONT_FAMILIES.pop(fam_name)
            continue

        # Now fill in None values of the FontFamily with the default font

        for style in ['norm', 'bold', 'italics', 'bold_italics']:
            font = getattr(fam, style)
            if font is None:
                setattr(fam, style, default_font_name)

    return found_fonts

class ToolBox:
    """
    A toolbox of various useful things like Constants and whatnot
    """
    def __init__(self, compiler):
        self._compiler = compiler
        self._full_sys_searched_fonts = None

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

    COLOR = _colors
    PAGE_SIZE = _page_sizes
    UNIT = _UNIT
    ALIGNMENT = _ALIGNMENT
    STRIKE_THROUGH = _STRIKE_THROUGH
    UNDERLINE = _UNDERLINE

    # ---------------------------------
    # Methods that allow a standard way for users to get constants from commands

    @staticmethod
    def color_for_str(color_name_str, false_on_fail):
        """
        Returns a color for the given string.
        """
        color_name_str = trimmed(str(color_name_str))
        res = getattr(_colors, color_name_str, None)
        if res is not None: return res
        return Color.from_str(color_name_str, false_on_fail)

    @staticmethod
    def page_size_for_str(page_size_str):
        try:
            return PAGE_SIZES_DICT[trimmed(page_size_str).upper()]
        except KeyError:
            raise AssertionError(f'{page_size_str} is not a valid page size.')

    @staticmethod
    def unit_for_str(unit_name_str):
        unit_name_str = trimmed(str(unit_name_str)).lower()
        if unit_name_str in ('cm', 'inch', 'pt', 'mm', 'pica'):
            return getattr(_UNIT, unit_name_str.upper())
        raise AssertionError(f'{unit_name_str} is not a valid unit.')

    @staticmethod
    def length_for_str(string):
        """
        Canverts string to a a length (float) in pts (that way it can be used
            on the canvas)
        """
        string = str(string).lower()
        try:
            if string[-2:] == 'cm':
                return float(string[:-2]) * _UNIT.CM
            elif string[-1:] == 'i':
                return float(string[:-1]) * _UNIT.INCH
            elif string[-2:] == 'in':
                return float(string[:-2]) * _UNIT.INCH
            elif string[-4:] == 'inch':
                return float(string[:-4]) * _UNIT.INCH
            elif string[-2:] == 'pt':
                return float(string[:-2])
            elif string[-3:] == 'pts':
                return float(string[:-3])
            elif string[-2:] == 'mm':
                return float(string[:-2]) * _UNIT.MM
            elif string[-4:] == 'pica':
                return float(string[:-4]) * _UNIT.PICA
            return float(string)
        except:
            raise ValueError("Could not convert {string} to a length.")

    @staticmethod
    def alignment_for_str(alignment_name):
        return _ALIGNMENT.validate(alignment_name)

    @staticmethod
    def strike_through_for_str(script_name):
        return _STRIKE_THROUGH.validate(script_name)

    @staticmethod
    def underline_for_str(script_name):
        return _UNDERLINE.validate(script_name)

    # ---------------------------------
    # Other Helpful Methods

    @staticmethod
    def assert_instance(obj, types, var_name=None, or_none=False):
        assert_instance(obj, types, var_name, or_none)

    @staticmethod
    def assert_subclass(obj, types, var_name=None, or_none=False):
        assert_subclass(obj, types, var_name, or_none)

    def validate_font_name(self, font_name, false_on_fail=False):
        """
        Returns True if the given font_name is registered and thus is safe
            to use on the PDF, raises an error (if false_on_fail is False)
            or returns False (if false_on_fail is True) otherwise.
        """
        if (font_name in self.registered_font_families()) \
                or (font_name in self.registered_fonts()) \
                or (font_name in self.standard_fonts()):
            return True

        if false_on_fail:
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
        font_name = str(font_name).replace(' ', '')

        if not (font_file_paths is None or isinstance(font_file_paths, list)):
            font_file_paths = [font_file_paths]

        if (font_name in FONTS_TO_IMPORT) or (font_name in STANDARD_FONTS):
            # Font has already been registered
            return

        def try_register(font_name):
            """
            Try to register the font_name, returning False if the it cannot
                be registered and True otherwise.
            """
            # If the name is in either of these, then the font was found
            if font_name in FONTS:
                FONTS_TO_IMPORT[font_name] = FONTS[font_name].file_path
                return True
            elif font_name in FONT_FAMILIES:
                for fnt_name in FONT_FAMILIES[font_name].fonts():
                    FONTS_TO_IMPORT[fnt_name] = FONTS[fnt_name].file_path
                return True

            return False

        if try_register(font_name):
            return

        paths_to_check = set()
        font_found = False

        if font_file_paths is not None:
            # Since a font_file_path was given, first check it for the requested font
            if isinstance(font_file_paths, list):
                curr_file_dir = self._compiler.curr_file_dir()
                paths = set()
                for p in font_file_paths:
                    paths.add(path.normpath(path.join(curr_file_dir, str(p))))

                main_file_dir = self._compiler.main_file_dir()
                for p in font_file_paths:
                    paths.add(path.normpath(path.join(main_file_dir, str(p))))

                for p in paths:
                    paths_to_check.add(p)
            else:
                curr_file_dir = self._compiler.curr_file_dir()
                paths_to_check.add(path.normpath(path.join(curr_file_dir, str(font_file_paths))))

                main_file_dir = self._compiler.main_file_dir()
                paths_to_check.add(path.normpath(path.join(main_file_dir, str(font_file_paths))))

            _find_fonts(font_file_paths)

            if try_register(font_name):
                return

        if not self._full_sys_searched_fonts:
            self.system_fonts() # Searches the fonts on the system and loads them into FONTS and FONT_FAMILIES

            if try_register(font_name):
                return

        paths_used = set()

        for p in font_file_paths:
            paths_used.add(str(p))

        for p in FONT_SEARCH_PATHS:
            paths_used.add(str(p))

        raise AssertionError(f'Font with name "{font_name}" could not be found on this/these path(s):\n{[p for p in paths_used]}\n\n')

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
        elif normal_font_name in FONTS:
            normal_font_name = FONTS[normal_font_name].full_name

        if bold_font_name in FONT_FAMILIES:
            bold_font_name = FONT_FAMILIES[bold_font_name].font(True, False)
        elif bold_font_name in FONTS:
            bold_font_name = FONTS[bold_font_name].full_name

        if italics_font_name in FONT_FAMILIES:
            italics_font_name = FONT_FAMILIES[italics_font_name].font(False, True)
        elif italics_font_name in FONTS:
            italics_font_name = FONTS[italics_font_name].full_name

        if bold_italics_font_name in FONT_FAMILIES:
            bold_italics_font_name = FONT_FAMILIES[bold_italics_font_name].font(True, True)
        elif bold_italics_font_name in FONTS:
            bold_italics_font_name = FONTS[bold_italics_font_name].full_name

        FONT_FAMILIES[str(family_name)] = FontFamily(str(family_name), normal_font_name, bold_font_name, italics_font_name, bold_italics_font_name)

    def fonts_in_directory(self, directory):
        """
        Returns a list of all the Fonts in the given directory.
        """
        directory = str(directory)

    def system_fonts(self):
        """
        Searches your system and returns a list of all the fonts available
        on your system.

        Returns a dict of font_name:font_file_path  key:value  pairs
        """
        if self._full_sys_searched_fonts is None:
            sf = self._full_sys_searched_fonts = _find_fonts(FONT_SEARCH_PATHS)
        else:
            sf = self._full_sys_searched_fonts

        return {f.full_name:f.file_path for f in sf.values()}

    def system_font_families(self):
        """
        Searches your system and returns a list of all the fonts available
        on your system.

        Returns a list of fonts
        """
        if self._full_sys_searched_fonts is None:
            sf = self._full_sys_searched_fonts = _find_fonts(FONT_SEARCH_PATHS)
        else:
            sf = self._full_sys_searched_fonts

        return {f.family_name:FONT_FAMILIES[f.family_name] for f in sf.values()}

    def standard_fonts(self):
        """
        Returns a tuple of strings of the names of fonts that are standard and
            available in all PDFs.
        """
        return STANDARD_FONTS

    def registered_fonts(self):
        """
        Returns a list of all registered fonts i.e. every font name that can be
            currently used. If you want more, then you need to register the new
            font.
        """
        return {key:value for key, value in FONTS_TO_IMPORT.items()}

    def registered_font_families(self):
        """
        Returns a dictionary of family_name:FontFamily key:value pairs
        """
        registered_font_families = {}
        for font_name in FONTS_TO_IMPORT:
            font = FONTS[font_name]

            fam_name = font.family_name

            fam = FONT_FAMILIES[fam_name]
            registered_font_families[fam_name] = fam

        for fam_name in ('Times', 'Courier', 'Helvetica', 'Symbol', 'Zapfdingbats'):
            registered_font_families[fam_name] = FONT_FAMILIES[fam_name]

        return registered_font_families

    @staticmethod
    def assure_landscape(page_size):
        """
        Returns a tuple of the given page_size in landscape orientation, even
            if it is already/given in landscape orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        a, b = page_size
        if a < b:
            return (assure_decimal(b), assure_decimal(a))
        else:
            return (assure_decimal(a), assure_decimal(b))

    @staticmethod
    def assure_portrait(page_size):
        """
        Returns a tuple of the given page_size in portrait orientation, even
            if it is already/given in portrait orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        a, b = page_size
        if a >= b:
            return (assure_decimal(b), assure_decimal(a))
        else:
            return (assure_decimal(a), assure_decimal(b))

    @staticmethod
    def string_size(string, text_info):
        """
        Returns the (width, height) of the given string based on the given
            text_info object.
        """
        font_name = str(text_info.working_font_name())
        font_size = text_info.font_size()

        assert isinstance(font_name, str), f'The font_name of the given text_info must be of type str, not {font_name}'
        assert isinstance(font_size, (int, float, Decimal)), f'The font_size of the given text_info must be of type int, float, or Decimal, not {font_name}'

        #print(f'FONTS: {FONTS}')
        #print(f'FONT_FAMILIES: {FONT_FAMILIES}')

        if not (font_name in FONTS_IMPORTED_TO_GLOBAL_FPDF):
            not_found = True
            if font_name in FONTS:
                GLOBAL_FPDF.add_font(font_name, fname=FONTS[font_name].file_path, uni=True)
                FONTS_IMPORTED_TO_GLOBAL_FPDF.add(font_name)
                not_found = False
            elif font_name in FONT_FAMILIES:
                fam = FONT_FAMILIES[font_name]
                for font_nm in  fam.fonts():
                    if font_nm in FONTS:
                        GLOBAL_FPDF.add_font(font_nm, fname=FONTS[font_nm].file_path, uni=True)
                        FONTS_IMPORTED_TO_GLOBAL_FPDF.add(font_nm)
                not_found = False
            elif font_name in STANDARD_FONTS:
                not_found = False

            if not_found:
                raise AssertionError(f'The font "{font_name}" needs to be imported before its use')

        text_info.apply_to_canvas(GLOBAL_FPDF)

        return (Decimal(GLOBAL_FPDF.get_string_width(string)), Decimal(font_size))


