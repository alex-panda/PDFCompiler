from fpdf import FPDF
from fpdf.errors import FPDFException

from tools import assure_decimal, assert_instance, assert_subclass, draw_str
from tools import prog_bar_prefix, print_progress_bar, calc_prog_bar_refresh_rate
from constants import TT, ALIGNMENT, ALIGNMENT, STRIKE_THROUGH, UNDERLINE, FONT_FAMILIES, FONTS_TO_IMPORT, UNIT, FONTS
from color import Color

from shapes import Point, Rectangle

from toolbox import ToolBox
from decimal import Decimal


class TextInfo:
    __slots__ = [
            '_script', '_alignment', '_line_spacing',
            '_font_name', '_font_size', '_font_color', '_font_color_gray', '_font_color_alpha', '_font_highlight_color',
            '_underline', '_strikethrough',
            '_bold', '_italics', '_can_split_words']

    def __init__(self):
        self._script = None # Whether it is superscript, subscript, or normal script
        self._alignment = None # The alignment of the text in the template. A default of None means that it is aligned to the Right
        self._line_spacing = None # How much space should be between lines in the paragraph

        self._font_name = None
        self._font_size = None
        self._font_color = None
        self._font_color_gray = None
        self._font_color_alpha = None
        self._font_highlight_color = None

        self._underline = None
        self._strikethrough = None

        # Boolean Feilds
        self._bold = None
        self._italics = None
        self._can_split_words = None

    # ---------

    def script(self):
        return self._script

    def set_script(self, new):
        assert_instance(new, int, 'script')
        self._script = new
        return self

    def alignment(self):
        return self._alignment

    def set_alignment(self, new):
        assert_instance(new, ALIGNMENT, 'alignment')
        self._alignment = new
        return self

    def line_spacing(self):
        return self._line_spacing

    def set_line_spacing(self, new):
        assert_instance(new, (int, Decimal, float), 'line_spacing')
        self._line_spacing = assure_decimal(new)
        return self

    # ---------

    def working_font_name(self):
        """
        The font name that is actually given to the canvas based on what the
            current font_name, bold, and italics are
        """
        fn = self.font_name()

        if fn in FONT_FAMILIES:
            fn = FONT_FAMILIES[fn].font(self.bold(), self.italics())
        elif fn in FONTS:
            fn = FONTS[fn].full_name
        return fn

    def font_name(self):
        """
        Returns the current font_name that this TextInfo is using. If it is
            set to the name of a FontFamily, then the font family's name
            is returned by this method. If you want the name of the font that
            will be passed to the canvas in that case, then use the
            working_font_name method.
        """
        return self._font_name

    def set_font_name(self, new):
        if isinstance(new, bytes):
            new = new.decode('utf-8')

        assert_instance(new, str, 'font_name')

        if new is not None:
            new = new.replace(' ', '')

        self._font_name = new

        return self

    def font_size(self):
        return self._font_size

    def set_font_size(self, new):
        assert_instance(new, (int, float, Decimal), 'font_size')
        self._font_size = new
        return self

    def font_color(self):
        return self._font_color

    def set_font_color(self, new):
        assert_instance(new, Color, 'font_color')
        self._font_color = new
        return self

    def font_color_gray(self):
        return self._font_color_gray

    def set_font_color_gray(self, new):
        assert_instance(new, (float, int), 'font_color_gray')
        if new is not None:
            assert 0.0 <= new <= 1.0, f'font_color_gray must be between 0 and 1 inclusive, not {new}'
        self._font_color_gray = new
        return self

    def font_highlight_color(self):
        return self._font_highlight_color

    def set_font_highlight_color(self, new):
        assert_instance(new, Color, 'font_highlight_color')
        self._font_highlight_color = new
        return self

    # ---------

    def underline(self):
        return self._underline

    def set_underline(self, new):
        assert_instance(new, UNDERLINE, 'underline')
        self._underline = new
        return self

    def strikethrough(self):
        return self._strikethrough

    def set_strikethrough(self, new):
        assert_instance(new, STRIKE_THROUGH, 'font_strikethrough')
        self._strikethrough = new
        return self

    # ---------

    def bold(self):
        return self._bold

    def set_bold(self, boolean):
        assert_instance(boolean, bool, 'bold')
        self._bold = boolean
        return self

    def italics(self):
        return self._italics

    def set_italics(self, boolean):
        assert_instance(boolean, bool, 'italics')
        self._italics = boolean
        return self

    def can_split_words(self):
        return self._can_split_words

    def set_can_split_words(self, boolean):
        assert_instance(boolean, bool, 'can_split_words')
        self._can_split_words = boolean
        return self

    # --------------------------
    # Non-getter-setter Methods

    def merge(self, other_text_info):
        """
        Merges this TextInfo with another so that this one changes its attributes
            to match all the NON-None attributes of the other one.
        """
        for atr in self.__slots__:
            if getattr(other_text_info, atr) is not None:
                setattr(self, atr, getattr(other_text_info, atr))

    def gen_undo_dict(self, other_text_info):
        """
        Takes in another TextInfo that you are about to merge with this
            one (so you will call this_text_info.merge(other_text_info))
            and generates a dict object that your can use this_text_info.undo()
            with to undo the changes you made to it.
        """
        return {atr:getattr(self, atr) for atr in self.__slots__ if getattr(other_text_info, atr) is not None}

    def undo(self, undo_dict):
        """
        Takes in an undo_dict generated by gen_undo_dict and undoes the changes
            that the merge that happened after the undo_dict was generated made.
        """
        for atr, value in undo_dict.items():
            setattr(self, atr, value)

    def copy(self):
        """
        Returns a copy of a TextInfo object.
        """
        new = TextInfo()
        for atr in self.__slots__:
            setattr(new, atr, getattr(self, atr))
        return new

    def clear(self):
        for atr in self.__slots__:
            setattr(self, atr, None)

    def apply_to_placer(self, placer):
        """
        Apply to the Placer what can be applied.
        """

    def apply_to_canvas(self, canvas):
        """
        Apply what can be applied to the canvas.
        """
        # Handle Font name
        fn = self.working_font_name()

        if fn is not None:
            try:
                canvas.set_font(fn, style='')
            except FPDFException:

                if fn[-2:] == 'BI':
                    fn = fn[:-2]
                    style = 'BI'

                elif fn[-1:] == 'B':
                    fn = fn[:-1]
                    style = 'B'

                elif fn[-1:] == 'I':
                    fn = fn[:-1]
                    style = 'I'

                else:
                    style = ''

                canvas.set_font(fn, style=style)

        # handle font size
        fs = self.font_size()

        if fs is not None:
            canvas.set_font_size(fs)

        fcg = self.font_color_gray()
        assert_instance(fcg, float, 'font_color_gray')

        if fcg is not None:
            assert 0.0 <= fcg <= 1.0, f'font_color_gray values must be between 0 and 1 inclusive, not {fcg}'
            canvas.set_text_color(fcg)

        # Handle font color
        fc = self.font_color()
        assert_instance(fc, Color, 'font_color')

        if fc is not None:
            canvas.set_text_color(*fc.rgb())

    def __repr__(self):
        string = f'{self.__class__.__name__}('
        for i, a in enumerate(self.__slots__):
            if i > 0:
                string += ', '
            attri_name = a[1:]
            attr_val = getattr(self, a)
            string += f'{attri_name}={attr_val}'
        string += ')'
        return string


