from reportlab.lib.units import inch, cm, mm, pica, toLength

import copy
from decimal import Decimal

from placer.templates import PDFDocumentTemplate, PDFDocument, PDFParagraph, PDFParagraphLine, PDFWord, TextInfo
from shapes import Point
from markup import MarkupStart, MarkupEnd, Markup
from constants import ALIGNMENT, TT
from toolbox import ToolBox
from tools import exec_python, eval_python

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

        self._broke_paragraph = True
        self._suppress_next_space = False

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
        if len(self._template_stack) == 0:
            return self._default_template
        else:
            return self._template_stack[-1]

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

    def _new_doc(self):
        self._curr_document = self.curr_template().next_document(peek=False)
        self.new_page()
        self.new_column()
        self.new_paragraph()
        self.new_paragraph_line()

    def new_page(self):
        self._curr_page = self.curr_template().next_page(peek=False)
        self._curr_page._create_col_rects()
        self.curr_document()._add_page(self._curr_page)

    def new_column(self):
        """
        If curr_column() is None after calling this method, that means that the
            current page has no more culumns on it, so you must call new_page
            and then check to see if that page has a column on it by seeing
            if curr_column() is None again after calling new_page()
        """
        if not hasattr(self, '_col_recursive_amt'):
            self._col_recursive_amt = 0
        else:
            self._col_recursive_amt += 1

        col_rect = self.curr_page()._next_column_rect(peek=False)

        if col_rect is None:
            if self._col_recursive_amt >= 777:
                raise AssertionError('A new column could not be found even after checking the next 777 pages. You need to add a page that has Columns for text to the template if you want to be able to get a new Column.')
            # The next page will try to set the set the column to its first
            #   column.
            self.new_page()
            self.new_column()
        else:
            self._curr_column = self.curr_template().next_column(peek=False)
            self._curr_column.set_total_rect(col_rect)
            self.curr_page()._add_col(self._curr_column)

        self._col_recursive_amt -= 1

    def new_paragraph(self):
        self._curr_paragraph = self.curr_template().next_paragraph(peek=False)
        self.new_paragraph_line() # Now get a new paragraph line for the current paragraph

    def new_paragraph_line(self):
        """
        Creates a new Paragraph line, adding it the current paragraph but it still
            needs to be added to a Column.
        """
        cpl = self.curr_paragraph_line()


        # Check if the previous paragraphLine should be added to the current column
        if cpl is not None and cpl.word_count() > 0 and self.curr_column() is not None:
            avail_area = (cc := self.curr_column()).available_area()
            cpl_area = cpl.total_rect()
            cpl_area.set_point(avail_area.point())

            if cpl_area.fits_inside(avail_area):
                cpl.set_total_offset(cc.inner_offset() + Point(0, cc.height_used()))
                cpl.place_words()
                self.curr_column().add_paragraph_line(cpl)

        # Add the previous paragraph line (if there is one) to the current paragraph
        if cpl is not None and cpl.word_count() > 0:
            self.curr_paragraph().add_paragraph_line(cpl)

        self._curr_paragraph_line = self.curr_template().next_paragraph_line(peek=False)

    def new_word(self, word:str, space_before=True):
        if len(word) == 0:
            # Don't add words that have nothing in them
            return

        next_word = self.curr_template().next_word(peek=False)
        next_word.set_space_before(space_before)
        next_word.set_text(word)

        curr_words = [next_word]
        # actually add the word to the current paragraph line if possible,
        #   otherwise add it to the next paragraph line.
        for i in range(9999):
            # Find next column if there is not one currently
            if (cc := self.curr_column()) is None:
                self.new_column() # Next page might have a column on it so go to it
                continue

            # Create a new paragraph line if there is not one currently (it is
            #   added to the current paragraph but not current Column)
            if (cpl := self.curr_paragraph_line()) is None:
                self.new_paragraph_line()
                cpl = self.curr_paragraph_line()

            #   set inner_size of current paragraph line so that it knows how
            #       much space is available for it.
            cpl.set_total_size(cc.available_area().size())

            # Now try to place the word in the current paragraph line
            curr_words, need_new_col, width_used = cpl.add_words(curr_words)

            if width_used:
                print(f'Width Used: {cc.available_area().size()}')

            if cpl.word_count() > 0 and width_used and not need_new_col:
                cpl.set_total_offset(cc.inner_offset() + Point(0, cc.height_used()))
                cpl.place_words()
                self.curr_column().add_paragraph_line(cpl)
                self.new_paragraph_line()

            if need_new_col:
                self.new_column()
                if self.curr_column() is None:
                    self.new_page()
                continue
            elif width_used:
                self.new_paragraph_line()
                continue

            break
        else:
            raise AssertionError(f'Could not place word "{word}" even though it was given 9999 tries. You probably have all the margins of your paper so large that there is nowhere for even a single letter of the word to be put on the PDF.')

    # ------------------------
    # Private Methods

    def _advance(self, num=1):
        """Advances to the next character in the text if it should advance."""
        self._tok_idx += num
        self._current_tok = self._tokens[self._tok_idx] if 0 <= self._tok_idx < len(self._tokens) else None

    def create_pdf(self):
        """
        Takes a bunch of tokens and creates a PDF. This method is run by the
            compiler to create the actual PDF, IT SHOULD NOT BE RUN IN THE
            PDFO FILE.
        """
        self._new_doc()
        from compiler import Token

        while self._current_tok is not None:
            ct = self._current_tok # Current Token

            if isinstance(ct, Token):
                self._handle_token()
            elif isinstance(ct, (MarkupStart, MarkupEnd)):
                self._handle_markup()
            else:
                raise Exception(f'Placer cannot handle Token: {self._current_tok}')

        self.curr_document()._call_end_callbacks()

        return self.curr_document()

    def _handle_token(self):
        """
        The state that is entered when a token is being handled.
        """
        ct = self._current_tok
        tt = ct.type

        result = None

        if tt == TT.PARAGRAPH_BREAK:
            self.new_paragraph()
            self.new_word(ct.value, ct.space_before)
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

    def _should_add_line_to_col(self):
        cpl = self.curr_paragraph_line()

        if cpl is not None and self.curr_column() is not None and cpl.word_count() > 0:
            avail_area = self.curr_column().available_area()
            cpl_area = cpl.total_rect()
            cpl_area.set_point(avail_area.point())

            if cpl_area.fits_inside(avail_area):
                self.curr_column().add_paragraph_line(cpl)
                return True
        return False

    @staticmethod
    def _print_tokens(tokens):
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

