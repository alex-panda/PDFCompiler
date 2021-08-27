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

    @abstractmethod
    def __init__(self, token_stream):
        pass

    @abstractmethod
    def place(self):
        """
        Takes in a TokenStream object and begins to place things down on
            token_stream.curr_document() based on the next Token in the TokenStream.
        """