class HasTextInfo:
    __slots__ = ['_text_info']
    def __init__(self):
        self._text_info = TextInfo()

    def text_info(self):
        return self._text_info

    def set_text_info(self, new):
        assert_instance(new, TextInfo, 'text_info', or_none=False)
        self._text_info = new

class PDFComponent(HasTextInfo):
    __slots__ = HasTextInfo.__slots__[:]
    __slots__.extend(['_left_margin', '_right_margin', '_top_margin', '_bottom_margin',
            '_rect', '_parent', '_on_creation_callbacks', '_end_callbacks'])
    def __init__(self):
        HasTextInfo.__init__(self)
        self._left_margin = 0
        self._right_margin = 0
        self._top_margin = 0
        self._bottom_margin = 0

        # This rectangle represents the inner rectangle of the component (i.e.
        # the area inside the Margins of the component)
        self._rect = Rectangle()

        # The parent of this PDFComponent. For example, the parent of a
        # PDFParagraph is a PDFColumn and the parent of a PDFColumn is a
        # PDFPage
        self._parent = None

        # Callbacks to be called when this PDFComponent is first "Created"
        self._on_creation_callbacks = []

        # A list of callbacks that will be called after the entirety of the
        #   PDFDocument has been placed.
        self._end_callbacks = []

    # --------------
    # Margins Start

    def left_margin(self):
        return self._left_margin

    def set_left_margin(self, new_left):
        rect = self.total_rect()
        self._left_margin = assure_decimal(new_left)
        self.set_total_rect(rect)

    def right_margin(self):
        return self._right_margin

    def set_right_margin(self, new_right):
        rect = self.total_rect()
        self._right_margin = assure_decimal(new_right)
        self.set_total_rect(rect)

    def top_margin(self):
        return self._top_margin

    def set_top_margin(self, new_top):
        rect = self.total_rect()
        self._top_margin = assure_decimal(new_top)
        self.set_total_rect(rect)

    def bottom_margin(self):
        return self._bottom_margin

    def set_bottom_margin(self, new_bottom):
        rect = self.total_rect()
        self._bottom_margin = assure_decimal(new_bottom)
        self.set_total_rect(rect)

    def margins(self):
        return self.left_margin(), self.right_margin(), self.top_margin(), self.bottom_margin()

    def set_margins(self, left, right=None, top=None, bottom=None):
        """
        Sets all the margins for the PDFComponent.

        Can either give the new margins directly or give a tuple of them.
        """
        if right is None:
            # Then left should be a tuple of them
            left, right, top, bottom = left

        rect = self.total_rect()
        self._left_margin = assure_decimal(left)
        self._right_margin = assure_decimal(right)
        self._top_margin = assure_decimal(top)
        self._bottom_margin = assure_decimal(bottom)
        self.set_total_rect(rect)

    # Margins End
    # --------------

    def on_creation_callbacks(self):
        return self._on_creation_callbacks

    def add_on_creation_callback(self, callback):
        """
        Adds a creation callback to the PDFComponent. This callback will be
            called when this PDFComponent is first created and initialized with
            its TextInfo. This is so that you can do things to it BEFORE the
            program even begins to place it. For example, you could add a
            callback that gives a PDFParagraphLine a left margin (to simulate a
            tab indent) if

            pdf_component.text_info().alignment() == ALIGNMENT.LEFT

            is True.

        The callback will be called with this PDFComponent being given as an
            argument.
        """
        self._on_creation_callbacks.append(callback)

    def clear_on_creation_callbacks(self):
        self._on_creation_callbacks = []

    def _call_on_creation_callbacks(self):
        """
        Runs all the on_creation callbacks for this PDFComponent
        """
        for callback in self._on_creation_callbacks:
            callback(self)

    def end_callbacks(self):
        return self._end_callbacks

    def add_end_callback(self, callback):
        """
        Adds an end callback to the PDFComponent. This callback function will
            be called and given this PDFComponent after every PDFComponent in
            the entire PDFDocument has been placed.
        """
        self._end_callbacks.append(callback)

    def clear_end_callbacks(self):
        self._end_callbacks = []

    def _call_end_callbacks(self):
        """
        Runs all the end callbacks for this PDFComponent
        """
        for callback in self._end_callbacks:
            callback(self)

    def parent(self):
        """
        Returns the parent of this PDFComponent. For example, the parent of a
            PDFParagraph is a PDFColumn and the parent of a PDFColumn is a
            PDFPage.
        """
        return self._parent

    def set_parent(self, parent):
        assert_subclass(parent, PDFComponent, 'parent', or_none=False)
        self._parent = parent

    # ------------------
    # Inner and Total Placement/Size Start

    def total_rect(self):
        rect = Rectangle()
        rect.set_point(self.total_offset())
        rect.set_size(self.total_size())
        return rect

    def set_total_rect(self, rect):
        assert_instance(rect, Rectangle, 'rect', or_none=False)
        self.set_total_offset(rect.point().copy())
        self.set_total_size(rect.size())

    def inner_rect(self):
        rect = Rectangle()
        rect.set_point(self.inner_offset().point())
        rect.set_size(self.inner_size())
        return rect

    def set_inner_rect(self, rect):
        assert_instance(rect, Rectangle, 'rect', or_none=False)
        self.set_inner_offset(rect.point())
        self.set_inner_size(rect.size())

    def set_total_offset(self, x, y=None):
        """
        Sets the total offset of the component (so the offset that includes the
            margins)
        """
        if y is not None:
            x = Point(x, y)
        else:
            Point._assure_point(x)
            x = x.copy()

        self._rect.set_point(x)

    def total_offset(self):
        return self._rect.point().copy()

    def set_inner_offset(self, x, y=None):
        """
        Sets the inner offset of this component from the top-left of the page
            that the component is on.

        Takes either a Point object or (x, y) values that can be int, Decimal,
            or float.
        """
        if y is not None:
            x = Point(x, y)
        else:
            Point._assure_point(x)
            x = x.copy()

        self.set_total_offset(x - Point(self.left_margin(), self.top_margin()))

    def inner_offset(self):
        """
        Returns the Point object that represents an offset from the top-left
            corner of the Page the component is on.
        """
        return self.total_offset() + Point(self.left_margin(), self.top_margin())

    def set_inner_size(self, width, height=None):
        """
        Sets the size of the component inside the margins.
        """
        if height is None:
            height = width[1]
            width = width[0]

        self.set_inner_height(height)
        self.set_inner_width(width)

    def inner_size(self):
        return (self.inner_width(), self.inner_height())

    def set_inner_height(self, height):
        self.set_total_height(assure_decimal(height) + self.top_margin() + self.bottom_margin())

    def set_inner_width(self, width):
        self.set_total_width(assure_decimal(width) + self.left_margin() + self.right_margin())

    def inner_height(self):
        """
        Height inside margins.
        """
        return self.total_height() - self.top_margin() - self.bottom_margin()

    def inner_width(self):
        """
        Width inside margins.
        """
        return self.total_width() - self.left_margin() - self.right_margin()

    def set_total_size(self, width, height=None):
        """
        Sets the size of the component with margins taken into account.
        """
        if height is None:
            height = width[1]
            width = width[0]

        self.set_total_height(height)
        self.set_total_width(width)

    def total_size(self):
        return (self.total_width(), self.total_height())

    def set_total_height(self, height):
        self._rect.set_height(height)

    def set_total_width(self, width):
        self._rect.set_width(width)

    def total_height(self):
        """
        Height with margins.
        """
        return self._rect.height()

    def total_width(self):
        """
        Width with margins.
        """
        return self._rect.width()

    # Inner and Total Placement/Size End
    # ------------------

    def copy(self):
        new = self.__class__()
        new.set_margins(self.margins())
        new.set_total_size(self.total_size())
        new.set_total_offset(self.total_offset())
        new.set_text_info(self.text_info().copy())
        new._on_creation_callbacks = self._on_creation_callbacks[:]
        new._end_callbacks = self._end_callbacks[:]
        return new

    def full_copy(self):
        """
        Copies not just the metadata like TextInfo, margins, offset, etc., but
            the things such as the PDFPages in the PDFDocument and PDFWords in
            the PDFParagraph.
        """
        return self.copy()

    def clear(self):
        self._rect.clear()
        self.set_margins(0, 0, 0, 0)
        self.text_info().clear()
        self._on_creation_callbacks = []
        self._end_callbacks = []

