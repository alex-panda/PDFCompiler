from reportlab.lib.units import inch, cm, mm, pica, toLength

import copy
from decimal import Decimal

from placer.templates import PDFDocumentTemplate, PDFDocument, PDFParagraph, PDFParagraphLine, PDFWord, TextInfo
from shapes import Point, Rectangle
from markup import MarkupStart, MarkupEnd, Markup
from constants import ALIGNMENT, TT
from toolbox import ToolBox
from tools import exec_python, eval_python, assert_instance

toolbox = ToolBox() # the toolbox to be given to the people compiling the pdf

class Placer:
    """
    The object that actually places tokens onto the PDF depending on the
        templates it is using.
    """
    def __init__(self, tokens, globals=None):
        self._tokens = tokens
        self._tok_idx = -1
        self._current_tok = None
        self._advance()

        # The templates that determine the things like color, boldness, size, etc.
        #   of the current word.
        self._default_template = PDFDocumentTemplate()
        self._template_stack = []

        # The actual PDFDocument that determines how everything is placed
        self._curr_document = None # Only one PDF document, but just to keep it standard it is call _curr_document
        self._curr_page = None
        self._curr_column = None
        self._curr_paragraph = None
        self._curr_paragraph_line = None

        self._last_placed_paragraph_line = None

        if globals is None:
            self._globals = {'placer':self}
        else:
            self._globals = copy.deepcopy(globals)
            self._globals['placer'] = self

    # ------------------------
    # Public Methods

    def curr_document(self):
        """
        Returns the current document. There is only one document per PDF, but
            just to keep it standard (like the other methods) it is called
            "curr_document"
        """
        return self._curr_document

    def curr_page(self):
        return self._curr_page

    def curr_column(self):
        return self._curr_column

    def curr_paragraph(self):
        return self._curr_paragraph

    def curr_paragraph_line(self):
        return self._curr_paragraph_line

    def curr_template(self):
        """
        Returns the current template being used.
        """
        if len(self._template_stack) > 0:
            return self._template_stack[-1]
        else:
            return self._default_template

    def push_template(self, template):
        """
        Push a template onto the template stack. Make sure to call pop_template
            later when the template is done being used.
        """
        assert isinstance(PDFDocumentTemplate), f'All templates pushed onto the Template stack must be of type PDFDocumentTemplate, not {template}.'
        template.sync_indexes_with(self.curr_template())
        self._template_stack.append(template)

    def pop_template(self):
        """
        Pops a template off the template stack.
        """
        popped = self._template_stack.pop()
        self.curr_template().sync_indexes_with(popped)
        return popped

    def default_template(self):
        return self._default_template

    def set_default_template(self, new_template):
        assert isinstance(PDFDocumentTemplate), f'The default template must be of type PDFDocumentTemplate, not {new_template}'
        self._default_template = new_template

    # ---------------------------
    # Public Methods for Starting New PDF Elements

    # Note: these new_pdf object methods each create whatever they depend on
    #   but also set what depends on them to None. For example, the current
    #   PDFColumn depends on the current page, so if a new page is called
    #   then it sets the current PDFColumn to None

    def _new_document(self):
        """
        Start a new PDFDocument. Should only be called once by the Placer,
            this method should NOT be called in any .pdfo file.
        """
        self._curr_document = self.curr_template().next_document(peek=False)
        self._curr_page = None
        self._curr_column = None
        self._curr_paragraph = None
        self._curr_paragraph_line = None

    def new_page(self):
        """
        Start a new Page of the Document
        """
        if self.curr_document() is None:
            self._new_document()

        if self.curr_page() is not None:
            # Go throught he PDFColumns of the current template as if each of the
            #   PDFColumns that should be on the current page were actually put
            #   on it.
            while self.curr_page()._next_column_rect() is not None:
                self.new_column()

        self._curr_page = self.curr_template().next_page(peek=False)

        self.curr_document()._add_page(self._curr_page)
        self._curr_page._set_parent_document(self.curr_document())

        self._create_col_rects(self._curr_page)
        self._curr_column = None

    def new_column(self):
        """
        If curr_column() is None after calling this method, that means that the
            current page has no more culumns on it, so you must call new_page
            and then check to see if that page has a column on it by seeing
            if curr_column() is None again after calling new_page()
        """
        if self.curr_page() is None:
            self.new_page()

        for i in range(999):
            col_rect = self.curr_page()._next_column_rect(peek=False)

            if col_rect is None:
                # The next page will try to set the set the column to its first
                #   column.
                self.new_page()
            else:
                self._curr_column = self.curr_template().next_column(peek=False)
                self._curr_column.set_total_rect(col_rect)
                self.curr_page()._add_col(self._curr_column)
                self._curr_column._set_parent_page(self.curr_page())
                break
        else:
            # TODO make this give the current token it was working on and where
            #   thus where it was in the file when it ran into this error
            raise AssertionError('A new PDFColumn could not be found even after checking the next 999 pages. You need to add a page that has PDFColumns for text to the current template if you want a new PDFColumn.')

    def new_paragraph(self):
        """
        Starts a new Paragraph.
        """
        if self.curr_document() is None:
            self._new_document()

        if self.curr_column() is None:
            self.new_column()

        cpl = self.curr_paragraph_line()
        if cpl is not None and cpl.word_count() > 0:
            self._place_curr_paragraph_line()

        self._curr_paragraph = self.curr_template().next_paragraph(peek=False)
        self._curr_paragraph._set_parent_document(self.curr_document())
        self.curr_column()._add_paragraph(self._curr_paragraph)
        self._curr_paragraph_line = None

    def new_paragraph_line(self):
        """
        Starts a new Paragraph line.
        """
        if self.curr_column() is None:
            self.new_column()

        if self.curr_paragraph_line() is not None:
            self._place_curr_paragraph_line(False)

        self._curr_paragraph_line = self.curr_template().next_paragraph_line(peek=False)

    def new_word(self, word:str, space_before=True):
        """
        Adds a new word (text) to the current paragraph line.
        """
        if len(word) == 0:
            # Don't add words that have nothing in them
            return

        ct = self.curr_template()
        next_word = ct.next_word(peek=False)
        next_word.set_space_before(space_before)
        next_word.set_text(word)

        curr_words = [next_word]
        refresh_words = False

        # actually add the word to the current paragraph line if possible,
        #   otherwise add it to the next paragraph line.
        for i in range(9999):
            # Find next column if there is not one currently
            cc = self.curr_column()
            if cc is None:
                self.new_column() # Make sure that a column is found
                cc = self.curr_column()

            # Create a new paragraph line if there is not one currently (it is
            #   added to the current paragraph but not current Column)

            cp = self.curr_paragraph()
            if cp is None:
                self.new_paragraph()
                cp = self.curr_paragraph()

            cpl = self.curr_paragraph_line()
            if cpl is None:
                self.new_paragraph_line()
                cpl = self.curr_paragraph_line()
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
                self.new_column()
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

    def create_pdf(self):
        """
        Takes the tokens given to this Object at creation time and creates a PDF.
            This method is run by the compiler to create the actual PDF, IT
            SHOULD NOT BE RUN IN THE PDFO FILE. It returns a PDFDocument that
            you can run the PDFDocument.draw(output_file_name) to actually draw
            it to a file.
        """
        from compiler import Token

        self._new_document()

        while self._current_tok is not None:
            ct = self._current_tok # Current Token

            if isinstance(ct, Token):
                self._handle_token()
            elif isinstance(ct, (MarkupStart, MarkupEnd)):
                self._handle_markup()
            else:
                raise Exception(f'Placer cannot handle Token: {self._current_tok}')

        cpl = self.curr_paragraph_line()
        if cpl is not None and cpl.word_count() > 0:
            self._place_curr_paragraph_line()

        self.curr_document()._call_end_callbacks()

        return self.curr_document()

    def _advance(self, num=1):
        """Advances to the next character in the text if it should advance."""
        self._tok_idx += num
        self._current_tok = self._tokens[self._tok_idx] if 0 <= self._tok_idx < len(self._tokens) else None

    def _handle_token(self):
        """
        The state that is entered when a token is being handled.
        """
        ct = self._current_tok
        tt = ct.type

        result = None

        if tt == TT.PARAGRAPH_BREAK:
            self.new_paragraph()
        elif tt == TT.EXEC_PYTH2:
            result = exec_python(ct.value, self._globals)
        elif tt == TT.EVAL_PYTH2:
            result = eval_python(ct.value, self._globals)
        else:
            self.new_word(ct.value, ct.space_before)

        if isinstance(result, Exception) or issubclass(type(result), Exception):
            from compiler import PythonException, Context

            raise PythonException(ct.start_pos.copy(), ct.end_pos.copy(),
                'An error occured while running your Python code.', result, Context())

        self._advance()

    def _handle_markup(self):
        """
        The state that is entered when markup is being handled.
        """
        print('Advanced past Markup')
        self._advance()

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
        if self.curr_column() is None:
            self.new_column()

        if self.curr_paragraph() is None:
            self.new_paragraph()

        cc = self.curr_column()
        cp = self.curr_paragraph()
        cpl = self.curr_paragraph_line()

        if cpl is None or cpl.word_count() == 0:
            cpl = self.curr_template().next_paragraph_line(peek=False)
            # We have to make a new PDFParagraphLine with either the same size
            #   as the last one or a completely new size
            if self._last_placed_paragraph_line is not None:
                cpl.set_total_height(self._last_placed_paragraph_line.total_height())
            else:
                # Just set it to a default height
                cpl.set_total_height(12) # Makes it the same height as 12 point font

            cpl.set_total_width(0)
        else:
            # Word count must be > 0
            offset = cc.inner_offset() + Point(0, cc.height_used())

            cp.set_total_offset(offset)
            offset = cp.inner_offset()

            cpl.set_total_offset(offset)

            self._place_words_on_line(cpl, cpl.text_info().alignment())

        self._last_placed_paragraph_line = cpl
        cc._add_paragraph_line(cpl)
        cpl._set_parent_column(cc)

        cp._add_paragraph_line(cpl)
        cpl._set_parent_paragraph(cp)

        for word in cpl._pdfwords:
            word._set_parent_paragraph_line(cpl)

        self._curr_paragraph_line = None

        if not replace_with_none:
            self.new_paragraph_line()

    # Private methods for PDFParagraphLine

    @staticmethod
    def _place_words_on_line(pdf_paragraph_line, alignment):
        """
        Actually places the words currently in the given ParagrahLine depending on
            what alignment this paragraph line is using.
        """
        ppl = pdf_paragraph_line
        align = alignment

        # Align the words left
        offset = ppl.inner_offset().copy()
        for word in ppl._pdfwords:
            word.set_total_offset(offset)
            offset += Point(word.total_width(), 0)

        if align == ALIGNMENT.CENTER:
            # Now nudge the words that are aligned left to the right so that
            # they are centered

            # The inner_width is the width that the words CAN use and
            #   curr_width is the width that the words DO use
            nudge_amt = (ppl.inner_width() - ppl.curr_width()) / 2

            for word in ppl._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.RIGHT:
            # Now nudge the words that are aligned left to the right so that
            # they are right aligned
            nudge_amt = ppl.inner_width() - ppl.curr_width()

            for word in ppl._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.JUSTIFY:
            word_cnt = 0

            for i, word in enumerate(ppl._pdfwords):
                if i != 0 and word._space_before:
                    word_cnt += 1

            # Now nudge each word to the right so that they are equally spaced
            nudge_amt = (ppl.inner_width() - ppl.curr_width()) / word_cnt

            curr_word_cnt = 0
            for i, word in enumerate(ppl._pdfwords):
                if i != 0 and word._space_before:
                    curr_word_cnt += 1

                word.set_total_offset(word.total_offset() + Point(nudge_amt * curr_word_cnt, 0))

        elif align != ALIGNMENT.LEFT:
            raise AssertionError(f'This PDFParagraphLine was had alignment {align}, which is not a valid alignment.')

    def _add_words_to_line(self, pdf_paragraph, pdf_paragraph_line, list_of_pdfwords, column_available_size):
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

        for word in list_of_pdfwords:
            assert_instance(word, PDFWord, 'pdfword', or_none=False)

            if width_used:
                leftover_words.append(word)
                continue

            # Try to add the word but if the paragraph_line is now too long
            #   with it added, remove the word and append it to the leftover
            #   words so that it can be added to the next paragraph line

            ppl._pdfwords.append(word)

            if ppl.curr_width() > available_width:
                leftover_words.append(ppl._pdfwords.pop())
                width_used = True
                continue

            if ppl.curr_height() > available_height:
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

        ppl.set_inner_height(ppl.curr_height())

        return (leftover_words, False, width_used) if len(leftover_words) > 0 else (None, False, width_used)

    # ----------
    # Private methods for PDFPage

    def _create_col_rects(self, pdf_page):
        """
        Creates the PDFColumn objects for this PDFPage.
        """
        assert len(pdf_page._col_rects) == 0, f'The columns for this page have already been created. Number of PDFColumns: {len(self._cols)}'
        assert pdf_page._num_rows >= 0 and pdf_page._num_cols >= 0, f'The numbers of columns and rows for a PDFPage must both be atleast 0. They are (row_count, column_count): ({self._num_rows}, {self._num_cols})'

        if pdf_page._num_rows == 0 or pdf_page._num_cols == 0:
            # No need to create any Column objects whatsoever
            return

        curr_x_offset, curr_y_offset = pdf_page.inner_offset().xy()
        col_width = pdf_page.inner_width() / pdf_page._num_cols
        col_height = pdf_page.inner_height() / pdf_page._num_rows

        # create the Column objects and place them on the page.
        for i in range(pdf_page._num_rows * pdf_page._num_cols):
            # Create new column
            next_col = Rectangle()

            # Place the column
            next_col.set_point(Point(curr_x_offset, curr_y_offset))
            next_col.set_size(col_width, col_height)

            # Add the column to the list of columns
            pdf_page._col_rects.append(next_col)

            # Figure out where the next column will be placed.
            if pdf_page.fill_rows_first():
                curr_x_offset += col_width

                # If have reached the last column, start next row
                if ((i + 1) % pdf_page._num_cols) == 0:
                    curr_y_offset += col_height
                    curr_x_offset = 0

            else:
                curr_y_offset += col_height

                # If have reached last column (not Column object but the last
                #   column of the grid of Column objects) then start next
                #   column
                if ((i + 1) % pdf_page._num_rows) == 0:
                    curr_x_offset += col_width
                    curr_y_offset = 0

    # -----------------
    # Other Methods

    @staticmethod
    def print_tokens(tokens):
        """
        Prints all given tokens for debug purposes.
        """
        broke_par = True
        suppress_next_space = True

        from compiler import Token

        for token in tokens:
            if isinstance(token, Token):
                tt = token.type
                tv = token.value
            elif isinstance(token, (MarkupStart, MarkupEnd)):
                m = token.markup()

                if m.paragraph_break():
                    tt = TT.PARAGRAPH_BREAK
                else:
                    continue


            if token.type == TT.PARAGRAPH_BREAK:
                broke_par = True
                print('\n------------\n', end='')
                continue

            if broke_par:
                print(f'\t{token.value}', end='')
                broke_par = False
                suppress_next_space = False

            else:
                if token.space_before and not suppress_next_space:
                    print(f' {token.value}', end='')
                else:
                    print(f'{token.value}', end='')
                    suppress_next_space = False
