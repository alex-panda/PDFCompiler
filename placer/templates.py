from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor, Color, CMYKColor

from tools import assure_decimal
from constants import TT, ALIGNMENT, ALIGNMENT, SCRIPT, STRIKE_THROUGH, UNDERLINE

from shapes import Point, Rectangle

from toolbox import ToolBox
from decimal import Decimal

def assert_instance(obj, types, var_name=None, or_none=True):
    if not (isinstance(obj, types) or (or_none and obj is None)):
        if var_name is None:
            var_name = 'This'
        string = f'{var_name} is supposed to be one of these types: {types}'

        if or_none:
            string += ' or None'

        string += f'\nbut it was {obj}'
        raise AssertionError(string)

def assert_subclass(obj, types, var_name=None, or_none=True):
    obj = type(obj)
    if not issubclass(obj, types) or (or_none and obj is None):
        if var_name is None:
            var_name = 'This'
        string = f'{var_name} is supposed to be a subclass of {types}'

        if or_none:
            string += ' or None'

        string += f'\nbut it was {obj}'
        raise AssertionError(string)

def draw_str(canvas:Canvas, point:Point, string:str):
    """
    Draws a string at the given Point on the given canvas.
    """
    #print(f'{point}, {string}')
    canvas.drawString(float(point.x()), float(point.y()), string)