class PDFDocument(PDFComponent):
    """
    The main and top-level class of the PDFHierarchy.
    """
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_pages', '_apply_to_canvas_list'])
    def __init__(self):
        super().__init__()
        self._pages = []
        self._apply_to_canvas_list = []

    # ----------------------------------------
    # Public methods in API

    def page_count(self):
        return len(self._pages)

    def pages(self):
        return self._pages

    def add_apply_to_canvas_obj(self, apply_to_canvas_obj):
        self._apply_to_canvas_list.append(apply_to_canvas_obj)

    # This method is mainly for if you are using some sort of special case and
    #   want to draw a compiled PDFDocument to canvas while not using the
    #   Commandline tool
    def draw(self, output_file_path, print_progress=False):
        """
        Draws the PDFDocument either to a canvas or to the output_file_path
        """
        canvas = FPDF(unit='pt', font_cache_dir=None)
        canvas.set_auto_page_break(False, 0)
        # Import all the fonts that we need to so that the canvas can use them
        for font_name, font_file_path in FONTS_TO_IMPORT.items():
            canvas.add_font(font_name, fname=font_file_path, uni=True)

        for obj in self._apply_to_canvas_list:
            obj.apply_to_canvas(canvas)

        if print_progress:
            page_len = len(self._pages)
            refresh = calc_prog_bar_refresh_rate(page_len)
            prefix = prog_bar_prefix('Drawing to', output_file_path)

        if print_progress:
            for i, page in enumerate(self._pages):
                if (i % refresh) == 0:
                    print_progress_bar(i, page_len, prefix)
                page.draw(canvas)

            print_progress_bar(page_len, page_len, prefix)
        else:
            for page in self._pages:
                page.draw(canvas)

        canvas.output(str(output_file_path))

    # ----------------------------------------
    # Private Methods

    def _add_page(self, page):
        assert_instance(page, PDFPage, 'page', or_none=False)
        page.set_parent(self)
        self._pages.append(page)
        page._page_num = self.page_count() + 1

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for page in self._pages:
            page._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(pages={self._pages})'


