import copy
from decimal import Decimal
from abc import ABC, abstractmethod

from placer.templates import PDFDocumentTemplate, PDFDocument, PDFParagraph, PDFParagraphLine, PDFWord, TextInfo
from shapes import Point, Rectangle
from markup import MarkupStart, MarkupEnd, Markup
from constants import ALIGNMENT, TT, PB_NUM_TABS
from toolbox import ToolBox
from tools import exec_python, eval_python, assert_instance, print_progress_bar, prog_bar_prefix, calc_prog_bar_refresh_rate

from placer.placer import Placer

class NaivePlacer(Placer):
    """
    The object that actually places tokens onto the PDF depending on the
        templates it is using. This is a Naive Placer because it just naively
        tries to place each word line by line, putting the word on the next
        line if the word does not fit on the current line.
    """
    def __init__(self, token_stream):
        self._token_stream = token_stream
        self._last_placed_paragraph_line = None

    def place(self):
        """
        Takes the tokens given to this Object at creation time and creates a PDF.
            This method is run by the compiler to create the actual PDF, IT
            SHOULD NOT BE RUN IN THE PDFO FILE. It returns a PDFDocument that
            you can run the PDFDocument.draw(output_file_name) to actually draw
            it to a file.
        """
        from compiler import Token
        ts = self._token_stream

        while ts.curr_token() is not None:

            ct = ts.curr_token() # Current Token

            if isinstance(ct, Token):
                self._handle_token()
            elif isinstance(ct, (MarkupStart, MarkupEnd)):
                ts.handle_markup()
            else:
                raise Exception(f'Placer cannot handle Token: {ct}')

        cpl = ts.curr_paragraph_line()

        if cpl is not None and cpl.word_count() > 0:
            self._place_curr_paragraph_line()

    def new_paragraph(self):
        """
        Starts a new paragarph, basically just wraps the TokenStream's
            new_paragraph method so that we can call _place_curr_paragraph_line
        """
        cpl = self._token_stream.curr_paragraph_line()

        if cpl is not None and cpl.word_count() > 0:
            self._place_curr_paragraph_line()

        self._token_stream.new_paragraph()

    def new_paragraph_line(self):
        """
        Starts a new paragarph_line, basically just wraps the TokenStream's
            new_paragraph_line method so that we can call
            _place_curr_paragraph_line
        """
        if self._token_stream.curr_paragraph_line() is not None:
            self._place_curr_paragraph_line()

        self._token_stream.new_paragraph_line()

    def new_word(self, word:str, space_before=True):
        """
        Adds a new word (text) to the current paragraph line.
        """
        if len(word) == 0:
            # Don't add words that have nothing in them
            return

        ts = self._token_stream
        ct = ts.curr_template()
        next_word = ct.next_word(peek=False)
        next_word.set_text(word)
        next_word.set_space_before(space_before)

        curr_words = [next_word]
        refresh_words = False

        # actually add the word to the current paragraph line if possible,
        #   otherwise add it to the next paragraph line.
        for i in range(9999):
            # Find next column if there is not one currently
            cc = ts.curr_column()
            if cc is None:
                ts.new_column() # Make sure that a column is found
                cc = ts.curr_column()

            # Create a new paragraph line if there is not one currently (it is
            #   added to the current paragraph but not current Column)

            cp = ts.curr_paragraph()
            if cp is None:
                self.new_paragraph()
                cp = ts.curr_paragraph()

            cpl = ts.curr_paragraph_line()
            if cpl is None:
                self.new_paragraph_line()
                cpl = ts.curr_paragraph_line()
                refresh_words = True

            if refresh_words:
                # Now refresh curr_words to match what should be on the current
                #   line
                for word in curr_words:
                    word.set_text_info(ct.next_word(peek=False).text_info())

            # Now try to place the word in the current paragraph line
            curr_words, need_new_col, width_used = \
                    self._add_words_to_line(cp, cpl, curr_words, cc.available_area().size())

            if cpl.word_count() > 0 and width_used and not need_new_col:
                self._place_curr_paragraph_line()

            if need_new_col:
                ts.new_column()
                continue
            elif width_used:
                self.new_paragraph_line()
                refresh_words = True
                continue

            break
        else:
            raise AssertionError(f'Could not place word "{word}" even though it was given 9999 tries. You probably have all the margins of your paper so large that there is nowhere for even a single letter of the word to be put on the PDF.')

    # ------------------------
    # Public and Private Methods For Advanceing and Processing Tokens

    def _handle_token(self):
        """
        The state that is entered when a token is being handled.
        """
        ct = self._token_stream.curr_token()
        tt = ct.type

        result = None

        if tt == TT.PARAGRAPH_BREAK:
            #self.new_word('<BREAK>', True) # For debug purposes
            self.new_paragraph()
        elif tt in (TT.EXEC_PYTH2, TT.EVAL_PYTH2):
            self._token_stream.handle_python_token()
        else:
            self.new_word(ct.value, ct.space_before)

        self._token_stream.advance()

    # -----------------
    # Public and Private Placement Methods

    # These methods are here so that the methods used to actually place the data
    #   are centralized and easy to change when needed (you don't have to jump
    #   to a bunch of class definitions because the classes just house data, not
    #   manipulate it, for the most part)

    def _place_curr_paragraph_line(self, replace_with_none=True):
        """
        Takes the current PDFParagraphLine and adds it to the current column,
            then it sets the current paragraph_line to None

        If the current paragraph_line is already None, it places an empty
            paragraph line onto the current column with the same height
            as the last one.
        """
        ts = self._token_stream
        if ts.curr_column() is None:
            ts.new_column()

        if ts.curr_paragraph() is None:
            self.new_paragraph()

        cc = ts.curr_column()
        cp = ts.curr_paragraph()
        cpl = ts.curr_paragraph_line()

        if cpl is None or cpl.word_count() == 0:
            cpl = ts.curr_template().next_paragraph_line(peek=False)
            # We have to make a new PDFParagraphLine with either the same size
            #   as the last one or a completely new size
            if ts.prev_paragraph_line() is not None:
                cpl.set_total_height(ts.prev_paragraph_line().total_height())
            else:
                # Just set it to a default height
                cpl.set_total_height(cpl.text_info().font_size()) # Makes it the same height as 12 point font

            cpl.set_total_width(0)
        else:
            # Word count must be > 0
            offset = cc.inner_offset() + Point(0, cc.height_used())

            cp.set_total_offset(offset)
            offset = cp.inner_offset()

            cpl.set_total_offset(offset)

            self._token_stream.place_words_with_alignment(cpl, cpl.text_info().alignment())

        ts._prev_paragraph_line = cpl

        # This adds the total height of the line to the cc.height_used()
        #   and adds th paragraph line to the column
        cc._add_paragraph_line(cpl)

        cpl._set_parent_column(cc)

        cp._add_paragraph_line(cpl)
        cpl._set_parent_paragraph(cp)

        for word in cpl._pdfwords:
            word._set_parent_paragraph_line(cpl)

        ts._curr_paragraph_line = None

        if not replace_with_none:
            self.new_paragraph_line()

    # Private methods for PDFParagraphLine

    @staticmethod
    def _add_words_to_line(pdf_paragraph, pdf_paragraph_line, list_of_pdfwords, column_available_size):
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
        pp = pdf_paragraph
        ppl = pdf_paragraph_line

        # Make the size smaller according to the margins of the current
        #   paragraph
        pp.set_total_size(column_available_size)
        ppl.set_total_size(pp.inner_size())

        available_width, available_height = ppl.inner_size()
        width_used = False
        height_used = False
        leftover_words = []

        curr_height = 0

        for word in list_of_pdfwords:
            assert_instance(word, PDFWord, 'pdfword', or_none=False)

            if width_used:
                leftover_words.append(word)
                continue

            # Try to add the word but if the paragraph_line is now too long
            #   with it added, remove the word and append it to the leftover
            #   words so that it can be added to the next paragraph line

            ppl.append_word(word)

            curr_height = ppl.curr_height()

            if ppl.curr_width() > available_width:
                leftover_words.append(ppl.pop_word())
                width_used = True
                continue

            if curr_height > available_height:
                # Width was fine but this line's height is too much so need to
                #   put all these words on the next line (reached bottom of the
                #   PDFColumn).
                height_used = True
                break

        if height_used:
            # Return all the words in this line, both already on the line and
            #   trying to be added to the line.
            leftover_words = ppl._pdfwords

            for word in list_of_pdfwords:
                if not (word in leftover_words):
                    leftover_words.append(word)

            ppl._pdfwords = []
            return leftover_words, True, width_used

        ppl.set_inner_height(curr_height)

        return (leftover_words, False, width_used) if len(leftover_words) > 0 else (None, False, width_used)
