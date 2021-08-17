from reportlab.lib.units import inch, cm, mm, pica, toLength

import copy
from decimal import Decimal
from abc import ABC, abstractmethod

from placer.templates import PDFDocumentTemplate, PDFDocument, PDFParagraph, PDFParagraphLine, PDFWord, TextInfo
from shapes import Point, Rectangle
from markup import MarkupStart, MarkupEnd, Markup
from constants import ALIGNMENT, TT, PB_NUM_TABS
from toolbox import ToolBox
from tools import exec_python, eval_python, assert_instance, print_progress_bar, prog_bar_prefix, calc_prog_bar_refresh_rate

class Placer(ABC):
    """
    A Placer object creates a PDFDocument object from a list of tokens. The
        PDFDocument.draw() method will be used to actually draw the PDF contents
        to the PDF file.
    """

    @abstractmethod
    def __init__(self, tokens, globals=None, file_path=None, print_progress=False):
        """
        tokens = the list of tokens to be iterated over. They may not all be
            actual Token objects but MarkupStart and MarkupEnd can also be
            in there to change the state of the Placer. Also, there may be
            TT.EXEC_PYTH2 and TT.EVAL_PYTH2 Tokens that need to be run with
            {'placer':self} added to the globals

        globals = a dictionary of globals that should be passed to te exec_python
            and eval_python methods when running a TT.EXEC_PYTH2 or TT.EVAL_PYTH2
            Token

        file_path = a string file path so that the progress bar can know what
            file is being placed (what file is the main/input file). Not much
            use other than the progress bar. It is NOT the output file path.

        print_progress = Whether to actually print a progress bar for how far
            along the placing is.
        """
        #globals.update({'placer':self})

    @abstractmethod
    def create_pdf(self):
        """
        Starts the main loop, iterating over the tokens and creating the pdf.
        """

    # --------------------------------
    # Template Methods

    @abstractmethod
    def curr_document(self):
        pass

    @abstractmethod
    def curr_page(self):
        pass

    @abstractmethod
    def curr_column(self):
        pass

    @abstractmethod
    def curr_paragraph(self):
        pass

    @abstractmethod
    def curr_paragraph_line(self):
        pass

    @abstractmethod
    def curr_template(self):
        """
        Returns the current template being used. This is template [-1] on the
            template stack or, if the stack is empty, the default template.
        """

    @abstractmethod
    def push_template(self, template):
        """
        Pushes a template onto the template stack. Tempalate [-1] is the current
            template or, if the stack is empty, the default template is the
            template to use.
        """

    @abstractmethod
    def pop_template(self):
        """
        Pops a tempalet off the template stack.
        """

    @abstractmethod
    def default_template(self):
        """
        The default template to use when the template stack is empty.
        """

    @abstractmethod
    def set_default_template(self, new_template):
        """
        Sets the default template to another template.
        """

    # ------------------------
    # New PDFComponent Methods

    @abstractmethod
    def new_page(self):
        """
        Starts a new page.
        """

    @abstractmethod
    def new_column(self):
        """
        Starts a new column on the current PDFPage.
        """

    @abstractmethod
    def new_paragraph(self):
        """
        Starts a new Paragraph.
        """

    @abstractmethod
    def new_paragraph_line(self):
        """
        Starts a new Paragraph line.
        """

    @abstractmethod
    def new_word(self, word:str, space_before=True):
        """
        Adds a new word (text) to the current paragraph line.
        """

    # ------------------------
    # Other Methods

    @abstractmethod
    def add_apply_to_canvas_obj(self, apply_to_canvas_obj):
        """
        Adds an object that will be later added to the curr_document (current
            PDFDocument) via
            self.curr_document().add_apply_to_canvas_obj(obj)
        """