class PDFPage(PDFComponent):
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_num_rows', '_num_cols', '_page_num',
        '_fill_rows_first', '_col_rects', '_cols',
        '_parent_document', '_curr_col_idx'])

    def __init__(self):
        super().__init__()
        self._num_rows = 1
        self._num_cols = 1
        self._page_num = None
        self._fill_rows_first = False
        self._col_rects = [] # The rectangles that contain each column
        self._cols = []

        self._parent_document = None

        self._curr_col_idx = -1 # The index of the Column that the Placer is currently putting ParagraphLines in

    def parent_document(self):
        return self._parent_document

    def _set_parent_document(self, parent):
        self._parent_document = parent

    def page_num(self):
        return self._page_num

    def page_size(self):
        return self.total_size()

    def set_page_size(self, width, height=None):
        """
        Sets the page size for this page. You can either use a tuple of height,
            width or you can give the height and width directly.
        """
        self.set_total_size(width, height)

    def fill_rows_first(self):
        return self._fill_rows_first

    def set_fill_rows_first(self, val=False):
        """
        If fill_rows_first is set to True, then the Column objects will be
            filled with text from left to right, top to bottom as opposed to
            top to bottom, left to right. In other words, the rows of Column
            objects will be filled with text first from left to right, and only
            once the last Column in the row has been filled will the next row
            of Column objects be filled.

        Do NOT set this while the Page is being filled with text. Doing so will
            cause undefined behavior. You must set it while the page is in a
            Template (i.e. before it is being used).
        """
        self._fill_rows_first = val

    def set_grid(self, num_rows, num_cols):
        """
        Sets how many rows and columns of Column objects should be created to
            hold the text.
        """
        self.set_num_rows(num_rows)
        self.set_num_cols(num_cols)

    def set_num_cols(self, num_cols):
        assert_instance(num_cols, int, 'num_cols', or_none=False)
        self._num_cols = num_cols

    def set_num_rows(self, num_rows):
        assert_instance(num_rows, int, 'num_cols', or_none=False)
        self._num_rows = num_rows

    def num_cols(self):
        return self._num_cols

    def num_rows(self):
        return self._num_rows

    def copy(self):
        new = super().copy()
        new._num_cols = self._num_cols
        new._num_rows = self._num_rows
        return new

    def _add_col(self, new_col):
        assert_instance(new_col, PDFColumn, 'new_col', or_none=False)
        self._cols.append(new_col)

    def _next_column_rect(self, peek=True):
        """
        returns the next Column that the placer should put text lines into or
            None if there are no more Columns on this Page.
        """
        if not peek:
            self._curr_col_idx += 1

        return self._col_rects[self._curr_col_idx] if self._curr_col_idx < len(self._col_rects) else None

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for col in self._cols:
            col._call_end_callbacks()

    def draw(self, canvas):
        canvas.add_page(format=tuple(float(s) for s in self.page_size()))

        for col in self._cols:
            col.draw(canvas)

    def __repr__(self):
        return f'{self.__class__.__name__}(columns={self._cols})'

