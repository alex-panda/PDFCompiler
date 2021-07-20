from reportlab.lib.units import inch, cm, mm, pica, toLength
from decimal import Decimal

from constants import ALIGN, TT
from tools import assure_decimal
from toolbox import ToolBox


class Point:
    """
    An (x, y) point.
    """
    def __init__(self, x=0, y=0):
        self.set_xy(x, y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def xy(self):
        return self._x, self._y

    def set_xy(self, x, y):
        self._x = assure_decimal(x)
        self._y = assure_decimal(y)

    def set_x(self, x):
        self._set_xy(x, self._y)

    def set_y(self, y):
        self._set_xy(self._x, y)

    def __eq__(self, other):
        return isinstance(other, Point) and self._x == other.x() and self._y == other.y()

    def __add__(self, other):
        other = self._assure_point(other)
        return (self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other):
        other = self._assure_point(other)
        return (self.x() - other.x(), self.y() - other.y())

    def __mult__(self, other):
        other = self._assure_point(other)
        return (self.x() * other.x(), self.y() * other.y())

    def __div__(self, other):
        other = self._assure_point(other)
        return (self.x() / other.x(), self.y() / other.y())

    def _assure_point(self, other):
        if isinstance(other, Point):
            return other
        raise ValueError(f'Tried to compare a point to some other thing that is not a point.\nThe other thing: {other}')

toolbox = ToolBox() # the toolbox to be given to the people compiling the pdf

class Placer:
    """
    The object that actually places tokens onto the PDF depending on the
        templates it is using.
    """
    def __init__(self):
        self._default_page = PDFPageTemplate()
        self._broke_paragraph = True

    def default_page(self):
        return self._default_page

    def default_paragraph(self):
        return self._default_paragraph

    def default_paragraph_line(self):
        return self._default_paragraph_line

    def default_word(self):
        return self._default_word

    def page_count(self):
        return self._page_count

    def place_text(self, text):
        """
        Places the given text onto the pdf with the current templates.
            This text is either in a string or a list of tokens. These tokens
            are all assumed to be plain-text, regardless of what the tokens
            actually represent. The only exception is for PARAGRAPH_BREAKs
            which are required to be given if you want a new paragraph to
            be produced.

        If a string is given, it is tokenized with all references to commands
            and python code ignored and simply not written.
        """

        for i, token in enumerate(text):

            if token.type == TT.PARAGRAPH_BREAK:
                self.new_paragraph()
                continue

            if self._broke_paragraph:
                print('\t', end='')
                self._broke_paragraph = False

                print(f'{token.value}', end='')
            else:
                print(f' {token.value}', end='')

    def new_paragraph(self):
        """
        Stop placing text in the old paragraph and reset everything for the new
            paragraph.
        """
        self._broke_paragraph = True
        print('\n', end='')
        #print('\nNEW PARAGRAPH\n', end='')

class Template:
    def __init__(self):
        self._margins = Margins() # The margins around the text for the template
        self._alignment = None # The alignment of the text in the template
        self._point = None # This is the placement of the upper-left-hand corner of the Template
        self._being_used = False
        self._use_times_left = None

    def can_be_used_again(self):
        """
        Returns true if this Template can be used again.
        """
        return self._use_times_left > 0 or self._use_times_left is None

    def use_times_left(self):
        """
        Returns the number of times this template should continue to be used
            until it is popped off the stack. It will return None if it should
            be used infinitely many more times and if it returns <= 0, then
            it should be popped off the stack.
        """
        return self._use_times_left

    def set_use_times_left(self, num_times_left):
        """
        Sets the number of use times this template has left. If set to None,
             then it has an infinite number of use times left. If set to
             a number that is <= 0, then it has no use times left.
        """
        if not isinstance(num_times_left, (int, Decimal, float, None)):
            raise ValueError(f'You tried to set the number of use times left for this template to a non-number, non-None, value.\nProblem Value: {num_times_left}')
        return self._use_times_left

    def being_used(self):
        """
        Returns true when this template is being actively used to layout a
            paragraph.
        """
        return self._being_used

    def margins(self):
        """
        The margins for the template. They determine how boxed in it is, and
            they are additive. So if you specify the margins of the
            page and the paragraph, the margins of the page are added to the
            paragraph to affect the text
        """
        return self._margins

    def alignment(self):
        return self._alignment

    def set_alignment(self, new_alignment):
        if not isinstance(new_alignment, ALIGN):
            if isinstance(new_alignment, str):
                new_alignment = toolbox.alignments_by_name(new_alignment)
            else:
                raise TypeError(f'You tried to set the alignment of the text to {new_alignment}, which is not in the ALIGN Enum required.')
        self._align = new_alignment

    def copy(self, recursive=False):
        """
        Copies this template. If recursive is True, then it also copies all
            children of it. For example, A PDFPageTemplate will copy all
            of its PDFParagraphTemplates, which will copy all of their
            PDFParagraphLineTemplates, which will copy all of their
            PDFWordTemplates.
        """
        raise NotImplementedError(f'The copy function has not been implemented for class {self.__class__.__name__}')

    # -------------------------------------------------------------------------
    # Helper Methods not in API

    def _start_use(self):
        """
        A method to be run right before the template is used again.

        NOTE: it is this method and not self._end_use() that decrements the
            number of uses this Template has left.
        """
        if self._use_times_left is not None:
            self._use_times_left -= 1
        self._being_used = True

    def _end_use(self):
        """
        This method notifies the Template that it has been used.
        """
        self._being_used = False

class Word:
    """
    Represents a Physical word on the page. You put the text in this, put it
        through each template from most general to least general, and that
        gets you the word as it will be on the page.
    """
    def __init__(self, text):
        self._text = text
        self._point = None
        self._font = None
        self._color = None

    def text(self):
        return self._text

    def placement(self):
        """
        Where the word is on the page in the PDF
        """
        return self._point

    def set_placement(self, point):
        point = self._point._assure_point(point)
        self._point = point

    def font(self):
        return self._font

    def set_font(self, font):
        self._font = font

    def color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    def __eq__(self, other):
        if isinstance(other, Word):
            return (other.text() == self.text())
        elif isinstance(other, str):
            return (self.text() == other)
        else:
            return False


class PDFPageTemplate(Template):
    """
    Describes how the current page should look.
    """
    def __init__(self):
        super().__init__()
        self.margins().set_all(1*inch, 1*inch, 1*inch, 1*inch)
        self._alignment = ALIGN.LEFT

        self._default_paragraph = PDFParagraphTemplate()

        self._page_index = 0

    def default_paragraph(self):
        return self._default_paragraph

    def _place_word(self, word:Word):
        """
        Recursively figures out how to place the next word in the PDF
        """
        self._default_paragraph._place_word(word)

    def copy(self):
        new_page = PDFParagraphTemplate()
        new_page.mangins.set_all(*self.margins().get_all())
        new_page._alignment = self._alignment
        new_page._page_index = self._page_index
        new_page._default_paragraph = self._default_paragraph.copy()
        return new_page

class PDFParagraphTemplate(Template):
    """
    Describes how a paragraph should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        super().__init__()
        self._default_paragraph_line = PDFParagraphLineTemplate()
        self._curr_line_index = 0

        # Paragraphs also have margins that will be added to the margins
        #   provided by the page. So if paragraph left margin is 1in and
        #   page left margin is 1in, the paragraph will be offset from the
        #   left corner of the page by 2 inches

        # The offsets that each LINE of the paragraph will have. These
        #   concrete offsets take precidence over the repeating left
        #   offsets (concrete offsets will be used if both concrete and
        #   repeating offsets apply to the same line). index 0 is line 1 of the
        #   paragraph
        first_par_line = self._default_paragraph_line.copy()
        first_par_line.margins().set_left(Decimal(1 * inch))

        self._concrete_lines = [first_par_line]
        self._repeating_lines = []

    def default_paragraph_line(self):
        return self._default_paragraph_line

    def alignment(self):
        """
        Paragraph alignment, i.e. ALIGN.RIGHT, .LEFT, .CENTER, or .JUSTIFY
        """
        return self._alignment

    def _place_word(self, word:Word):
        self._default_paragraph_line._place_word(word)

    def copy(self):
        new_par = PDFParagraphTemplate()
        new_par._default_paragraph_line = self._default_paragraph_line.copy()
        new_par._curr_line_index = self._curr_line_index
        return new_par

class PDFParagraphLineTemplate(Template):
    def __init__(self):
        super().__init__()
        self._default_word = PDFWordTemplate()

        self._concrete_words = []
        self._repeating_words = []
        self._curr_word_index = 0

    def default_word(self):
        return self._default_word

    def default_word(self):
        return self._default_word

    def _place_word(self, word:Word):
        self._default_word._place_word(word)

    def copy(self):
        new_line = PDFParagraphLineTemplate()
        new_line._default_word = self._default_word.copy()
        return new_line

class PDFWordTemplate(Template):
    """
    A template for each word in a Line of a Paragraph of a Page in the PDF.
    """
    def __init__(self):
        super().__init__()

    def _place_word(self, word:Word):
        pass

    def copy(self):
        new_word = PDFWordTemplate()
        return new_word

class Margins:
    """
    Describes the margins of something.
    """
    def __init__(self, left=-1, right=-1, top=-1, bottom=-1):
        self.set_all(left, right, top, bottom)

    def left(self):
        return self._left

    def set_left(self, new_left):
        if self._valid_margin(new_left):
            self._left = assure_decimal(new_left)

    def right(self):
        return self._right

    def set_right(self, new_right):
        if self._valid_margin(new_right):
            self._right = assure_decimal(new_right)

    def top(self):
        return self._top

    def set_top(self, new_top):
        if self._valid_margin(new_top):
            self._top = assure_decimal(new_top)

    def bottom(self):
        return self._bottom

    def set_bottom(self, new_bottom):
        if self._valid_margin(new_bottom):
            self._bottom = assure_decimal(new_bottom)

    def set_all(self, left=0, right=0, top=0, bottom=0):
        self._left   = assure_decimal(left)
        self._right  = assure_decimal(right)
        self._top    = assure_decimal(top)
        self._bottom = assure_decimal(bottom)

    def copy(self):
        m = Margins()
        m.left = self.left
        m.right = self.right
        m.top = self.top
        m.bottom = self.bottom
        return m

    # -------------------------------------------------------------------------
    # Helper Functions not part of API

    def _valid_margin(self, val):
        """
        Checks that the given margin is of a valid type.
        """
        if isinstance(val, (float, Decimal, int)):
            return True
        else:
            raise TypeError('You tried to set the margins of the page to something other than a float, Decimal, or int.')
