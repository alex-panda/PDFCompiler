from placer.templates import PDFDocumentTemplate, TextInfo
from tools import exec_python, eval_python, print_progress_bar, calc_prog_bar_refresh_rate, prog_bar_prefix
from constants import ALIGNMENT, TT, PB_NUM_TABS
from markup import MarkupStart, MarkupEnd, Markup
from shapes import Point, Rectangle
from compiler import Token
from constants import TT

class TokenStream:
    """
    A a stream of tokens to be passed to different placers. The current token
        that the string is at can be gotten with the curr_token() method and
        the stream can be advanced to the next token when next() is called.

    The point of the token stream is to allow people to define their own Placer
        objects that will be passed this token stream, affectively allowing
        different modes of placement. For example, a DefaultPlacer can be
        placing words in paragraphs and then come accross a token that makes it
        switch to a MathPlacer that interprets the tokens in such a way as to
        put mathmatical equations on the page. When another token is reached,
        the MathPlacer will return the TokenStream to the DefaultPlacer which
        will start placing the tokens as words on a line once again.
    """

    def __init__(self, tokens, starting_placer, globals=None, file_path=None, print_progress=False):
        self.set_print_progress(print_progress)

        # The templates that determine the things like color, boldness, size, etc.
        #   of the current word.
        self._default_template = PDFDocumentTemplate()
        self._template_stack = []

        self._file_path = file_path # The path to the main/input pdfo file that is being placed

        self._progress_bar_prefix = 'Placing' if file_path is None else prog_bar_prefix('Placing', file_path)
        self._prog_bar_refresh_rate = calc_prog_bar_refresh_rate(len(tokens))

        # The actual PDFDocument that determines how everything is placed
        self._curr_document = None # Only one PDF document, but just to keep it standard it is call _curr_document
        self._curr_page = None
        self._curr_column = None
        self._curr_paragraph = None
        self._curr_paragraph_line = None

        self._prev_document = None
        self._prev_page = None
        self._prev_column = None
        self._prev_paragraph = None
        self._prev_paragraph_line = None

        # A list of the different objects that have apply_to_canvas methods
        self._apply_to_canvas_list = []

        if globals is not None:
            self._globals = globals
        else:
            self._globals = {}

        globals_to_add = {'placer':self}
        self._globals.update(globals_to_add)

        self._placer_stack = [starting_placer]
        self._curr_placer = None

        self._tokens = tokens
        self._tok_idx = -1
        self._current_tok = None
        self.advance()

    def next_placer(self, advance=True):
        """
        Returns the next placer to use to place tokens on document.

        if advance is True, then the Placer will be popped before it is returned and
            the curr_placer will be updated to this new Placer
        """
        if advance:
            self._curr_placer = self._placer_stack.pop()(self) if len(self._placer_stack) > 0 else None
            return self._curr_placer
        else:
            return self._placer_stack[-1](self) if len(self._placer_stack) > 0 else None

    def curr_placer(self):
        return self._curr_placer

    def place_tokens(self):
        """
        Places the tokens on the PDFDocument by using the current Placer (the
            Placer at the top of the Placer stack).

        If this placer stops placing tokens, then the next placer on the stack
            will begin placing tokens. The placement of tokens only ends once
            the current Placer has finished placing tokens and there are no more
            placers on the placer stack.
        """
        self.next_placer()

        if self.curr_document() is None:
            self.new_document()

        # Print 0% progress bar (if asked for)
        if self.print_progress():
            print_progress_bar(0, len(self._tokens), self._progress_bar_prefix)

        while self.curr_placer() is not None:
            self.curr_placer().place()
            self.next_placer()

        # Print 100 % Progress Bar (if asked for)
        if self.print_progress():
            print_progress_bar(len(self._tokens), len(self._tokens), self._progress_bar_prefix)

        cd = self.curr_document()
        cd._call_end_callbacks()

        for obj in self._apply_to_canvas_list:
            cd.add_apply_to_canvas_obj(obj)

        return cd

    def add_placer(self, placer):
        """
        Adds the next placer to be used when the current one decides to stop
            placing Tokens.
        """
        self._placer_stack.append(placer)

    # ----------------
    # Moving/Accessing the Location of the Stream

    def advance(self, num_forward=1):
        """
        Moves forward or backward (if you give a negative number) in the token
            stream. If there is no token at the token it ends up at index, then
            the current token will be None.

        The token gotten after moving forward or backwards can be gotten from
            either the ruturn value of this method or by calling curr_token()
        """
        self._tok_idx += num_forward
        self._current_tok = self._tokens[self._tok_idx] if 0 <= self._tok_idx < len(self._tokens) else None

        if (self.curr_index() % self._prog_bar_refresh_rate) == 0:
            print_progress_bar(self.curr_index(), len(self._tokens), self._progress_bar_prefix)

        return self._current_tok

    def move_to(self, index):
        """
        Moves the stream to the token at the given index. If no token is at that
            index (you are out of bounds of the token list), then the current
            token will be None.
        """
        self._tok_idx = index
        self._current_tok = self._tokens[self._tok_idx] if 0 <= self._tok_idx < len(self._tokens) else None
        return self._current_tok

    def curr_token(self):
        """
        Returns the current token.
        """
        return self._current_tok

    def curr_index(self):
        """
        Returns the current index.
        """
        return self._tok_idx

    # ----------------
    # Print Progress Methods

    def print_progress(self):
        return self._print_progress

    def set_print_progress(self, boolean):
        assert isinstance(boolean, bool), f'Print progress must be a boolean value, not {boolean}'
        self._print_progress = boolean

    # ----------------
    # Current Template Methods

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

    def add_apply_to_canvas_obj(self, apply_to_canvas_obj):
        self._apply_to_canvas_list.append(apply_to_canvas_obj)

    # ----------------
    # Document Access Methods

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

    def prev_document(self):
        return self._prev_document

    def prev_page(self):
        return self._prev_page

    def prev_column(self):
        return self._prev_column

    def prev_paragraph(self):
        return self._prev_paragraph

    def prev_paragraph_line(self):
        return self._prev_paragraph_line

    # ---------------------------
    # Public Methods for Starting New PDF Elements

    # Note: these new_pdf object methods each create whatever they depend on
    #   but also set what depends on them to None. For example, the current
    #   PDFColumn depends on the current page, so if a new page is called
    #   then it sets the current PDFColumn to None

    def new_document(self):
        """
        Start a new PDFDocument. Should only be called once by the Placer,
            this method should NOT be called in any .pdfo file.
        """
        self._prev_document = self.curr_document()
        self._prev_page = self.curr_page()
        self._prev_column = self.curr_column()
        self._prev_paragraph = self.curr_paragraph()
        self._prev_paragraph_line = self.curr_paragraph_line()

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

        self._prev_page = self.curr_page()
        self._curr_page = self.curr_template().next_page(peek=False)

        self.curr_document()._add_page(self._curr_page)
        self._curr_page._set_parent_document(self.curr_document())

        self.create_col_rects(self._curr_page)

        self._prev_column = self.curr_column()
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
                self._prev_column = self.curr_column()
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

        self._prev_paragraph = self.curr_paragraph()
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

        self._prev_paragraph_line = self.curr_paragraph_line()
        self._curr_paragraph_line = self.curr_template().next_paragraph_line(peek=False)

    # ---------------------------
    # Built-in Handling of tokens to be called by the placer when necessary

    def handle_token(self):
        """
        This method should be called when the placer does not have a built-in
            way to handle the current token. This is so that new features can
            be added without necessarily breaking current Placer implementations.
        """
        ct = self.curr_token()
        if isinstance(ct, Token):
            if ct.type in (TT.EVAL_PYTH2, TT.EXEC_PYTH2):
                self.handle_python_token(call_next=False)
        elif isinstance(ct, (MarkupStart, MarkupEnd)):
            self.handle_markup(call_next=False)
        return self.advance()

    def handle_python_token(self, advance=True):
        """
        Runs the current token as second pass Python. Use this method instead
            of directly running them in the Placer so that they are run
            consistently and if changes need to be made later they can be without
            you having to change your Placer object.

        if call_next is True, then, after the current token is handled as a
            python token, next() will be called and the next token
            will be returned, otherwise, None is returned and the current token
            remains the same.
        """
        ct = self.curr_token()
        assert isinstance(ct, Token), f'handle_python_token() was called when the current token was not of type Token. current token = {ct}'
        tt = ct.type

        if tt == TT.EVAL_PYTH2:
            result = eval_python(ct.value, self._globals, ct.locals)
        else:
            result = exec_python(ct.value, self._globals, ct.locals)

        if isinstance(result, Exception) or issubclass(type(result), Exception):
            from compiler import PythonException, Context

            raise PythonException(ct.start_pos.copy(), ct.end_pos.copy(),
                'An error occured while running your Python code.', result, Context('Placer', 'Placer', globals=self._globals))

        if advance:
            self.advance()

    def handle_markup(self, advance=True):
        """
        Handles a markup start or end in the TokenStream. This should be called
            by a Placer object instead of the Placer object trying to handle
            it itself.
        """
        markup = self._current_tok

        if isinstance(markup, MarkupStart):
            # get the current PDFDocument's default text_info
            cti = self.curr_template().default().text_info()

            # Now make it easy to undo the changes at the end of the range
            if markup.markup_end is not None:
                markup.markup_end.undo_dict = cti.gen_undo_dict(markup.markup.text_info())

            # Actually change the current document's info to what it should be
            cti.merge(markup.markup.text_info())

        elif isinstance(markup, MarkupEnd):
            cti = self.curr_template().default().text_info()
            cti.undo(markup.undo_dict)

        if advance:
            return self.advance()

    # ---------------------
    # Methods Necessary for PDFComponent Initialization

    @staticmethod
    def create_col_rects(pdf_page):
        """
        Creates the PDFColumn objects for this PDFPage.
        """
        assert len(pdf_page._col_rects) == 0, f'The columns for this page have already been created. Number of PDFColumns: {len(pdf_page._col_rects)}'
        assert pdf_page.num_rows() >= 0 and pdf_page.num_cols() >= 0, f'The numbers of columns and rows for a PDFPage must both be atleast 0. They are (row_count, column_count): ({pdf_page._num_rows}, {pdf_page._num_cols})'

        if pdf_page.num_rows() == 0 or pdf_page.num_cols() == 0:
            # No need to create any Column objects whatsoever
            return

        curr_x_offset, curr_y_offset = starting_x, starting_y = pdf_page.inner_offset().xy()
        col_width = pdf_page.inner_width() / pdf_page.num_cols()
        col_height = pdf_page.inner_height() / pdf_page.num_rows()

        fill_rows_first = pdf_page.fill_rows_first()
        #print(f'{pdf_page.num_rows()} * {pdf_page.num_cols()} = {pdf_page.num_rows() * pdf_page.num_cols()}')

        # create the Column objects and place them on the page.
        for i in range(pdf_page.num_rows() * pdf_page.num_cols()):
            # Create new column
            next_col = Rectangle()

            # Place the column
            next_col.set_point(Point(curr_x_offset, curr_y_offset))
            next_col.set_size(col_width, col_height)

            # Add the column to the list of columns
            pdf_page._col_rects.append(next_col)

            # Figure out where the next column will be placed.
            if fill_rows_first:
                curr_x_offset += col_width

                # If have reached the last column, start next row
                if ((i + 1) % pdf_page.num_cols()) == 0:
                    curr_y_offset += col_height
                    curr_x_offset = starting_x

            else:
                curr_y_offset += col_height

                # If have reached last column (not Column object but the last
                #   column of the grid of Column objects) then start next
                #   column
                if ((i + 1) % pdf_page.num_rows()) == 0:
                    curr_x_offset += col_width
                    curr_y_offset = starting_y

    # ----------------
    # Methods Provided to Do Common Operations

    @staticmethod
    def place_words_with_alignment(pdf_paragraph_line, alignment):
        """
        Actually places the words currently in the given ParagrahLine depending on
            what alignment this paragraph line is using.

        The pdf_paragraph_line is assumed to have its width be the total width
            available which may be far wider than the space that the words
            actually take up.
        """
        ppl = pdf_paragraph_line
        align = alignment

        if ppl._curr_alignment != ALIGNMENT.LEFT:
            # Align the words left
            offset = ppl.inner_offset()
            for word in ppl._pdfwords:
                word.set_total_offset(offset)
                offset += Point(word.total_width(), 0)

            ppl._curr_alignment = ALIGNMENT.LEFT

        if align == ALIGNMENT.CENTER:
            ppl._curr_alignment = ALIGNMENT.CENTER

            # Now nudge the words that are aligned left to the right so that
            # they are centered

            # The inner_width is the width that the words CAN use and
            #   curr_width is the width that the words DO use
            nudge_amt = (ppl.inner_width() - ppl.curr_width()) / 2

            for word in ppl._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.RIGHT:
            ppl._curr_alignment = ALIGNMENT.RIGHT

            # Now nudge the words that are aligned left to the right so that
            # they are right aligned
            nudge_amt = ppl.inner_width() - ppl.curr_width()

            for word in ppl._pdfwords:
                word.set_total_offset(word.total_offset() + Point(nudge_amt, 0))

        elif align == ALIGNMENT.JUSTIFY:
            ppl._curr_alignment = ALIGNMENT.JUSTIFY
            word_cnt = 0

            for i, word in enumerate(ppl._pdfwords):
                if i != 0 and word._space_before:
                    word_cnt += 1

            if word_cnt > 0:
                # Now nudge each word to the right so that they are equally spaced
                nudge_amt = (ppl.inner_width() - ppl.curr_width()) / word_cnt

                curr_word_cnt = 0
                for i, word in enumerate(ppl._pdfwords):
                    if i != 0 and word._space_before:
                        curr_word_cnt += 1

                    word.set_total_offset(word.total_offset() + Point(nudge_amt * curr_word_cnt, 0))

        elif align != ALIGNMENT.LEFT:
            raise AssertionError(f'This PDFParagraphLine was had alignment {align}, which is not a valid alignment.')