class PDFColumn(PDFComponent):
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_paragraph_lines', '_paragraphs', '_height_used', '_parent_page'])
    def __init__(self):
        super().__init__()
        self._paragraph_lines = []
        self._paragraphs = [] # These are the paragraphs that START in this Column
        self._height_used = 0

        self._parent_page = None

    def parent_page(self):
        return self._parent_page

    def _set_parent_page(self, parent):
        self._parent_page = parent

    def paragraphs(self):
        """
        Returns a list of all the paragraphs that START in this Column. If you
            want to see all the columns that the paragraph is in then you need
            to do call PDFColumn.parent_columns()
        """
        return self._paragraphs

    def _add_paragraph(self, paragraph):
        self._paragraphs.append(paragraph)

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for par_line in self._paragraph_lines:
            par_line._call_end_callbacks()

    def _add_paragraph_line(self, paragraph_line):
        """
        Adds a paragraph line to this PDFColumn. The PDFParagrahLines must be
            fully initialized with all the words that will be in them in them.
            Their total height must also be their final total height.
        """
        self._paragraph_lines.append(paragraph_line)
        self._height_used += paragraph_line.total_height() * paragraph_line.text_info().line_spacing()

    def height_used(self):
        """
        Returns how much height has been used up by PDFParagrahLines so far in
        this PDFColumn
        """
        return self._height_used

    def available_area(self):
        """
        Returns a Rectangle object representing the area that is available
            for use by PDFParagrahLines (the area that has not already been used
            by PDFParagrahLines).
        """
        x, y = self.inner_offset().xy()
        width, height = self.inner_size()

        return Rectangle(x, y + self.height_used(), width, height - self.height_used())

    def draw(self, canvas):
        for pl in self._paragraph_lines:
            pl.draw(canvas)

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        # Call callbacks for paragraphs
        for par in self._paragraphs:
            par._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(paragraph_lines={self._paragraph_lines})'

class PDFParagraph(PDFComponent):
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_space_between_lines', '_paragraph_lines',
        '_parent_document', '_parent_columns'])

    def __init__(self):
        super().__init__()
        self._space_between_lines = 0
        self._paragraph_lines = []

        self._parent_document = None
        self._parent_columns = []

    def parent_document(self):
        return self._parent_document

    def _set_parent_document(self, parent):
        self._parent_document = parent

    def parent_columns(self):
        return self._parent_columns

    def _add_parent_column(self, parent):
        self._parent_columns.append(parent)

    def paragraph_lines(self):
        return self._paragraph_lines

    def _add_paragraph_line(self, line):
        assert_instance(line, PDFParagraphLine, or_none=False)
        self._paragraph_lines.append(line)

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        # Call callbacks for paragraphs
        for par_line in self.paragraph_lines():
            par_line._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(paragraph_lines={self._paragraph_lines})'