class TextInfo:
    __slots__ = ['_script', '_alignment', '_line_spacing',
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
        assert_instance(new, SCRIPT, 'script')
        self._script = new

    def alignment(self):
        return self._alignment

    def set_alignment(self, new):
        assert_instance(new, ALIGNMENT, 'alignment')
        self._alignment = new

    def line_spacing(self):
        return self._line_spacing

    def set_line_spacing(self, new):
        assert_instance(new, (int, Decimal, float), 'line_spacing')
        self._line_spacing = new

    # ---------

    def font_name(self):
        return self._font_name

    def set_font_name(self, new):
        assert_instance(new, (TTFont, str), 'font_name')
        self._font_name = new

    def font_size(self):
        return self._font_size

    def set_font_size(self, new):
        assert_instance(new, int, 'font_size')
        self._font_size = new

    def font_color(self):
        return self._font_color

    def set_font_color(self, new):
        assert_instance(new, (Color, CMYKColor), 'font_color')
        self._font_color = new

    def font_color_gray(self):
        return self._font_color_gray

    def set_font_color_gray(self, new):
        assert_instance(new, (float, int), 'font_color_gray')
        if new is not None:
            assert 0.0 <= new <= 1.0, f'font_color_gray must be between 0 and 1 inclusive, not {new}'
        self._font_color_gray = new

    def font_color_alpha(self):
        return self._font_color_alpha

    def set_font_color_alpha(self, new):
        assert_instance(new, (float, int), 'font_color_alpha')
        if new is not None:
            assert 0.0 <= new <= 1.0, f'font_color_alpha must be between 0 and 1 inclusive, not {new}'
        self._font_color_alpha = new

    def font_highlight_color(self):
        return self._font_highlight_color

    def set_font_highlight_color(self, new):
        assert_instance(new, (Color, CMYKColor), 'font_highlight_color')
        self._font_highlight_color = new

    # ---------

    def underline(self):
        return self._underline

    def set_underline(self, new):
        assert_instance(new, UNDERLINE, 'underline')
        self._underline = new

    def font_strikethrough(self):
        return self._strikethrough

    def set_strikethrough(self, new):
        assert_instance(new, STRIKE_THROUGH, 'font_strikethrough')
        self._strikethrough = new

    # ---------

    def bold(self):
        return self._bold

    def set_bold(self, boolean):
        assert_instance(boolean, bool, 'bold')
        self._bold = boolean

    def italics(self):
        return self._italics

    def set_italics(self, boolean):
        assert_instance(boolean, bool, 'italics')
        self._italics = boolean

    def can_split_words(self):
        return self._can_split_words

    def set_can_split_words(self, boolean):
        assert_instance(boolean, bool, 'can_split_words')
        self._can_split_words = boolean

    # --------------------------
    # Non-getter-setter Methods

    def merge(self, other_text_info):
        """
        Merges this TextInfo with another so that this one changes its attributes
            to match all the NON-None attributes of the other one.
        """
        if other_text_info is None:
            return

        for atr in self.__slots__:
            if getattr(other_text_info, atr) is not None:
                setattr(self, atr, getattr(other_text_info, atr))

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

    def apply_to_canvas(self, canvas):
        # Handle Font nam and Font Size
        fn, fs = self.font_name(), self.font_size()

        if fn is not None or fs is not None:
            if not (fn is not None and fs is not None):
                raise AssertionError(f'Either font size or font name was set but the other one was not set. If font size or font name are set, both must be set to a non-None value.\nfont_name: {fn}\nfont_size: {fs}\n')

            canvas.setFont(fn, fs)

        # Handle font color
        fc = self.font_color()
        assert_instance(fc, (CMYKColor, Color), 'font_color')

        if fc is not None:
            canvas.setFillColor(fc)

        fca = self.font_color_alpha()
        if fca is not None:
            canvas.setFillAlpha(fca)

        fcg = self.font_color_gray()
        assert_instance(fcg, float, 'font_color_gray')

        if fcg is not None:
            assert 0.0 <= fcg <= 1.0, f'font_color_gray values must be between 0 and 1 inclusive, not {fcg}'
            canvas.setFillGray(fcg)

class HasTextInfo:
    def __init__(self):
        self._text_info = TextInfo()

    def text_info(self):
        return self._text_info

    def set_text_info(self, new):
        assert_instance(new, TextInfo, 'text_info')
        self._text_info = new

class PDFComponent(HasTextInfo):
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

        # A list of the callbacks that will be called after this PDFComponent
        #   receives its final placement on the PDF
        self._placed_callbacks = []

        # A list of callbacks that will be called after the entirety of the
        #   PDFDocument has been placed.
        self._end_callbacks = []

    # --------------
    # Margins Start

    def left_margin(self):
        return self._left_margin

    def set_left_margin(self, new_left):
        inner_size, inner_offset= self.inner_size(), self.inner_offset()
        self._left_margin = assure_decimal(new_left)
        self.set_inner_size(inner_size); self.set_inner_offset(inner_offset)

    def right_margin(self):
        return self._right_margin

    def set_right_margin(self, new_right):
        inner_size, inner_offset= self.inner_size(), self.inner_offset()
        self._right_margin = assure_decimal(new_right)
        self.set_inner_size(inner_size); self.set_inner_offset(inner_offset)

    def top_margin(self):
        return self._top_margin

    def set_top_margin(self, new_top):
        inner_size, inner_offset= self.inner_size(), self.inner_offset()
        self._top_margin = assure_decimal(new_top)
        self.set_inner_size(inner_size); self.set_inner_offset(inner_offset)

    def bottom_margin(self):
        return self._bottom_margin

    def set_bottom_margin(self, new_bottom):
        inner_size, inner_offset= self.inner_size(), self.inner_offset()
        self._bottom_margin = assure_decimal(new_bottom)
        self.set_inner_size(inner_size); self.set_inner_offset(inner_offset)

    def margins(self):
        return self.left_margin(), self.right_margin(), self.top_margin(), self.bottom_margin()

    def set_margins(self, left=0, right=0, top=0, bottom=0):
        """
        Sets all the margins for the PDFComponent.
        """
        inner_size, inner_offset= self.inner_size(), self.inner_offset()
        self._left_margin = assure_decimal(left)
        self._right_margin = assure_decimal(right)
        self._top_margin = assure_decimal(top)
        self._bottom_margin = assure_decimal(bottom)
        self.set_inner_size(inner_size); self.set_inner_offset(inner_offset)

    # Margins End
    # --------------

    def placed_callbacks(self):
        return self._placed_callbacks

    def add_placed_callback(self, callback):
        """
        Adds a placed callback to the PDFComponent. This callback function will
            be called and given this PDFComponent when the PDFComponent is
            placed for the final time and will not be messed with further by
            the placer.
        """
        self._placed_callbacks.append(callback)

    def _call_placed_callbacks(self):
        """
        Runs all the placed callbacks for this PDFComponent
        """
        for callback in self._placed_callbacks:
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

    def total_rect(self):
        rect = Rectangle()
        rect.set_point(self.total_offset())
        rect.set_size(self.total_size())
        return rect

    def inner_rect(self):
        rect = Rectangle()
        rect.set_point(self.inner_offset())
        rect.set_size(self.inner_size())
        return rect

    def set_total_offset(self, x, y=None):
        """
        Sets the total offset of the component (so the offset that includes the
            margins)
        """
        if y is not None:
            x = Point(x, y)
        else:
            Point._assure_point(x)

        self.set_inner_offset(x + Point(self.left_margin(), self.top_margin()))

    def total_offset(self):
        return self.inner_offset() - Point(self.left_margin(), self.top_margin())

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

        self._rect.set_point(x)

    def inner_offset(self):
        """
        Returns the Point object that represents an offset from the top-left
            corner of the Page the component is on.
        """
        return self._rect.point().copy()

    def set_inner_size(self, height, width=None):
        """
        Sets the size of the component inside the margins.
        """
        self._rect.set_size(height, width)

    def inner_size(self):
        return (self.inner_height(), self.inner_width())

    def set_inner_height(self, height):
        self._rect.set_height(height)

    def set_inner_width(self, width):
        self._rect.set_width(width)

    def inner_height(self):
        """
        Height inside margins.
        """
        return self._rect.height()

    def inner_width(self):
        """
        Width inside margins.
        """
        return self._rect.width()

    def set_total_size(self, height, width=None):
        """
        Sets the size of the component with margins taken into account.
        """
        if width is None:
            width = height[1]
            height = height[0]

        self.set_total_width(width)
        self.set_total_height(height)

    def total_size(self):
        return (self.total_height(), self.total_width())

    def set_total_height(self, height):
        self.set_inner_height(height - self.top_margin() - self.bottom_margin())

    def set_total_width(self, width):
        self.set_inner_width(width - self.left_margin() - self.right_margin())

    def total_height(self):
        """
        Height with margins.
        """
        return self.inner_height() + self.top_margin() + self.bottom_margin()

    def total_width(self):
        """
        Width with margins.
        """
        return self.inner_width() + self.left_margin() + self.right_margin()

    def copy(self):
        new = self.__class__()
        new.set_inner_size(self.inner_size())
        new.set_inner_offset(self.inner_offset())
        new.set_margins(*self.margins())
        new.set_text_info(self.text_info().copy())
        return new

    def clear(self):
        self._rect.clear()
        self.set_margins(0, 0, 0, 0)
        self.text_info().clear()

class PDFDocument(PDFComponent):
    def __init__(self):
        super().__init__()
        self._pages = []

    def page_count(self):
        return len(self._pages)

    def pages(self):
        return self._pages

    def draw(self, output_file_path_or_canvas):
        """
        Draws the PDFDocument either to a canvas or to the output_file_path
        """
        if isinstance(output_file_path_or_canvas, Canvas):
            canvas = output_file_path_or_canvas
        else:
            canvas = Canvas(output_file_path_or_canvas, bottomup=0)

        for page in self._pages:
            page.draw(canvas)

        canvas.save()

    def _add_page(self, page):
        assert_instance(page, PDFPage)
        page.set_parent(self)
        self._pages.append(page)
        page._page_num = self.page_count()
        page._call_placed_callbacks()

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for page in self._pages:
            page._call_end_callbacks()

    def __repr__(self):
        return f'{self.__class__.__name__}(pages={self._pages})'

class PDFPage(PDFComponent):
    def __init__(self):
        super().__init__()
        self._num_rows = 1
        self._num_cols = 1
        self._page_num = None
        self._fill_rows_first = False
        self._cols = []

        self._curr_col_idx = -1 # The index of the Column that the Placer is currently putting ParagraphLines in

    def page_size(self):
        return self.total_size()

    def set_page_size(self, height, width=None):
        """
        Sets the page size for this page. You can either use a tuple of height,
            width or you can give the height and width directly.
        """
        self.set_total_size(height, width)

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

    def set_grid(self, num_cols, num_rows):
        """
        Sets how many rows and columns of Column objects should be created to
            hold the text.
        """
        self.set_num_cols(num_cols)
        self.set_num_rows(num_rows)

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

    def _create_cols(self, template):
        """
        Creates the PDFColumn objects for this PDFPage.
        """
        assert len(self._cols) == 0, f'The columns for this page have already been created. Number of PDFColumns: {len(self._cols)}'
        assert self._num_rows >= 0 and self._num_cols >= 0, f'The numbers of columns and rows for a PDFPage must both be atleast 0. They are (row_count, column_count): ({self._num_rows}, {self._num_cols})'

        if self._num_rows == 0 or self._num_cols == 0:
            # No need to create any Column objects whatsoever
            return

        col_width = self.inner_width() / self._num_cols
        col_height = self.inner_height() / self._num_rows

        curr_x_offset, curr_y_offset = self.inner_offset().xy()

        # create the Column objects and place them on the page.
        for i in range(self._num_rows * self._num_cols):
            # Create new column
            next_col = template.next_column(peek=False)

            # Place the column
            next_col.set_total_offset(curr_x_offset, curr_y_offset)
            next_col.set_total_size(col_height, col_width)
            next_col.set_parent(self)

            # Add the column to the list of columns
            self._cols.append(next_col)

            # Figure out where the next column will be placed.
            if self.fill_rows_first():
                curr_x_offset += col_width

                # If have reached the last column, start next row
                if ((i + 1) % self._num_cols) == 0:
                    curr_y_offset += col_height
                    curr_x_offset = 0

            else:
                curr_y_offset += col_height

                # If have reached last column (not Column object but the last
                #   column of the grid of Column objects) then start next
                #   column
                if ((i + 1) % self._num_rows) == 0:
                    curr_x_offset += col_width
                    curr_y_offset = 0

        for col in self._cols:
            col._call_placed_callbacks()

    def _next_column(self):
        """
        returns the next Column that the placer should put text lines into or
            None if there are no more Columns on this Page.
        """
        self._curr_col_idx += 1
        return self._cols[self._curr_col_idx] if self._curr_col_idx < len(self._cols) else None

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for col in self._cols:
            col._call_end_callbacks()

    def draw(self, canvas):
        canvas.setPageSize(self.page_size())

        for col in self._cols:
            col.draw(canvas)

        canvas.showPage()

    def __repr__(self):
        return f'{self.__class__.__name__}(columns={self._cols})'

class PDFColumn(PDFComponent):
    def __init__(self):
        super().__init__()
        self._paragraph_lines = []
        self._height_used = 0

    def _call_end_callbacks(self):
        super()._call_end_callbacks()

        for par_line in self._paragraph_lines:
            par_line._call_end_callbacks()

    def add_paragraph_line(self, paragraph_line):
        """
        Adds a paragraph line to this PDFColumn. The PDFColumn must be fully
        initialized with all the words that will be in it in it.
        """
        self._paragraph_lines.append(paragraph_line)
        #print(f'{self.total_offset()}, {paragraph_line.total_height()} * {paragraph_line.text_info().line_spacing()}, {self.height_used()}')
        paragraph_line.set_total_offset(self.total_offset() + Point(0, self.height_used()))
        paragraph_line.place_words()
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
        x, y = self.total_offset().xy()
        height, width = self.total_size()

        return Rectangle(x, y + self.height_used(), height - self.height_used(), width)

    def draw(self, canvas):
        for pl in self._paragraph_lines:
            pl.draw(canvas)

    def __repr__(self):
        return f'{self.__class__.__name__}(paragraph_lines={self._paragraph_lines})'

class PDFParagraph(PDFComponent):
    def __init__(self):
        super().__init__()
        self._space_between_lines = 0
        self._paragraph_lines = []

    def add_paragraph_line(self, line):
        assert_instance(line, PDFParagraphLine, or_none=False)
        self._paragraph_lines.append(line)

    def __repr__(self):
        return f'{self.__class__.__name__}(paragraph_lines={self._paragraph_lines})'

class PDFParagraphLine(PDFComponent):
    def __init__(self):
        super().__init__()
        self._pdfwords = []

    def word_count(self):
        return len(self._pdfwords)

    def place_words(self):
        """
        Actually places the words currently in this ParagrahLine depending on
            what alignment this paragraph line is using.
        """
        align = self.text_info().alignment()

        # Align the words left
        offset = self.inner_offset().copy()
        for word in self._pdfwords:
            word.set_total_offset(offset)
            offset += Point(word.total_width(), 0)

        if align == ALIGNMENT.CENTER:
            # Now nudge the words that are aligned left to the right so that
            # they are centered
            nudge_amt = (self.inner_width() - self._curr_words_width()) / 2

            for word in self._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.RIGHT:
            # Now nudge the words that are aligned left to the right so that
            # they are right aligned
            nudge_amt = self.inner_width() - self._curr_words_width()

            for word in self._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.JUSTIFIED:
            # Now nudge each word to the right so that they are equally spaced
            nudge_amt = (self.inner_width() - self._curr_words_width()) / len(self._pdfwords) - 1

            for i, word in enumerate(self._pdfwords):
                if i != 0:
                    word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align != ALIGNMENT.LEFT:
            raise AssertionError(f'This PDFParagraphLine was had alignment {align}, which is not a valid alignment.')

    def add_words(self, list_of_pdfwords):
        """
        Uses current inner_width to place the list of words

        If all words could be placed, then None is returned, otherwise a list
            of the words that could not be placed is returned.

        Before this method is run, the line should have its inner_size set to
            what is AVAILABLE for the line to use, and this method will set
            the size back to what it actually used after it adds as many words
            as possible.

        In addition to the words that it could not place, this method will
            also return True if the line used up all if its available height
            and False otherwise.
        """
        available_height, available_width = self.inner_size()
        width_used = False
        height_used = False
        leftover_words = []

        for word in list_of_pdfwords:
            assert_subclass(word, InlinePDFObj, 'pdfword', or_none=False)

            if width_used:
                leftover_words.append(word)
                continue

            # Try to add the word but if the paragraph_line is now too long
            #   with it added, remove the word and append it to the leftover
            #   words so that it can be added to the next paragraph line

            self._pdfwords.append(word)

            if self.curr_words_width() > available_width:
                leftover_words.append(self._pdfwords.pop())
                width_used = True

            if self.curr_words_height() > available_height:
                # Width was fine but this line's height is too much so need to
                #   put all these words on the next line (reached bottom of the
                #   PDFColumn).
                height_used = True
                break

        if height_used:
            # Return all the words in this line, both already on the line and
            #   trying to be added to the line.
            words = self._pdfwords

            for word in list_of_pdfwords:
                if not (word in words):
                    words.append(word)

            self._pdfwords = []

            return words, True, width_used

        self.set_inner_size(self.curr_words_width(), self.curr_words_height())

        return leftover_words if len(leftover_words) > 0 else None, False, width_used

    def curr_words_width(self):
        """
        Returns the current width of this ParagraphLine according to the words
            currently in it.

        NOTE: This method iterates through all the words in this
            PDFParagraphLine every single time it is run.
        """
        total_width = 0
        last_word_idx = len(self._pdfwords) - 1

        for i, word in enumerate(self._pdfwords):
            if i == last_word_idx:
                word.set_space_after(False)
            else:
                word.set_space_after(True)

            word.calc_dims()

            total_width += word.total_width()

        return total_width

    def curr_words_height(self):
        """
        Returns the current height of this PDFParagraphLine according to the
            words currently in it.

        NOTE: This method iterates through all the words in this
            PDFParagraphLine every single time it is run.
        """
        height = 0

        for word in self._pdfwords:
            word.calc_dims()

            word_height = word.total_height()
            word_height += word.total_offset().y() - self.total_offset().y()

            if word_height > height:
                height = word_height

        return height

    def draw(self, canvas):
        line_height = self.inner_height()

        for word in self._pdfwords:
            word.draw(canvas, line_height)

    def __repr__(self):
        return f'{self.__class__.__name__}(words={self._pdfwords})'

class InlinePDFObj(PDFComponent):
    def calc_dims(self):
        """
        Calculate the dimensions of the PDF object (if needed).
        """
        raise NotImplementedError()

    def height(self):
        """
        Returns the Height of the PDFObject
        """
        raise NotImplementedError()

    def width(self):
        """
        Returns the Width of the PDFObject
        """
        raise NotImplementedError()

class PDFWord(InlinePDFObj):
    def __init__(self):
        super().__init__()
        self._text = ''
        self._space_after = False

    def text(self):
        """
        Returns the Text that this word contains. If space_after is true, then
            a space will be appended to the text that is returned.
        """
        if self._space_after:
            return self._text + ' '
        else:
            return self._text

    def set_text(self, text):
        self._text = text

    def space_after(self):
        """
        Whether there should be a space after the word.
        """
        return self._space_after

    def set_space_after(self, boolean):
        self._space_after = boolean

    def calc_dims(self):
        """
        Calculate the dimensions of this word with its current TextInfo.

        space_after must be set to True if you want the space after the word to
            be taken into account when this method calculates the dimensions of
            this PDFWord
        """
        from reportlab.pdfbase.pdfmetrics import stringWidth
        font_name = self.text_info().font_name()
        font_size = self.text_info().font_size()
        self.set_inner_height(Decimal(1.2) * font_size)

        self.set_inner_width(stringWidth(self.text(), font_name, font_size))

    def draw(self, canvas, line_height=None):
        """
        Draw the Word to the given canvas.
        """
        self.text_info().apply_to_canvas(canvas)
        draw_point = self.inner_offset()

        if line_height is not None:
            draw_point += Point(0, line_height)

        draw_str(canvas, draw_point, self.text())

    def __repr__(self):
        return f'{self.__class__.__name__}(text={self.text()})'


class Template:
    """
    Templates are used as factories to figure out what the current page/column/
        paragraph/paragraph line/word is supposed to look out by creating the
        objects for them.
    """
    def __init__(self, default, child_template):
        self._concretes = []
        self._repeating = []

        self._state_index = 0

        self._callbacks = []

        self._child_template = child_template
        self._default = default # What PDFComponent is this a template for?
        self._template_for_type = type(default)

        self._curr_instance = None

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

        if self.child_template() is None or next == end_template_type:
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
        i = self._state_index

        if not peek:
            self._state_index += 1

        if copy:
            if i in self._concretes:
                return self._concretes[i].copy()
            elif i in self._repeating:
                return self._repeating[i].copy()
            else:
                return self._default.copy()
        else:
            if i in self._concretes:
                return self._concretes[i]
            elif i in self._repeating:
                return self._repeating[i]
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

    def being_used(self):
        """
        Returns true when this template is being actively used to layout a
            paragraph.
        """
        return self._being_used

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
        new.set_margins(*self.margins())
        new._alignment = self._alignment
        new._default = self._default.copy()
        new._concretes = [c.copy() for c in self._concretes]
        new._repeating = [r.copy() for r in self._repeating]
        new._state_index = self._state_index
        new._child_template = self._child_template.copy()
        return new

    # -------------------------------------------------------------------------
    # Helper Methods not in API

    def _assert_child(self, obj, or_none=False):
        assert_instance(obj, self._template_for_type, or_none=or_none)

    def _next_state(self):
        self._state_index += 1

    def _reset_state(self):
        self._state_index = 0

        if self.child_template():
            self.child_template()._reset_state()

    def _copy_state_indexes(self, other_template):
        """
        Sets the state indexes of this template to the state indexes of the
            given template.
        """
        self._state_index = other_template._state_index

        if self._child_template and other_template._child_template:
            self._child_template._copy_state_indexes(other_template._child_template)

class PDFDocumentTemplate(Template):
    def __init__(self):
        default = PDFDocument()

        # Set Defaults for text on the pages
        t = default.text_info()
        t.set_script(SCRIPT.NORMAL)
        t.set_alignment(ALIGNMENT.LEFT)

        t.set_font_name('Times-Roman')
        t.set_font_size(12)
        t.set_font_color(ToolBox.colors().black)
        t.set_font_color_gray(None)
        t.set_font_color_alpha(1)
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
        text_info = self.merge_text_info(TextInfo(), PDFPage)
        next_doc = self.next(peek)
        next_doc.set_text_info(text_info)
        return next_doc

    def next_page(self, peek=True):
        """
        Returns a copy of what the next page should look like.
        """
        text_info = self.merge_text_info(TextInfo(), PDFPage)
        next_page = self.page_template().next(peek)
        next_page.set_text_info(text_info)
        return next_page

    def next_column(self, peek=True):
        """
        Returns a copy of what the next column should look like.
        """
        text_info = self.merge_text_info(TextInfo(), PDFColumn)
        next_column = self.column_template().next(peek)
        next_column.set_text_info(text_info)
        return next_column

    def next_paragraph(self, peek=True):
        """
        Returns a copy of what the next paragraph should look like.
        """
        text_info = self.merge_text_info(TextInfo(), PDFParagraph)
        next_paragraph = self.paragraph_template().next(peek)
        next_paragraph.set_text_info(text_info)
        return next_paragraph

    def next_paragraph_line(self, peek=True):
        """
        Returns a copy of what the next paragrph line should look like.
        """
        text_info = self.merge_text_info(TextInfo(), PDFParagraphLine)
        next_paragraph_line = self.paragraph_line_template().next(peek)
        next_paragraph_line.set_text_info(text_info)
        return next_paragraph_line

    def next_word(self, peek=True):
        """
        Returns a copy of what the next word should look like.
        """
        text_info = self.merge_text_info(TextInfo(), PDFWord)
        next_word = self.word_template().next(peek)
        next_word.set_text_info(text_info)
        return next_word

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
        default.set_margins(1*inch, 1*inch, 1*inch, 1*inch)
        default.set_page_size(ToolBox.page_sizes().A4)
        default.set_grid(1, 1)

        super().__init__(default, PDFColumnTemplate())

class PDFColumnTemplate(Template):
    """
    Describes how a column should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        default = PDFColumn()
        super().__init__(default, PDFParagraphTemplate())


class PDFParagraphTemplate(Template):
    """
    Describes how a paragraph should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        default = PDFParagraph()
        super().__init__(default, PDFParagraphLineTemplate())
        first_par_line = default.copy()
        first_par_line.set_left_margin(Decimal(1 * inch))

        self.add_concrete(first_par_line)

class PDFParagraphLineTemplate(Template):
    def __init__(self):
        default = PDFParagraphLine()
        super().__init__(default, PDFWordTemplate())

class PDFWordTemplate(Template):
    def __init__(self):
        default = PDFWord()
        super().__init__(default, None)