class PDFParagraphLine(PDFComponent):
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_pdfwords', '_parent_paragraph', '_parent_column',
        '_curr_height', '_curr_width', '_curr_alignment'])

    def __init__(self):
        super().__init__()
        self._pdfwords = []

        self._parent_paragraph = None
        self._parent_column = None

        self._curr_alignment = None
        self._curr_height = 0
        self._curr_width = 0

    def parent_paragraph(self):
        return self._parent_paragraph

    def _set_parent_paragraph(self, parent):
        self._parent_paragraph = parent

    def parent_column(self):
        return self._parent_column

    def _set_parent_column(self, parent):
        self._parent_column = parent

    def words(self):
        return self._pdfwords

    def word_count(self):
        return len(self._pdfwords)

    def append_word(self, word):
        """
        Appends a word to the end of the line
        """
        self._pdfwords.append(word)

        # If there is a penultimate word, that word may need to have whether
        #   it has a space after it changed, which means it needs its dimensions
        #   recalculated
        if len(self._pdfwords) > 1:
            prev_word = self._pdfwords[-2]
            self._curr_width -= prev_word.total_width()
            prev_word._set_space_after(word.space_before())
            self._curr_width += prev_word.total_width()

            th = prev_word.total_height()
            if self._curr_height < th:
                self._curr_height = th

        word._set_space_after(False)
        self._curr_width += word.total_width()

        th = word.total_height()
        if self._curr_height < th:
            self._curr_height = th

    def pop_word(self):
        """
        Pops a word off the end of the line.
        """
        if len(self._pdfwords) >= 2:
            prev_word = self._pdfwords[-2]
            prev_word._set_space_after(False)

        word = self._pdfwords.pop()

        width = 0
        height = 0

        # have recalculate the total height and might as well do width with it
        #   because the current height is not additive/subtractive, it is the
        #   max height of the line
        for pdfword in self._pdfwords:
            width += pdfword.total_width()
            th = pdfword.total_height()

            if height > th:
                height = th

        self._curr_width = width
        self._curr_height = height

        return word

    def realign(self, new_alignment):
        """
        Realigns this paragraph line to the given alignment.

        NOTE: This should only be used in end_callbacks because the words will
            not be positioned anymore after. If you use this in an on_creation
            callback then you will not see the affects of this method since the
            words will be realigned later anyway, probably not to the alignment
            you want to realign it to.
        """
        from placer import NaivePlacer
        NaivePlacer._place_words_on_line(self, new_alignment)

    def curr_width(self):
        """
        Returns the current width of this ParagraphLine according to the
            inline_objects currently in it.

        NOTE: This method iterates through all the inline objects in this
            PDFParagraphLine every single time it is run.
        """
        return self._curr_width

    def curr_height(self):
        """
        Returns the current height of this PDFParagraphLine according to the
            words currently in it.

        NOTE: This method iterates through all the words in this
            PDFParagraphLine every single time it is run.
        """
        return self._curr_height

    def draw(self, canvas):
        line_height = self.inner_height()

        for word in self._pdfwords:
            word.draw(canvas, line_height)

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        # Call callbacks for paragraphs
        for word in self._pdfwords:
            word._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(words={self._pdfwords})'

class PDFInlineObject(PDFComponent):
    """
    A base class for objects that can be added to a PDFParagraphLine
    """
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_space_before', '__space_after',
        '_width_with_space', '_width_without_space',
        '_height_with_space', '_height_without_space'])

    def __init__(self):
        super().__init__()
        self._space_before = False
        self.__space_after = False

        self._width_with_space = 0
        self._width_without_space = 0
        self._height_with_space = 0
        self._height_without_space = 0

    def set_space_before(self, boolean):
        """
        Sets whether there should be a space before it (if it is not at the
            beginning of new paragraph line)
        """
        assert_instance(boolean, bool, 'boolean', or_none=False)
        self._space_before = boolean

    def _set_space_after(self, boolean):
        self.__space_after = boolean
        self.set_inner_size(self.curr_width(), self.curr_height())

    def _space_after(self):
        return self.__space_after

    def curr_width(self):
        """
        Returns the current width of the inline object.

        If self._space_after is True, then the width of this object with a space after
            it is returned, the inner width is used otherwise.
        """
        raise NotImplementedError()

    def curr_height(self):
        raise NotImplementedError()

    def space_before(self):
        return self._space_before

class PDFWord(PDFInlineObject):
    __slots__ = PDFComponent.__slots__[:]
    __slots__.extend(['_text', '_parent_paragraph_line'])

    def __init__(self):
        super().__init__()
        self._text = ''

        self._parent_paragraph_line = None

    def parent_paragraph_line(self):
        return self._parent_paragraph_line

    def _set_parent_paragraph_line(self, parent):
        self._parent_paragraph_line = parent

    def text(self):
        """
        Returns the Text that this word contains. If space_after is true, then
            a space will be appended to the text that is returned.
        """
        return self._text + ' ' if self._space_after() else self._text

    def set_text(self, text):
        """
        Sets the text of this PDFWord. If calc_dims is True, then it also
            automatically calculates the dimensions of the text with and without
            a space.
        """
        assert isinstance(text, str), f'text must be a str, not {text}'
        self._text = text

        self._width_with_space, self._height_with_space = \
                ToolBox.string_size(text + ' ', self.text_info())

        self._width_without_space, self._height_without_space = \
                ToolBox.string_size(text, self.text_info())

    def curr_width(self):
        return self._width_with_space if self._space_after() else self._width_without_space

    def curr_height(self):
        return self._height_with_space if self._space_after() else self._height_without_space

    def draw(self, canvas, line_height=None):
        """
        Draw the Word to the given canvas.
        """
        self.text_info().apply_to_canvas(canvas)
        draw_point = self.inner_offset()

        if line_height is not None:
            draw_point += Point(0, line_height)

        # For some reason using the text() method makes parenthesis not show and
        #   just be super wonky so have to substitute it out with the following
        #   two method calls
        #canvas.text(float(draw_point.x()), float(draw_point.y()), self.text())
        canvas.set_xy(float(draw_point.x()), float(draw_point.y()))
        canvas.cell(w=0, h=0, txt=self.text())

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(text={self.text()})'


class Template:
    """
    Templates are used as factories to figure out what the current page/column/
        paragraph/paragraph line/word is supposed to look out by creating the
        objects for them.
    """
    def __init__(self, default, child_template, reset_children_on_next=True):
        self._concretes = []
        self._repeating = []
        self._one_use = []

        self._callbacks = []

        self._child_template = child_template
        self._default = default # What PDFComponent is this a template for?
        self._template_for_type = type(default)

        self._curr_instance = None

        self._reset_children_on_next = reset_children_on_next
        self.reset_state()

    def set_default(self, new):
        self._assert_child(new)
        self._default = new

    def default(self):
        return self._default

    def merge_text_info(self, text_info, end_template_type=None):
        """
        Merges the given TextInfo with each TextInfo down the hierarchy until
            the end_template_type is reached. It does merge with the
            end_template_type.
        """
        next = self.next(peek=True, copy=False)
        text_info.merge(next.text_info())

        if self.child_template() is None or isinstance(next, end_template_type):
            return text_info

        return self.child_template().merge_text_info(text_info, end_template_type)

    def sync_indexes_with(self, other_template):
        """
        Syncronizes this template's state indexes with the given template's
            state indexes.
        """
        assert isinstance(type(other_template), self), f'The other template must be of the same type as this one in order to sync their indexes. This one is ({self}), the other one is {other_template}'
        self._state_index = other_template._state_index

        if self.child_template() and other_template.child_template():
            self.child_template().sync_indexes_with(other_template.child_template())

    def next(self, peek=True, copy=True):
        """
        Returns the next new instance of the class this Template is a Template
            for.
        """
        if not peek:
            self._state_index += 1

            if self._reset_children_on_next and self.child_template():
                self.child_template().reset_state()

        i = self._state_index
        rep_i = -1 if len(self._repeating) == 0 else i % len(self._repeating)

        if copy:
            if len(self._one_use) > 0:
                return self._one_use[0].copy() if peek else self._one_use.pop(0).copy()
            elif 0 <= i < len(self._concretes):
                return self._concretes[i].copy()
            elif 0 <= rep_i < len(self._repeating):
                return self._repeating[rep_i].copy()
            else:
                return self._default.copy()
        else:
            if len(self._one_use) > 0:
                return self._one_use[0] if peek else self._one_use.pop(0)
            elif 0 <= i < len(self._concretes):
                return self._concretes[i]
            elif 0 <= rep_i < len(self._repeating):
                return self._repeating[rep_i]
            else:
                return self._default

    def child_template(self):
        return self._child_template

    def curr_state_index(self):
        """
        The current state index. This is necessary because each Template acts as
            a finite state machine with a different one of the child template
            type being selected depending on what the current index is.
        """
        return self._state_index

    def add_concrete(self, new):
        """
        Adds a concrete object of the type this Template is for. Concretes only
            happen at their specific index so, for example, if it is a
            paragraph and you want the first line of the paragraph in bold,
            then you would add a PDFParagraphLineTemplate to the
            PDFParagraphTemplate in question.  Since the paragraph line will be
            index 0, the first line (index 0) of the paragraph will overide the
            font of its words and make them bold.  After that, all lines will
            use the default PDFParagraphLineTemplate because no more repeating
            or concrete PDFParagraphLineTemplates are defined.
        """
        self._assert_child(new)
        self._concretes.append(new)

    def concretes(self):
        return self._concretes

    def add_repeating(self, new):
        """
        Adds a repeating child template. This means that whatever pattern
            of child templates are in self.repeating(), will be repeated over
            and over. If a concrete child template is present, then that will
            be used instead for that line of the text.
        """
        self._assert_child(new)
        self._repeating.append(new)

    def repeating(self):
        return self._repeating

    def add_one_use(self, new):
        """
        These are instances of this Templates child type that will only be used
            and then will be thrown away. Useful for things like starting
            chapters with the first paragraph being special and thus putting
            it in the one_use so that it is used once and then thrown out. The
            one_use objects are used in First-In-Last-Out order (a queue).
        """
        self._assert_child(new)
        self._one_use.append(new)

    def one_use(self):
        return self._one_use

    def add_callback(self, callback_function):
        """
        Callbacks are functions that will be called when an instance of
            the Template is created, with the instance being passed
            to the callback function. This allows you to do things like figure
            out where the first line of a paragraph is exactly placed on the PDF
            and put a picture to the left of it to make a list.

        Make sure that any objects you add to the PDF in a callback is added to
            ConcreteObject.added_objects so that the added objects can (like
            pictures) can be removed and added again if the ConcreteObject is
            moved.
        """
        self._add_callback(callback_function)

    def copy(self):
        """
        Copies this template. If recursive is True, then it also copies all
            children of it. For example, A PDFPageTemplate will copy all
            of its PDFParagraphTemplates, which will copy all of their
            PDFParagraphLineTemplates, which will copy all of their
            PDFWordTemplates.
        """
        new = self.__class__()
        new._default = self._default.copy()
        new._concretes = [c.copy() for c in self._concretes]
        new._repeating = [r.copy() for r in self._repeating]
        new._one_use   = [o.copy() for o in self.one_use]
        new._state_index = self._state_index
        new._child_template = self._child_template.copy()
        return new

    def clear(self, recursive=True):
        """
        Clears this template. If recursive is True, then it will also
            recursively clear all of its descendents.
        """
        self._default.clear()
        self._concretes = []
        self._repeating = []
        self._one_use   = []
        self._state_index = -1

        if recursive and self.child_template():
            self.child_template().clear()


    # -------------------------------------------------------------------------
    # Helper Methods not in API

    def _assert_child(self, obj, or_none=False):
        assert_instance(obj, self._template_for_type, or_none=or_none)

    def reset_state(self, recursively=True):
        self._state_index = -1

        if recursively and self._reset_children_on_next and self.child_template():
            self.child_template().reset_state()

class PDFDocumentTemplate(Template):
    def __init__(self):
        default = PDFDocument()

        # Set Defaults for text on the pages
        t = default.text_info()
        t.set_script(0)
        t.set_alignment(ALIGNMENT.LEFT)

        t.set_font_name('Times')
        t.set_font_size(12)
        t.set_font_color(ToolBox.COLOR.BLACK)
        t.set_font_color_gray(None)
        t.set_font_highlight_color(None)

        t.set_underline(UNDERLINE.NONE)
        t.set_strikethrough(STRIKE_THROUGH.NONE)

        t.set_bold(False)
        t.set_italics(False)
        t.set_can_split_words(False)

        t.set_line_spacing(2)

        super().__init__(default, PDFPageTemplate())

    # ---------------------------
    # Get the next instance of an object

    def next_document(self, peek=True):
        """
        Returns a copy of what the next document should look like.
        """
        next = self.next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFDocument))
        next._call_on_creation_callbacks()
        return next

    def next_page(self, peek=True):
        """
        Returns a copy of what the next page should look like.
        """
        next = self.page_template().next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFPage))
        next._call_on_creation_callbacks()
        return next

    def next_column(self, peek=True):
        """
        Returns a copy of what the next column should look like.
        """
        next = self.column_template().next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFColumn))
        next._call_on_creation_callbacks()
        return next

    def next_paragraph(self, peek=True):
        """
        Returns a copy of what the next paragraph should look like.
        """
        next = self.paragraph_template().next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFParagraph))
        next._call_on_creation_callbacks()
        return next

    def next_paragraph_line(self, peek=True):
        """
        Returns a copy of what the next paragrph line should look like.
        """
        next = self.paragraph_line_template().next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFParagraphLine))
        next._call_on_creation_callbacks()
        return next

    def next_word(self, peek=True):
        """
        Returns a copy of what the next word should look like.
        """
        next = self.word_template().next(peek)
        next.set_text_info(self.merge_text_info(TextInfo(), PDFWord))
        next._call_on_creation_callbacks()
        return next

    # ---------------------------
    # More obvious ways of getting the different templates in the document
    #   hierarchy

    def page_template(self):
        return self.child_template()

    def column_template(self):
        return self.child_template().child_template()

    def paragraph_template(self):
        return self.child_template().child_template().child_template()

    def paragraph_line_template(self):
        return self.child_template().child_template().child_template().child_template()

    def word_template(self):
        return self.child_template().child_template().child_template().child_template().child_template()

class PDFPageTemplate(Template):
    """
    Describes how the current page should look.
    """
    def __init__(self):
        default = PDFPage()

        # Set Defaults for Pages
        default.set_margins(1 * UNIT.INCH, 1 * UNIT.INCH, 1 * UNIT.INCH, 1 * UNIT.INCH)

        default.set_page_size(ToolBox.PAGE_SIZE.LETTER)
        default.set_grid(1, 1)

        super().__init__(default, PDFColumnTemplate())

class PDFColumnTemplate(Template):
    """
    Describes how a column should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        default = PDFColumn()

        super().__init__(default, PDFParagraphTemplate(), reset_children_on_next=False)

class PDFParagraphTemplate(Template):
    """
    Describes how a paragraph should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        default = PDFParagraph()

        def spacing_callback(paragraph):
            par_lines = paragraph.paragraph_lines()

            if len(par_lines) > 0:
                last_line = par_lines[-1]

                if last_line.text_info().alignment() == ALIGNMENT.JUSTIFY:
                    last_line.realign(ALIGNMENT.LEFT)

        default.add_end_callback(spacing_callback)

        super().__init__(default, PDFParagraphLineTemplate())

class PDFParagraphLineTemplate(Template):
    def __init__(self):
        default = PDFParagraphLine()
        super().__init__(default, PDFWordTemplate())

        first_line = default.copy()

        def tab_callback(par_line):
            if par_line.text_info().alignment() == ALIGNMENT.LEFT:
                par_line.set_left_margin(0.5 * UNIT.INCH)

        first_line.add_on_creation_callback(tab_callback)
        self.add_concrete(first_line)

class PDFWordTemplate(Template):
    def __init__(self):
        default = PDFWord()
        super().__init__(default, None)



