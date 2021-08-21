"""
This is the main file that holds the Tokenizer, Parser, and Interpreter
    that actually compile the PDF.
"""
import os.path as path
import re
import copy as _copy
from decimal import Decimal

from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes as pagesizes

from placer.placer import Placer
from constants import CMND_CHARS, END_LINE_CHARS, ALIGNMENT, TT, TT_M, WHITE_SPACE_CHARS, NON_END_LINE_CHARS, PB_NUM_TABS, PB_NAME_SPACE, STD_FILE_ENDING, STD_LIB_FILE_NAME, OUT_TAB
from tools import assure_decimal, is_escaped, is_escaping, exec_python, eval_python, string_with_arrows, trimmed, print_progress_bar, prog_bar_prefix, calc_prog_bar_refresh_rate, assert_instance
from marked_up_text import MarkedUpText
from markup import Markup, MarkupStart, MarkupEnd
from toolbox import ToolBox
from placer.placers.naiveplacer import NaivePlacer

# -----------------------------------------------------------------------------
# Errors That Can Occur While Compiling

class Error(Exception):
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result  = f'Line {self.pos_start.ln + 1}, Column {self.pos_start.col + 1}, in file {self.pos_start.file_path}\n'
        result += f'    {self.error_name} Occured: {self.details}'
        result += '\n' + string_with_arrows(self.pos_start.file_text, self.pos_start, self.pos_end)
        return result

class ExpectedValidCmndNameError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Expected Valid Command Name', details)

class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character Error', details)

class ExpectedCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Expected Character Error', details)

class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=''):
        super().__init__(pos_start, pos_end, 'Invalid Syntax Error', details)

class RunTimeError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, 'Run-Time Error', details)
        self.context = context

    def generate_traceback(self):
        result = ''
        pos = self.pos_start
        ctx = self.context

        while ctx is not None:
            result = f'  File {pos.file_path}, line {pos.ln + 1}, in {ctx.display_name}\n' + result
            pos = ctx.entry_pos
            ctx = ctx.parent

        return 'Traceback (most recent call last):\n' + result

class PythonException(RunTimeError):
    def __init__(self, pos_start, pos_end, details, python_error, context):
        import traceback
        self.python_error = f'{python_error.exc_trace}'
        super().__init__(pos_start, pos_end, details, context)
        self.error_name = 'Python Exception'

    def as_string(self):
        string = super().as_string()

        string += '\nHere is the Python Exception:\n\n'
        string += f'{self.python_error}'
        return string


# -----------------------------------------------------------------------------
# Position Class

class Position:
    """
    Position in a Tokenized file or a file that is being tokenized.
    """
    __slots__ = ['idx', 'ln', 'col', 'file_path', 'file_text']
    def __init__(self, idx, ln, col, file_path, file_text):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.file_path = file_path # The path tot he file that this is a position in
        self.file_text = file_text # The text of the file this is a position in

    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1

        if current_char in END_LINE_CHARS:
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.file_path, self.file_text)

    def __repr__(self):
        file = self.file_path.split('\\')[-1]
        return f"{self.__class__.__name__}(line {self.ln}, col {self.col}, in {file})"

# -----------------------------------------------------------------------------
# File Class

class File:
    __slots__ = ['file_path',
            'raw_text', 'tokens', 'ast',
            'import_context', 'import_tokens', 'being_run']
    def __init__(self, file_path):
        self.file_path = file_path # Path to file

        # Fields set in Compiler._compiler_import_file
        self.raw_text = None # The raw text that is in the file
        self.tokens = None # The tokens that make up the File once it has been tokenized
        self.ast = None # The Abstract Syntax tree from the Tokens being Parsed

        # Fields set by Compiler._import_file
        self.import_context = None # The context obtained by running the file, can be used to import this file into another file
        self.import_tokens = None # The tokens to add to the token_document when the file is imported
        self.being_run = False

# -----------------------------------------------------------------------------
# Token Class

class Token:
    __slots__ = ['start_pos', 'end_pos', 'type', 'value', 'space_before']
    def __init__(self, type, value, start_pos, end_pos=None, space_before=True):
        self.start_pos = start_pos

        if isinstance(space_before, bool):
            # Space before is whether there should be a space before the token
            #   when it is put on the page. This is so that tokens like the
            #   '=' and '{' that are singled out of a sentence can still tell
            #   the placer whether there was space before them because the
            #   default is to just put a space before each token is placed down.
            self.space_before = space_before
        else:
            self.space_before = (space_before in WHITE_SPACE_CHARS)

        if end_pos is None:
            end_pos = self.start_pos.copy()
            end_pos.advance() # Necessary if you want errors to display the errors correctly because they use start_pos - end_pos
            self.end_pos = end_pos
        else:
            self.end_pos = end_pos

        self.type = type
        self.value = str(value)

        if type == TT.WORD and value == '':
            raise Exception(f'An empty string has been made into a Token. This is a compiler problem. {self}')

    def matches(self, token_type, value):
        """
        Checks if the given token_type and value matches this one.
        """
        return self.type == token_type and self.value == value

    def copy(self):
        start_pos = None if self.start_pos is None else self.start_pos.copy()
        end_pos = None if self.end_pos is None else self.end_pos.copy()
        return Token(self.type, self.value, start_pos, end_pos, self.space_before)

    def gen_pass_2_python(self, locals):
        """
        Generates a SecondPassPythonToken that can store the locals
            that should be provided when the python code is run in the Placer.
            The Placer already has the globals that should be provided.
        """
        start_pos = None if self.start_pos is None else self.start_pos.copy()
        end_pos = None if self.end_pos is None else self.end_pos.copy()
        return SecondPassPythonToken(self.type, self.value, start_pos, end_pos, self.space_before, locals)

    def __repr__(self):
        """
        This is what is called when you print this object since __str__ is undefined.
        """
        return f"Token(\"<{self.type}>\":{' ' if self.space_before else ''}{self.value})"

class SecondPassPythonToken(Token):
    __slots__ = Token.__slots__[:]
    __slots__.extend(['locals'])
    def __init__(self, type, value, start_pos, end_pos=None, space_before=False, locals=None):
        super().__init__(type, value, start_pos, end_pos, space_before)
        self.locals = locals

# -----------------------------------------------------------------------------
# Tokenizer Class

class Tokenizer:
    """
    Takes raw text and tokenizes it.
    """
    def __init__(self, file_path, file_text, starting_position=None, print_progress_bar=False):
        super().__init__()
        self._print_progress_bar = print_progress_bar

        if starting_position:
            # Parse assuming that you are starting at the given line and column int he file
            self._pos = starting_position.copy()
            self._pos.idx = -1
        else:
            # Parse assuming that you are starting at the beginning of the file
            self._pos = Position(-1, 0, -1, file_path, file_text)

        self._text = file_text
        self._current_char = None
        self._previous_char = ''
        self._plain_text = ''
        self._plain_text_start_pos = None
        self._space_before_plaintext = False
        self._unpaired_cbrackets = 0
        self._unpaired_oparens = 0

        self._tokens = []
        self._advance()

    def _advance(self, num=1):
        """Advances to the next character in the text if it should advance."""
        for i in range(num):
            self._previous_char = self._current_char
            self._pos.advance(self._current_char)
            self._current_char = self._text[self._pos.idx] if self._pos.idx < len(self._text) else None

    @staticmethod
    def plaintext_tokens_for_str(string, count_starting_space=False):
        """
        If you want to write plaintext to the placer and the string to be
            interpreted only as plaintext, then this is what you use to
            tokenize the string. Just take the return-ed string from this
            method and give it to the place_text method of the Placer.

        If count_starting_space is True, then it will treat the whitespace
            before the first letter as actual space that could produce
            a paragraph break
        """
        tokens = []
        idx = -1
        cc = None

        def next_tok(idx):
            idx += 1
            return string[idx] if idx < len(string) else None, idx

        def try_append_word(curr_word, space_before):
            curr_word = re.sub('(\s)+', '', curr_word)
            if len(curr_word) > 0:
                tokens.append(Token(TT.WORD, curr_word, DUMMY_POSITION.copy(), space_before=space_before))

        cc, idx = next_tok(idx)

        if not count_starting_space:
            # Eat all end line chars at beginning so no paragraph break at beginning
            while (cc is not None) and (cc in END_LINE_CHARS):
                cc, idx, = next_tok(idx)

        space_before = False
        curr_word = ''
        while cc is not None:
            if cc in NON_END_LINE_CHARS:
                cc, idx = next_tok(idx)

                try_append_word(curr_word, space_before)
                curr_word = ''
                space_before = True

                while (cc is not None) and (cc in NON_END_LINE_CHARS):
                    cc, idx, = next_tok(idx)

                continue

            elif cc in END_LINE_CHARS:
                cc, idx = next_tok(idx)

                try_append_word(curr_word, space_before)
                curr_word = ''
                space_before = True

                if cc in END_LINE_CHARS:
                    tokens.append(Token(TT.PARAGRAPH_BREAK, TT.PARAGRAPH_BREAK, DUMMY_POSITION.copy()))
                    cc, idx = next_tok(idx)

                    while (cc is not None) and (cc in END_LINE_CHARS):
                        cc, idx, = next_tok(idx)

                continue
            else:
                curr_word += cc
                cc, idx = next_tok(idx)

        try_append_word(curr_word, space_before)

        return tokens

    @staticmethod
    def marked_up_text_for_tokens(list_of_tokens):
        """
        Returns a MarkedUpText object that is equivalent to the List of Tokens given.
        """

        text = MarkedUpText()
        curr_index = 0
        pending_markups = []

        for t in list_of_tokens:
            if isinstance(t, (MarkupStart, MarkupEnd)):
                text.add_markup_start_or_end(t, curr_index)
            elif isinstance(t, Token):
                if t.type == TT.PARAGRAPH_BREAK:
                    # Add two newlines to signify a paragraph break
                    text += '\n\n'
                    curr_index += 2
                elif t.type in (TT.EXEC_PYTH2, TT.EVAL_PYTH2):
                    markup = Markup()
                    markup.add_python(t)
                    text.add_markup(markup, curr_index)
                else:
                    if t.space_before:
                        text += ' '
                        curr_index += 1
                    text += t.value
                    curr_index += len(t.value)
            else:
                raise Exception(f'{t} was in the list of tokens given to be changed into MarkedUpText, but MarkedUpText can\'t denote it. This is a compiler problem, tell the makers of the compiler that you got this error.')

        text_len = len(text)
        #print(f'curr_index = {curr_index}, text_len = {text_len}, markups = {None if text_len not in text._markups else text._markups[text_len]}')
        if text_len > 0 and text_len in text._markups:
            markups = text._markups.pop(text_len)

            index = text_len - 1
            if index in text._markups:
                text._markups[index].extend(markups)
            else:
                text._markups[index] = markups

            #print(f'AFTER markups = {None if index not in text._markups else text._markups[index]}')

        return text

    @staticmethod
    def tokens_for_marked_up_text(marked_up_text):
        """
        Returns a list of tokens for the given MarkedUpText.
        """

        def try_token(token_value, token_list):
            if len(token_value) > 0:
                space_before = (token_value[0] in WHITE_SPACE_CHARS)
                tokens = Tokenizer.plaintext_tokens_for_str(str(token_value), True)
                token_value = ''

                if len(tokens) > 0:
                    tokens[0].space_before = space_before
                    token_list.extend(tokens)
            return token_value, token_list

        token_list = []
        token_value = ''
        pending_end_markups = []

        for i, char in enumerate(marked_up_text):
            markups = marked_up_text.markups_for_index(i)
            # markups is a list of MarkupStart and MarkupEnd objects or
            #   None if there are None

            # Since Markups are inclusive of their index, the MarkupStarts must
            #   be appended before the next char and the MarkupEnds must be
            #   appended after the next character is added

            if markups:
                token_value, token_list = try_token(token_value, token_list)

                for markup in markups:
                    if isinstance(markup, MarkupStart):
                        token_list.append(markup)
                    else:
                        pending_end_markups.append(markup)

            token_value += char

            if pending_end_markups:

                token_value, token_list = try_token(token_value, token_list)

                for markup in pending_end_markups:
                    token_list.append(markup)

                pending_end_markups = []

        token_value, token_list = try_token(token_value, token_list)

        return token_list

    def tokenize(self, file=True):
        """
        Turn the raw text into tokens that the compiler can use.

        If file is true, the tokenizer assumes that the text is from a file and
            bookends the tokens with TT.FILE_START and TT.FILE_END
        """
        self._tokens = []
        self._plain_text = ''
        what_can_be_escaped = {'{', '}', '=', '\\', '(', ')', ','}

        if file:
            self._tokens.append(Token(TT.FILE_START, '<FILE START>', self._pos.copy()))

        print_progress = self._print_progress_bar

        if print_progress:
            text_len = len(self._text)
            prefix = prog_bar_prefix('Tokenizing', self._pos.file_path)
            refresh = calc_prog_bar_refresh_rate(text_len)
            full_bar_printed = False

            if print_progress_bar(0, text_len, prefix):
                full_bar_printed = True

        # By default, all text is plain text until something says otherwise
        while self._current_char is not None:

            i = self._pos.idx

            if print_progress and (i % refresh) == 0:
                print_progress_bar(i, text_len, prefix)

            cc = self._current_char

            t = None

            if is_escaped(i, self._text, what_can_be_escaped):
                self._plain_text_char()
            elif is_escaping(i, self._text, what_can_be_escaped):
                self._advance() # Just advance because it is just escaping something else
            elif cc in END_LINE_CHARS:
                self._try_word_token()
                self._advance()

                pos_start = self._pos.copy()

                if self._current_char in END_LINE_CHARS:

                    while self._current_char in END_LINE_CHARS:
                        # Do nothing, just eat the END_LINE_CHARS now that we know that there is a PARAGRAPH_BREAK
                        self._advance()

                    t = Token(TT.PARAGRAPH_BREAK, TT.PARAGRAPH_BREAK, pos_start, self._pos.copy())
            elif cc in NON_END_LINE_CHARS:
                self._try_word_token()
                self._advance()
            elif cc == '{':
                if self._unpaired_cbrackets == 0:
                    self._first_unpaired_bracket_pos = self._pos.copy()
                self._unpaired_cbrackets += 1
                t = Token(TT.OCBRACE, '{', self._pos.copy(), space_before=self._previous_char)
                self._advance()

            elif cc == '}':
                self._unpaired_cbrackets -= 1
                if self._unpaired_cbrackets < 0:
                    raise InvalidSyntaxError(self._pos.copy(), self._pos.copy().advance(),
                            'Unpaired, unescaped, closing curly bracket "}". You need to add an open curly bracket "{" before it or escape it by putting a backslash before it.')
                t = Token(TT.CCBRACE, '}', self._pos.copy(), space_before=self._previous_char)
                self._advance()

            elif cc == '=':
                t = Token(TT.EQUAL_SIGN, '=', self._pos.copy(), space_before=self._previous_char)
                self._advance()
            elif cc == '(':

                if self._unpaired_oparens == 0:
                    self._first_unpaired_oparens_pos = self._pos.copy()
                self._unpaired_oparens += 1
                t = Token(TT.OPAREN, '(', self._pos.copy(), space_before=self._previous_char)
                self._advance()

            elif cc == ')':

                self._unpaired_oparens -= 1
                if self._unpaired_oparens < 0:
                    raise InvalidSyntaxError(self._pos.copy(), self._pos.copy().advance(),
                            'Unpaired, unescaped, closing parenthesis ")". You need to add an open curly bracket "(" before it or escape it by putting a backslash before it.')
                t = Token(TT.CPAREN, ')', self._pos.copy(), space_before=self._previous_char)
                self._advance()

            elif cc == ',':
                t = Token(TT.COMMA, ',', self._pos.copy(), space_before=self._previous_char)
                self._advance()
            elif cc == '\\':
                t = self._tokenize_cntrl_seq()
            else:
                self._plain_text_char()

            if t is not None:
                # Actually append the Token (or list of tokens) if there is a Token to append
                self._try_word_token()

                if isinstance(t, Token):
                    self._tokens.append(t)
                else:
                    # t must be a list of tokens
                    self._tokens.extend(t)

        if print_progress and not full_bar_printed:
            print_progress_bar(text_len, text_len, prefix)

        if self._unpaired_cbrackets > 0:
            raise InvalidSyntaxError(self._first_unpaired_bracket_pos.copy(), self._first_unpaired_bracket_pos.copy().advance(),
                    f'{self._unpaired_cbrackets} unpaired, unescaped, opening curly bracket(s) "{" starting from this opening curly bracket. Either escape each one by putting a backslash before them or pair them with a closing curly bracket "}".')

        if self._unpaired_oparens > 0:
            raise InvalidSyntaxError(self._first_unpaired_oparens_pos.copy(), self._first_unpaired_oparens_pos.copy().advance(),
                    f'{self._unpaired_oparens} unpaired, unescaped, opening parenthes(es) "(" starting from this open parenthes(es). Either escape each one by putting a backslash before them or pair them with a closing parenthesis ")".')

        self._try_word_token()

        if file:
            self._tokens.append(Token(TT.FILE_END, '<FILE END>', self._pos.copy()))

        return self._tokens

    # -------------------------------------------------------------------------
    # Parsing Methods

    def _tokenize_cntrl_seq(self):
        """
        Parse a control sequence.
        """
        t = None

        pos_start = self._pos.copy()

        # Note, Multi-line matches tend be longer and so need to come before
        #   single-line matches because shorter matches will match before longer
        #   matches, even if the longer match would have worked had it been tried

        # Multiple Line Python ----------------------
        if self._match(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_START):
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_END, 1, pos_start, )

        elif self._match(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_START):
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_END, 1, pos_start, use_eval=True)

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_START):
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_END, 2, pos_start, )

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_START):
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, use_eval=True)

        # One Line Python -----------------------
        elif self._match(TT_M.ONE_LINE_PYTH_1PASS_EXEC_START):
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_1PASS_EXEC_END, 1, pos_start, one_line=True)

        elif self._match(TT_M.ONE_LINE_PYTH_1PASS_EVAL_START):
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_1PASS_EVAL_END, 1, pos_start, one_line=True, use_eval=True)

        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EXEC_START):
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_2PASS_EXEC_END, 2, pos_start, one_line=True)

        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EVAL_START):
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, one_line=True, use_eval=True)

        # Comment ----------------------
        elif self._match(TT_M.MULTI_LINE_COMMENT_START):
            t = self._tokenize_comment(pos_start, one_line=False)

        elif self._match(TT_M.SINGLE_LINE_COMMENT_START):
            t = self._tokenize_comment(pos_start, one_line=True)

        # Command --------------------------
        else:
            # It is an identifier, so tokenize it
            t = self._tokenize_identifier()

        return t

    def _tokenize_python(self, end_codes, pass_num, pos_start, one_line=False, use_eval=False):
        """
        Parses the string from self._pos as python code until one of the end_codes
            are reached.

        If one_line is true, that means that this python statement is supposed
            to only be one line so it cannot turn the rest of the file
            into python.
        """
        python_str = ''

        pos_end = self._pos.copy()
        match_found = False

        while self._current_char is not None:
            if self._match(end_codes, False):

                # Only eat the chars if they are not in the END_LINE_CHARS.
                #   Otherwise it is needed in order to determine whether to put
                #   in a PARAGRAPH_BREAK
                if not self._current_char in END_LINE_CHARS:
                    self._match(end_codes)

                match_found = True
                break
            else:
                # Since python has not ended yet, just add the given char to it
                python_str += self._current_char
                self._advance()

        if (self._current_char is None) and (not match_found) and (not one_line):
            raise InvalidSyntaxError(pos_start, pos_end,
                    f'You made the rest of your file Python because there was no matching character sequence to end the Python section of your document denoted by this character sequence.')

        pos_end = self._pos.copy()

        if pass_num == 1:
            if use_eval:
                return Token(TT.EVAL_PYTH1, python_str, pos_start, pos_end)
            else:
                return Token(TT.EXEC_PYTH1, python_str, pos_start, pos_end)
        else:
            if use_eval:
                return Token(TT.EVAL_PYTH2, python_str, pos_start, pos_end)
            else:
                return Token(TT.EXEC_PYTH2, python_str, pos_start, pos_end)

    def _tokenize_comment(self, pos_start, one_line=False):
        """
        Parses a comment, basically just eating any characters it finds until
            the comment is done. None of the characters are put into any Token,
            so the Parser will never even see them.
        """
        pos_end = self._pos.copy()
        if one_line:
            # Its a one_line comment
            while self._current_char is not None:
                if self._match(TT_M.SINGLE_LINE_COMMENT_END):
                    break
                else:
                    self._advance()
        else:
            found_match = False

            # it's a continous comment, so parse until '<-%\' or '<-#\' is found
            while self._current_char is not None:
                if self._match(TT_M.MULTI_LINE_COMMENT_END):
                    found_match = True
                    break
                else:
                    self._advance()

            if self._current_char is None and not found_match:
                raise InvalidSyntaxError(pos_start, pos_end, 'You commented out the rest of your file because there was no matching "<-%\\" or "<-#\\" to end the comment.')

        if len(self._tokens) > 0 and self._tokens[-1].type == TT.PARAGRAPH_BREAK:
            # Need to eat all end line white space now so that another
            #   PARAGRAPH_BREAK cannot be produced due to this comment text being
            #   ignored and there being white space before it. Two PARAGRAPH_BREAKs
            #   next to eachother breaks all grammar rules and causes the Parser
            #   to terminate early (i.e. before it reaches the FILE_END token)
            while self._current_char in END_LINE_CHARS:
                self._advance()

    def _tokenize_identifier(self):
        """
        Tokenize an identifier like \\bold or \\i
        """
        identifier_name = ''

        start_pos = self._pos.copy()
        space_before = self._previous_char

        #tokens = []
        #tokens.append(Token(TT.BACKSLASH, '\\', start_pos.copy(), self._pos.copy(), space_before=space_before))

        self._advance() # advance past '\\'

        problem_start = self._pos.copy()

        while self._current_char is not None:
            if self._current_char in CMND_CHARS:
                identifier_name += self._current_char
                self._advance()
            else:
                if len(identifier_name) == 0:

                    raise ExpectedValidCmndNameError(problem_start, self._pos.copy(),
                            f'All commands must specify a valid name with all characters of it in {CMND_CHARS}\n"{self._current_char}" is not one of the valid characters. You either forgot to designate a valid command name or forgot to escape the backslash before this character.')

                token = Token(TT.IDENTIFIER, identifier_name, start_pos.copy(), self._pos.copy(), space_before=space_before)

                return token

    # -------------------------------------------------------------------------
    # Other Helper Methods

    def _try_word_token(self):
        """
        Create a WORD token given what is in self._plain_text
        """
        self._plain_text = re.sub('(\s)+', '', self._plain_text)

        if len(self._plain_text) > 0:
            self._tokens.append(Token(TT.WORD, self._plain_text, self._plain_text_start_pos, self._pos.copy(), space_before=self._space_before_plaintext))
            self._space_before_plaintext = False
            self._plain_text = ''
            self._plain_text_start_pos = None

    def _plain_text_char(self):
        """
        The current_char is a plain_text character
        """
        if self._plain_text_start_pos is None:
            self._plain_text_start_pos = self._pos.copy()

            if self._pos.idx - 1 >= 0:
                self._space_before_plaintext = (self._text[self._pos.idx - 1] in WHITE_SPACE_CHARS)
            else:
                self._space_before_plaintext = False

        self._plain_text += self._current_char
        self._advance()

    def _match(self, matches:list, advance_past_on_match=True):
        """
        Takes the given list of strings to match and sees if any of them match
            the text at the current index of the self._text

        This method does not look forward in the text for a match, just returns
            True if the string starting at the current index matches any of
            the matches.

        If advance_past_on_match, then if this method matches something, it will
            advance past the string it matched.
        """
        index = self._pos.idx
        for str_to_match in matches:
            if ((index + len(str_to_match)) < len(self._text)) \
                    and (str_to_match == self._text[index:index + len(str_to_match)]):

                if advance_past_on_match:
                    self._advance(len(str_to_match))

                return True
        return False

# -----------------------------------------------------------------------------
# Nodes for Parser

DUMMY_POSITION = Position(0, 0, 0, 'Dummy File Name', 'Dummy File Text')

class LeafNode:
    """
    Base class for all Leaf Nodes (nodes that can only have one token)
    """
    __slots__ = ['start_pos', 'end_pos']
    def __init__(self, token):
        """
        Takes a token and sets the start and end positions using it. Still
            must name the token in the actual node (i.e. self.writing, etc.)
        """
        self.start_pos = token.start_pos
        self.end_pos = token.end_pos

class FileNode:
    __slots__ = ['start_pos', 'end_pos', 'file_start', 'document', 'file_end']
    def __init__(self, file_start, document, file_end):
        self.file_start = file_start # Token
        self.document = document # DocumentNode
        self.file_end = file_end # Token

        self.start_pos = file_start.start_pos
        self.end_pos = file_end.end_pos

    def __repr__(self):
        return f'{self.__class__.__name__}({self.file_start}, {self.document}, {self.file_end})'

class DocumentNode:
    __slots__ = ['start_pos', 'end_pos', 'starting_paragraph_break', 'paragraphs', 'ending_paragraph_break']
    def __init__(self, paragraphs, starting_paragraph_break=None, ending_paragraph_break=None):
        self.starting_paragraph_break = starting_paragraph_break # Token
        self.paragraphs = paragraphs # List of ParagraphNodes
        self.ending_paragraph_break = ending_paragraph_break # Token

        if starting_paragraph_break:
            self.start_pos = starting_paragraph_break.start_pos
        elif len(paragraphs) > 0:
            self.start_pos = paragraphs[0].start_pos
        else:
            self.start_pos = DUMMY_POSITION.copy()

        if len(paragraphs) > 0:
            self.end_pos = paragraphs[-1].end_pos
        elif ending_paragraph_break:
            self.end_pos = ending_paragraph_break.end_pos
        elif starting_paragraph_break:
            self.end_pos = starting_paragraph_break.end_pos
        else:
            self.end_pos = DUMMY_POSITION.copy()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.paragraphs})'

class ParagraphNode:
    __slots__ = ['start_pos', 'end_pos', 'writing', 'paragraph_break']
    def __init__(self, paragraph_break, writing):
        self.paragraph_break = paragraph_break # Token
        self.writing = writing # WritingNode

        self.start_pos = writing.start_pos

        if paragraph_break:
            self.end_pos = paragraph_break.end_pos
        else:
            self.end_pos = writing.end_pos

    def __repr__(self):
        return f'{self.__class__.__name__}({self.writing})'

class WritingNode(LeafNode):
    __slots__ = LeafNode.__slots__[:]
    __slots__.extend(['writing'])
    def __init__(self, writing):
        """
        writing can be either a python node or a plain_text node.
        """
        super().__init__(writing)
        self.writing = writing # PythonNode or PlainTextNode

    def __repr__(self):
        return f'{self.__class__.__name__}({self.writing})'

class PythonNode(LeafNode):
    __slots__ = LeafNode.__slots__[:]
    __slots__.extend(['python', 'python_string'])
    def __init__(self, python):
        """
        python is a single python Token (PASS1EXEC|PASS2EXEC|PASS1EVAL|PASS2EVAL)
        """
        super().__init__(python)
        self.python = python # one of the exec or eval Nodes
        self.python_string = None

    def __repr__(self):
        return f'{self.__class__.__name__}({self.python})'

class CommandDefNode:
    __slots__ = ['start_pos', 'end_pos', 'cmnd_name', 'cmnd_params', 'cmnd_key_params', 'text_group']
    def __init__(self, cmnd_name, cmnd_params, cmnd_key_params, text_group):
        self.start_pos = cmnd_name.start_pos
        self.end_pos = text_group.end_pos

        self.cmnd_name = cmnd_name # IDENTIFIER Token
        self.cmnd_params = cmnd_params # list of CommandParamNodes
        self.cmnd_key_params = cmnd_key_params # list of CommandKeyParamNodes
        self.text_group = text_group # the text_group that the command will run

    def __repr__(self):
        cmnd_args = ''
        for i, arg in enumerate(self.cmnd_params):
            if i > 0:
                cmnd_args += ', '
            cmnd_args += f'{arg}'

        return f'{self.__class__.__name__}({self.cmnd_name} = ({cmnd_args}) ' + '{' + f'{self.text_group}' + '}' + ')'

class CommandParamNode:
    __slots__ = ['start_pos', 'end_pos', 'identifier']
    def __init__(self, identifier):
        self.start_pos = identifier.start_pos
        self.end_pos = identifier.end_pos

        self.identifier = identifier # IDENTIFIER Token

    def __repr__(self):
        return f'{self.__class__.__name__}({self.identifier})'

class CommandKeyParamNode:
    __slots__ = ['start_pos', 'end_pos', 'key', 'text_group']
    def __init__(self, key, text_group):
        self.start_pos = key.start_pos
        self.end_pos = text_group.end_pos
        self.key = key # WORD Token
        self.text_group = text_group # TextGroupNode

    def __repr__(self):
        return f'{self.__class__.__name__}({self.text_group})'

class CommandCallNode:
    __slots__ = ['start_pos', 'end_pos', 'cmnd_name', 'cmnd_tex_args', 'cmnd_key_args']
    def __init__(self, cmnd_name, cmnd_tex_args, cmnd_key_args):
        self.start_pos = cmnd_name.start_pos
        self.end_pos = cmnd_name.end_pos

        self.cmnd_name = cmnd_name # IDENTIFIER Token
        self.cmnd_tex_args = cmnd_tex_args # list of CommandTexArgNode
        self.cmnd_key_args = cmnd_key_args # dict of keyword:CommandArgNode pairs

    def __repr__(self):
        string = f'{self.__class__.__name__}(\\{self.cmnd_name}'

        # add args
        for arg in self.cmnd_tex_args:
            string += '{' + f'{arg}' + '}'

        # add kwargs
        for kwarg in self.cmnd_key_args:
            string += '{' + f'{kwarg.key}={kwarg.text_group}' + '}'

        # end string
        string += ')'
        return string

class CommandTexArgNode:
    __slots__ = ['start_pos', 'end_pos', 'text_group']
    def __init__(self, text_group):
        self.start_pos = text_group.start_pos
        self.end_pos = text_group.end_pos

        self.text_group = text_group # TextGroupNode

    def __repr__(self):
        return f'{self.__class__.__name__}({self.text_group})'

class CommandKeyArgNode:
    __slots__ = ['start_pos', 'end_pos', 'key', 'text_group']
    def __init__(self, key, text_group):
        self.start_pos = key.start_pos
        self.end_pos = text_group.end_pos

        self.key = key # IDENTIFIER Token
        self.text_group = text_group # TextGroupNode

    def __repr__(self):
        return f'{self.__class__.__name__}({self.key}={self.text_group})'

class TextGroupNode:
    __slots__ = ['start_pos', 'end_pos', 'ocbrace', 'document', 'ccbrace']
    def __init__(self, ocbrace, document, ccbrace):
        self.start_pos = ocbrace.start_pos
        self.end_pos = ccbrace.end_pos

        self.ocbrace = ocbrace
        self.document = document
        self.ccbrace = ccbrace

    def __repr__(self):
        return f'{self.__class__.__name__}({self.document})'

class PlainTextNode(LeafNode):
    __slots__ = LeafNode.__slots__[:]
    __slots__.extend(['plain_text'])
    def __init__(self, plain_text:list):
        """
        plain_text is a list of OCBRACE, CCBRACE, EQUAL_SIGN, and WORD Tokens
            in any order.
        """
        self.plain_text = plain_text # list of Tokens

        if len(plain_text) > 0:
            self.start_pos = plain_text[0].start_pos
            self.end_pos = plain_text[-1].end_pos
        else:
            self.start_pos = DUMMY_POSITION.copy()
            self.end_pos = DUMMY_POSITION.copy()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.plain_text})'

# -----------------------------------------------------------------------------
# Parser Class and Related

class ParseResult:
    """
    A class that wraps results from the Parser because the parser will be
        trying out different things (is the next token plain text or a
        paragraph break? neither? then whats the next thing it could be?) and
        this ParseResult allows the Parser to try something and then undo that
        thing. An error can also can be returned if none of the things that were
        supposed to work actually work.
    """
    __slots__ = ['error', 'node', 'last_registered_advance_count', 'advance_count', 'to_reverse_count', 'affinity']
    def __init__(self):
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0
        self.affinity = 0

    def register_advancement(self):
        """
        Registers that the Parser advanced a token so that that advancement
            can be undone later if need be.
        """
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, res):
        """
        Registers a result, adding the error to this result if there was one and
            returning the node.
        """
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        self.affinity += res.affinity
        if res.error: self.error = res.error
        return res.node

    def register_try(self, res):
        """
        Returns None if the given result did not work and the Node of
            the result if it did.
        """
        if res.error:
            self.affinity += res.affinity
            self.to_reverse_count = res.advance_count
            return None
        return self.register(res)

    def reversing(self):
        """
        The last try is being reverse so set the to_reverse_count back to 0 and
            return what it was so that it can be reversed.
        """
        to_reverse = self.to_reverse_count
        self.to_reverse_count = 0
        return to_reverse

    def add_affinity(self, amt=1):
        """
        Affinity is how far along the result was getting before it ran into an
            error. This is useful for when there are multiple possibilities as
            to where the errors my be coming from such as in the writing rule
            of this language's grammar. This affinity can be used to see whether
            any of the rules applied or not because if non of them did, then
            the parser is probably just at the end of the file.
        """
        self.affinity += amt

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self

class Parser:
    """
    Creates an Abstract Syntax Tree based on the rules in grammar.txt.

    Look at grammar.txt for the outline of what the Parser is trying to do.
        It takes each rule and recursively tries to make it work. When a rule
        does not work, it returns a ParseResult with an error in
        ParseResult.error. In the case of the error, the index is changed
        back to what it was before the Parser tried the rule.
        If there was no error, then the Node that was successfully created by
        the rule is returned.

    This Parser uses a top-down approach to parsing, as opposed to a bottom-up
        approach to parsing, which is a far harder method of parsing to write
        a Parser for.
    """
    def __init__(self, tokens, print_progress_bar=False):

        # Progress Printing Info
        self._print_progress_bar = print_progress_bar
        self._tokens_len = len(tokens)
        file_path = '' if self._tokens_len == 0 else tokens[0].start_pos.file_path
        self._progress_bar_prefix = prog_bar_prefix('Parsing', file_path)
        self._prog_bar_refresh = calc_prog_bar_refresh_rate(self._tokens_len)

        # Things needed to actually parse the tokens
        self._tokens = tokens
        self._tok_idx = -1
        self._current_tok = None
        self._advance()

    def parse(self):
        """
        Returns a ParseResult with either an error in res.error or a node in
            res.node
        """
        if self._print_progress_bar:
            print_progress_bar(self._tok_idx, self._tokens_len, self._progress_bar_prefix)

        if self._current_tok.type == TT.FILE_START:
            res = self._file()
        else:
            res = self._document()

        if self._print_progress_bar:
            print_progress_bar(self._tok_idx, self._tokens_len, self._progress_bar_prefix)

        return res

    # ------------------------------
    # Main Helper Methods

    def _advance(self, parse_result=None):
        """
        Advances to the next token. It returns the token before the new one and
            registers an advancement with the given parse_result for convenience.
        """
        prev_token = self._current_tok

        if parse_result:
            parse_result.register_advancement()

        self._tok_idx += 1
        self._update_current_tok()

        return prev_token

    def _reverse(self, parse_result):
        self._tok_idx -= parse_result.reversing()
        self._update_current_tok()

    def _update_current_tok(self):
        if self._tok_idx >= 0 and self._tok_idx < len(self._tokens):
            self._current_tok = self._tokens[self._tok_idx]
        else:
            # TT.NONE_LEFT will NOT match any Tokens needed for any rule,
            #   forcing an error to occur in each rule and the rules to
            #   terminate. This is much safer than just not changing the token
            #   any more when you run out of tokens to parse because now, even if
            #   you have a low-level rule that will accept infinitely many of a
            #   token of a certain type, that type will not be infinitely given
            #   if the list of tokens ends on it
            if self._current_tok is not None:
                self._current_tok = Token(TT.NONE_LEFT, 'NO TOKENS LEFT', self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy())
            else:
                dummy_start_pos = DUMMY_POSITION.copy()
                dummy_end_pos = dummy_start_pos.copy()
                self._current_tok = Token(TT.NONE_LEFT, 'NO TOKENS LEFT', dummy_start_pos, dummy_end_pos)

    # ------------------------------
    # Rules

    def _file(self):
        """
        A document but with a FILE_START token at the beginning and a FILE_END
            token at the end.
        """
        res = ParseResult()
        start_pos = self._current_tok.start_pos.copy()

        if self._current_tok.type == TT.FILE_START:
            file_start = self._advance(res)
        else:
            return res.failure(InvalidSyntaxError(start_pos, start_pos.copy().advance(),
                    'For some reason, your file does not begin with a FILE_START Token. This is a Compiler Error, so contact the developer and let them know.'))

        document = res.register(self._document())
        if res.error: return res

        if self._current_tok.type == TT.FILE_END:
            file_end = self._advance(res)
        else:
            return res.failure(InvalidSyntaxError(self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy(),
                f'Reached the end of the file but there was no FILE_END Token. The file must have Invalid Syntax or the compiler is having issues.\nALL TOKENS: {self._tokens}\n\nLAST TOKEN SEEN: {self._current_tok}\n\nLast Token Seen Index: {self._tok_idx}'))

        return res.success(FileNode(file_start, document, file_end))

    def _document(self):
        """
        A document is a group of paragraphs, essentially.
        """
        res = ParseResult()
        paragraphs = []

        # will eat token if there, otherwise nothing
        self._eat_pb(res)

        print_prog_bar = self._print_progress_bar
        if print_prog_bar:
            refresh = self._prog_bar_refresh
            toks_len = self._tokens_len
            prefix = self._progress_bar_prefix

        while True:
            # paragraph will be None if the try failed, otherwise it will be the
            #   new ParagraphNode
            result = self._paragraph()
            if result.error and result.affinity > 0:
                res.register(result)
                return res

            paragraph = res.register_try(result)

            # If, when we tried to make another paragraph, it failed,
            #   that means that there are no more paragraphs left in the
            #   document, so undo the try by going back the number of
            #   tokens that the try went forward
            if not paragraph:
                self._reverse(res)
                break
            else:
                if print_prog_bar:
                    i = self._tok_idx
                    if (i % refresh) == 0:
                        print_progress_bar(i, toks_len, prefix)

                paragraphs.append(paragraph)

        self._eat_pb(res)

        return res.success(DocumentNode(paragraphs))

    def _paragraph(self):
        """
        A peice of writing, with a paragraph break before it possibly.
        """
        res = ParseResult()

        start_pos = self._current_tok.start_pos.copy()

        # Check for Paragraph Break
        paragraph_break = self._eat_pb(res)


        # Check for Writing
        writing = res.register(self._writing())

        if res.error:
            return res

        # writing should be a WritingNode and paragraph_break is a Token of
        #   type PARAGRAPH_BREAK
        return res.success(ParagraphNode(paragraph_break, writing))

    def _writing(self):
        """
        A peice of writing such as something to run in python, a command def
            or command call, text group, or pain text.
        """
        res = ParseResult()

        start_pos = self._current_tok.start_pos.copy()

        results = []
        new_res = self._python()
        results.append(new_res)
        writing = res.register_try(new_res)

        if not writing:
            self._reverse(res)
            new_res = self._cmnd_def()
            results.append(new_res)
            writing = res.register_try(new_res)

        if not writing:
            self._reverse(res)
            new_res = self._cmnd_call()
            results.append(new_res)
            writing = res.register_try(new_res)

        if not writing:
            self._reverse(res)
            new_res = self._plain_text()
            results.append(new_res)
            writing = res.register_try(new_res)

        if not writing:
            self._reverse(res)
            new_res = self._text_group()
            results.append(new_res)
            writing = res.register_try(new_res)

        if not writing:
            best_result = None
            for result in results:
                if result.affinity > 0 and ((not best_result) or result.affinity > best_result.affinity):
                    best_result = result

            if not best_result:
                return res.failure(InvalidSyntaxError(self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy(),
                    'There was no writing, but writing was expected.'
                    ))
            else:
                return res.failure(best_result)

        # writing should be either a PythonNode or a PlainTextNode
        return res.success(WritingNode(writing))

    def _python(self):
        """
        This fulfills the python rule of the grammar.
        """
        res = ParseResult()

        ct = self._current_tok
        type = self._current_tok.type

        # Python Switch Statement to figure out whether the token is a Python Token
        try:
            python = {
                TT.EXEC_PYTH1: ct,
                TT.EVAL_PYTH1: ct,
                TT.EXEC_PYTH2: ct,
                TT.EVAL_PYTH2: ct
            }[ct.type]
        except KeyError:
            return res.failure(InvalidSyntaxError(ct.start_pos.copy(), ct.start_pos.copy().advance(),
                    'Expected a Token of Type PASS1EXEC, PASS1EVAL, PASS2EXEC, or PASS1EVAL but did not get one.')
                )

        self._advance(res)

        # python should be a single python Token of type PASS1EXEC or PASS2EXEC
        #   or PASS1EVAL or PASS2EVAL
        return res.success(PythonNode(python))

    def _cmnd_def(self):
        """
        A command definition. For example:

        \\hi = (\\first_name, \\last_name={}) {
            Hello \\first_name \\last_name
        }
        """
        res = ParseResult()

        cmnd_name = res.register(self._need_token(TT.IDENTIFIER))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        equal_sign = res.register(self._need_token(TT.EQUAL_SIGN))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        cmnd_params = []

        # (OPAREN PB? (cmnd_params PB? (COMMA PB? cmnd_params)*)? PB? CPAREN)?
        oparen = res.register_try(self._need_token(TT.OPAREN))
        if oparen:

            res.add_affinity()

            self._eat_pb(res)

            cmnd_param = res.register_try(self._cmnd_param())

            if not cmnd_param:
                self._reverse(res)
            else:
                res.add_affinity()
                cmnd_params.append(cmnd_param)

                while True:

                    self._eat_pb(res)

                    comma = res.register_try(self._need_token(TT.COMMA))

                    if not comma:
                        self._reverse(res)
                        break

                    res.add_affinity()

                    cmnd_param = res.register(self._cmnd_param())
                    if res.error:
                        return res.failure(InvalidSyntaxError(
                                comma.start_pos.copy(), comma.end_pos.copy(),
                                'Extra comma. You need to either have a variable name after it or remove it.'
                            ))

                    res.add_affinity()

                    cmnd_params.append(cmnd_param)

            self._eat_pb(res)

            cparen = res.register(self._need_token(TT.CPAREN))
            if res.error:
                return res.failure(InvalidSyntaxError(
                    oparen.start_pos, oparen.end_pos,
                    'You need to have a matching closing parenthesis ")" to match this parenthisis after your parameters for the Command Definition.'
                    ))

            res.add_affinity()

        self._eat_pb(res)

        # text_group
        text_group = res.register(self._text_group())
        if res.error:
            return res.failure(InvalidSyntaxError(
                self._current_tok.start_pos, self._current_tok.end_pos,
                'Here, you need to have a pair of curly brackets "{}", at the very least, in order to finish off this command definition.'
                ))

        res.add_affinity()

        cmnd_tex_params = []
        cmnd_key_params = []
        for param in cmnd_params:
            if isinstance(param, CommandParamNode):
                cmnd_tex_params.append(param)
            elif isinstance(param, CommandKeyParamNode):
                cmnd_key_params.append(param)
            else:
                raise Exception(f'This was outputted as a command parameter but is not one: {param}')

        return res.success(CommandDefNode(cmnd_name, cmnd_tex_params, cmnd_key_params, text_group))

    def _cmnd_param(self):
        """
        A command Parameter. So either \\hi = {a default value} or \\hi
        """
        res = ParseResult()

        self._eat_pb(res)

        text_group = res.register_try(self._cmnd_key_param())
        if text_group:
            return res.success(text_group)

        self._reverse(res)

        text_group = res.register_try(self._cmnd_tex_param())
        if text_group:
            return res.success(text_group)
        else:
            self._reverse(res)
            return res.failure(InvalidSyntaxError(self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy(),
                    'Expected a Command Parameter here.'))

    def _cmnd_key_param(self):
        """
        A command parameter so \\hi = {a default value}
        """
        res = ParseResult()

        self._eat_pb(res)

        key = res.register(self._need_token(TT.IDENTIFIER))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        res.register(self._need_token(TT.EQUAL_SIGN))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        text_group = res.register(self._text_group())
        if res.error: return res

        res.add_affinity()

        return res.success(CommandKeyParamNode(key, text_group))

    def _cmnd_tex_param(self):
        """
        A command parameter that is just an IDENTIFIER
        """
        res = ParseResult()

        ident = res.register(self._need_token(TT.IDENTIFIER))

        res.add_affinity()

        if not ident:
            return res
        else:
            return res.success(CommandParamNode(ident))

    def _cmnd_call(self):
        """
        A command call like
        \\hi
                or
        \\hi{FirstName}{\\last_name={LastName}}
        """
        res = ParseResult()

        cmnd_name = res.register(self._need_token(TT.IDENTIFIER))
        if res.error: return res

        res.add_affinity()

        args = []

        while True:
            arg = res.register_try(self._cmnd_arg())

            if not arg:
                self._reverse(res)
                break

            res.add_affinity()

            args.append(arg)

        cmnd_tex_args = []
        cmnd_key_args = []

        for arg in args:
            if isinstance(arg, CommandTexArgNode):
                cmnd_tex_args.append(arg)
            elif isinstance(arg, CommandKeyArgNode):
                cmnd_key_args.append(arg)
            else:
                raise Exception(f'Expected a command argument Node, instead got: {arg}')

        return res.success(CommandCallNode(cmnd_name, cmnd_tex_args, cmnd_key_args))

    def _cmnd_arg(self):
        """
        A cmnd argument such as {FirstName} or {\\first_name={FirstName}} in

        \\hi{FirstName}{\\first_name={FirstName}}
        """
        res = ParseResult()

        arg = res.register_try(self._cmnd_key_arg())
        if arg:
            return res.success(arg)

        self._reverse(res)

        arg = res.register_try(self._cmnd_tex_arg())
        if arg:
            return res.success(arg)

        self._reverse(res)
        return res.failure(InvalidSyntaxError(
            self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy(),
            'Expected a Command Argument here.'
            ))

    def _cmnd_tex_arg(self):
        """
        A command text argument

        \\he{FirstName}
        """
        res = ParseResult()

        text_group = res.register(self._text_group())
        if res.error: return res

        res.add_affinity()

        return res.success(CommandTexArgNode(text_group))

    def _cmnd_key_arg(self):
        """
        A command key argument such as {\\first_name={FirstName}} in

        \\he{\\first_name={FirstName}}
        """
        res = ParseResult()

        res.register(self._need_token(TT.OCBRACE))
        if res.error: return res

        res.add_affinity()

        ident = res.register(self._need_token(TT.IDENTIFIER))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        res.register(self._need_token(TT.EQUAL_SIGN))
        if res.error: return res

        res.add_affinity()

        self._eat_pb(res)

        text_group = res.register(self._text_group())
        if res.error: return res

        res.add_affinity()

        res.register(self._need_token(TT.CCBRACE))
        if res.error: return res

        res.add_affinity()

        return res.success(CommandKeyArgNode(ident, text_group))

    def _text_group(self):
        """
        A text group is
            { document }
        """
        res = ParseResult()

        ocb = res.register(self._need_token(TT.OCBRACE))
        if res.error: return res

        res.add_affinity()

        document = res.register(self._document())
        if res.error: return res

        res.add_affinity()

        ccb = res.register(self._need_token(TT.CCBRACE))
        if res.error: return res

        res.add_affinity()

        return res.success(TextGroupNode(ocb, document, ccb))

    def _plain_text(self):
        res = ParseResult()
        plain_text = []

        while True:
            cc = self._current_tok
            start_pos = cc.start_pos

            # Python Switch Statement
            try:
                new_tok = {
                    TT.BACKSLASH: cc,
                    TT.EQUAL_SIGN: cc,
                    TT.COMMA: cc,
                    TT.OPAREN: cc,
                    TT.CPAREN: cc,
                    TT.OBRACE: cc,
                    TT.CBRACE: cc,
                    TT.WORD: cc
                }[cc.type]

                # If I remember correctly, you cannot directly wrap the dict
                #   in this append method because it appends the error
                #   to the list when there is an error, which is problematic
                plain_text.append(new_tok)
                res.add_affinity()

            except KeyError:
                break

            self._advance(res)

        if len(plain_text) == 0:
            return res.failure(InvalidSyntaxError(start_pos.copy(), start_pos.copy().advance(),
                        'Expected atleast 1 WORD, BACKSLASH, OCBRACE, CCBRACE, or EQUAL_SIGN Token.'
                    )
                )

        # plain_text is a list of OCBRACE, CCBRACE, EQUAL_SIGN, and WORD Tokens
        #   in any order.
        return res.success(PlainTextNode(plain_text))

    # -------------------------------------------------------------------------
    # Non-Rule Lesser Help Methods

    def _eat_pb(self, parse_result):
        """
        Eat a PARAGRAPH_BREAK

        A helper method that, unlike the other methods, just exists because
            there are many rules with PARAGRAPH_BREAK? in them. This
            method does that, returning None if the current token is not
            a PARAGRAPH_BREAK and the PARAGRAPH_BREAK Token if there is one.
            If a PARAGRAPH_BREAK token is found, the method also advances past
            past it.
        """
        par_break = None
        if self._current_tok.type == TT.PARAGRAPH_BREAK:
            par_break = self._advance(parse_result)

        return par_break

    def _need_token(self, token_type):
        """
        A helper method that just checks that a token exists right now. Will
            return a ParseResult with an error if the token is not the required
            one and a ParseResult with the node of the result being the token if
            the current token is the correct one.

        This method exists not because there is a Node for it (there is not one)
            but because what this method does is something that needs to be done
            a lot in the parse methods.
        """
        res = ParseResult()

        if not (self._current_tok.type == token_type):
            return res.failure(InvalidSyntaxError(self._current_tok.start_pos.copy(), self._current_tok.end_pos.copy(),
                        f'Expected a Token of type {token_type}, but got token {self._current_tok}'))

        return res.success(self._advance(res))

# -----------------------------------------------------------------------------
# Interpreter and Related Classes

class RunTimeResult:
    """
    Wraps a return value in the Interpreter so that, when a visit method
        finishes visiting a Node, it can tell the Node that visited it various
        things such as whether to return immediately or not.
    """
    __slots__ = ['value', 'error']
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = None
        self.error = None

    def register(self, res):
        """
        Register the returned result from a Node you just visited. This way,
            if you should return because an error occured or something, you can.
        """
        self.error = res.error
        return res.value

    def success(self, value):
        self.reset()
        self.value = value
        return self

    def failure(self, error):
        self.reset()
        self.error = error
        return self

class SymbolTable:
    """
    The symbol table is used to store the commands.
    """
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def get(self, name):
        """
        Returns the value for the name if it is in the SymbolTable, None otherwise
        """
        value = self.symbols.get(name, None)
        if value == None and self.parent:
          return self.parent.get(name)
        return value

    def set(self, name, value):
        """
        Sets a the value for a name in the symbol table
        """
        self.symbols[name] = value

    def remove(self, name):
        """
        Removes a name from the symbol table.
        """
        self.symbols.pop(name)

    def import_(self, other_symbol_table, commands_to_import=None):
        """
        Imports the symbols of the other symbol table into this one.

        If commands_to_import is None, then import every command. Otherwise,
            only import the commands with the names listed.
        """
        if commands_to_import is None:
            self.symbols.update(other_symbol_table.symbols)

        else:
            oth_syms = other_symbol_table.symbols

            for command_name in commands_to_import:
                if command_name in oth_syms:
                    self.symbols[command_name] = oth_syms[command_name]
                else:
                    raise AssertionError(f'Could not import {command_name}.')

    def copy(self):
        import copy

        new = SymbolTable(None if self.parent is None else self.parent.copy())
        new.symbols = copy.deepcopy(self.symbols)

        return new

    def __repr__(self):
        string = f'\n{type(self).__name__}('
        string += f'symbols={self.symbols}'
        string += ')'
        return string

class Context:
    """
    Provides Context for every command/amount of python code that is run. By
        that I mean that the Context determines what commands and variables are
        available and when.
    """
    __slots__ = ['display_name', 'file_path', 'entry_pos', 'parent',
            '_globals', '_locals', 'symbols', '_token_document', 'global_level']
    def __init__(self, display_name, file_path, parent=None, entry_pos=None, token_document=None, globals=None, locals=None, symbol_table=None):
        """
        Context could be a function if in a function or the entire program
            (global) if not in a function.
        """
        self.display_name = display_name # the command/program name
        self.file_path = file_path # the path to the file that the command is in
        self.entry_pos = entry_pos # the position in the code where the context changed (where the command was called)
        self.parent = parent # Parent context if there is one

        # These are the globals and locals used by Python. The SymbolTable is
        #   used for Commands, not these
        self._globals = globals # dict or None

        self._locals = locals # dict or None

        # Make sure that there are globals
        self.globals() # will throw an error if there are no globals, even in parent contexts

        if symbol_table is not None:
            assert_instance(symbol_table, SymbolTable, or_none=False)
            self.symbols = symbol_table # SymbolTable
        elif parent is not None and parent.symbols is not None:
            self.symbols = SymbolTable(parent.symbols)
        else:
            self.symbols = SymbolTable()

        if token_document is not None:
            self._token_document = token_document
        else:
            self._token_document = []

        self.global_level = True

    def __repr__(self):
        string = f'\n{type(self).__name__}(\n'
        string += f'\tdisplay_name={self.display_name}'
        string += f'\tsymbols={self.symbols}'
        string += f'\tglobals={self._globals}'
        string += f'\tlocals={self._locals}'
        string += f'\tparent={self.parent}'
        string += '\n)'
        return string

    def copy(self):
        _globals = None if self._globals is None else {key:val for key, val in self._globals.items()}
        _locals = None if self._locals is None else {key:val for key, val in self._locals.items()}
        entry_pos = None if self.entry_pos is None else self.entry_pos.copy()
        parent = None if self.parent is None else self.parent.copy()

        new = Context(self.display_name, self.file_path, parent, entry_pos, self._token_document[:], _globals, _locals)

        new.symbols = self.symbols.copy()
        return new

    def gen_child(self, child_display_name:str, child_entry_pos=None, locals_to_add=None):
        """
        Generates a child context i.e. a subcontext such as that which is inside
            a command.

        locals_to_add are things like the \\test variable below, which should
            be made available to any Python Code that is inside the command

        \\# Global Context
        \\hello = (\\test) = {
            \\# This should have a subcontext where commands can be defined in
            \\#     here but not mess with those defined in the global context/
            \\#     any parent context
            \\test \\# is defined in this child context
        }
        \\# \\test is undefined here, in this global context
        """
        # Generate the new python locals. Because only one locals dict can be
        #   passed to an exec or eval method at a time, it must have all the
        #   references to parent locals in it so that it works as if it could
        #   look up the locals hierarchy as the SymbolTables do for Commands
        # In other words, the child Context's locals must be a superset of this
        #   Context's locals
        child_lcls = {} if (self._locals is None) else {key:val for key, val in self._locals.items()}

        if locals_to_add:
            child_lcls.update(locals_to_add)

        parent = self

        # Give the new context a reference to globals so that it does not have
        #   to walk up a bunch of parents to get it anyway
        child = Context(child_display_name, self.file_path, parent, child_entry_pos, self.token_document(), self.globals(), child_lcls, SymbolTable(self.symbols))
        child.global_level = False
        return child

    def import_(self, other_context, tokens_to_import=[], commands_to_import=None):
        """
        Takes another context and imports its contents into this one.
        """
        self.symbols.import_(other_context.symbols, commands_to_import)
        self.globals().update(other_context.globals())

        self.token_document().extend(tokens_to_import)

    def globals(self):
        if self._globals is not None:
            return self._globals
        elif self.parent is not None:
            return self.parent.globals()
        else:
            raise Exception("You did not pass in globals to the Global Context.")

    def locals(self):
        return self._locals

    def token_document(self):
        """
        The list of tokens that should be given to the Placer object to actually
            make the PDFDocument.
        """
        return self._token_document

    def set_token_document(self, new_doc):
        self._token_document = new_doc

class InterpreterFlags:
    """
    Flags for the Interpreter so that it can know what to do when it does
        a pass over an Abstract Syntax Tree created by the Parser.

    The difference between these flags and the context in the Interpreter is
        that things in the flags stay the same for the entire AST pass
        whereas the things in the context could change at each visit to a node.
    """
    def __init__(self):
        pass

class Interpreter:
    """
    The interpreter visits each node in the Abstract Syntax Tree generated
        by the Parser and actually runs the corresponding code for the
        node.
    """
    def __init__(self):
        self._context_stack = []
        self._curr_context = None

        self._command_node_stack = []
        self._curr_command_node = None

    def _push_context(self, context):
        self._context_stack.append(context)
        self._curr_context = context

    def _pop_context(self):
        self._context_stack.pop()
        self._curr_context = self._context_stack[-1] if len(self._context_stack) > 0 else None

    def curr_context(self):
        return self._curr_context

    def _push_command_node(self, command_node):
        self._command_node_stack.append(command_node)
        self._curr_command_node = command_node

    def _pop_command_node(self):
        self._command_node_stack.pop()
        self._curr_command_node = self._command_node_stack[-1] if len(self._command_node_stack) > 0 else None

    def curr_command_node(self):
        return self._curr_command_node

    def visit_root(self, node, context, flags, print_progress=False):
        """
        The visit to the root node of an AST.
        """
        if print_progress:
            print(prog_bar_prefix(f'{OUT_TAB}Running AST for ', f'{context.display_name}', align='>', suffix='', append='...'))

        prev_context = self._curr_context
        self._curr_context = context

        result =  self.visit(node, context, flags)

        self._curr_context = prev_context

        if print_progress:
            print(prog_bar_prefix(f'{OUT_TAB}Done Running AST for ', context.display_name, align='>', suffix='', append=''))

        return result

    def visit(self, node, context, flags):
        method_name = f'_visit_{type(node).__name__}'
        method = getattr(self, method_name, self._no_visit_method)
        return method(node, context, flags)

    def _no_visit_method(self, node, context, flags):
        raise Exception(f'No _visit_{type(node).__name__} method defined in Interpreter')

    # ------------------------------
    # Rule Implementations

    def _visit_FileNode(self, node, context, flags):
        res = RunTimeResult()
        result = res.register(self.visit(node.document, context, flags))

        if res.error:
            return res

        return res.success(result)

    def _visit_DocumentNode(self, node, context, flags):
        res = RunTimeResult()

        document = []

        was_global = context.global_level

        if was_global:
            context.global_level = False

        for paragraph in node.paragraphs:
            write_tokens = res.register(self.visit(paragraph, context, flags))

            if res.error:
                return res
            else:
                if was_global:
                    context.token_document().extend(write_tokens)
                document.extend(write_tokens)

        if was_global:
            context.global_level = True

        return res.success(document)

    def _visit_ParagraphNode(self, node, context, flags):
        res = RunTimeResult()

        # How long the document has gotten so far
        i = len(context.token_document())

        # Visit the writing (could be Plaintext, Python, command def, or a Command call)
        write_tokens = res.register(self.visit(node.writing, context, flags))

        if res.error:
            return res

        if len(write_tokens) > 0:
            # Command was called and this Class was used to make the length
            #   of the write_tokens > 0 because a command was called
            if write_tokens[0] == Interpreter.CommandCalled:
                write_tokens.pop(0)

            if node.paragraph_break:
                # Add the paragraph break to before the current text was added
                context.token_document().insert(i, node.paragraph_break)

        return res.success(write_tokens)

    def _visit_WritingNode(self, node, context, flags):
        """
        Visits a WritingNode. If successful, this method will return a string of
            what the ParagraphNode is supposed to write.
        """
        res = RunTimeResult()
        write_tokens = res.register(self.visit(node.writing, context, flags))

        # Error Handling
        if res.error:
            return res

        return res.success(write_tokens)

    def _visit_PythonNode(self, node, context, flags):
        res = RunTimeResult()
        python_token = node.python
        tt = python_token.type

        # Execute or eval python
        if tt == TT.EXEC_PYTH1:
            python_result = exec_python(python_token.value, context.globals(), context.locals())
        elif tt == TT.EVAL_PYTH1:
            python_result = eval_python(python_token.value, context.globals(), context.locals())

        # For second pass python, it needs to be kept until we are actually
        #   placing the text on the PDF, then the Placer will be made available
        #   to the python and the code can make changes to the PDF
        elif tt in (TT.EXEC_PYTH2, TT.EVAL_PYTH2):
            python_result = [python_token.gen_pass_2_python( \
                    None if context.locals() is None else \
                        {key:val for key, val in context.locals().items()})]
        else:
            raise Exception(f"The following token was found in a PythonNode, it is not supposed to be in a PythonNode: {tt}")

        if isinstance(python_result, type(None)):
            python_result = []
        elif isinstance(python_result, str):
            python_result = Tokenizer.plaintext_tokens_for_str(python_result)
        elif isinstance(python_result, MarkedUpText):
            python_result = Tokenizer.tokens_for_marked_up_text(python_result)
        elif isinstance(python_result, Exception) or issubclass(type(python_result), Exception):
            return res.failure(PythonException(node.start_pos.copy(), node.end_pos.copy(),
                'An error occured while running your Python code.', python_result, context))

        return res.success(python_result)

    def _visit_CommandDefNode(self, node, context, flags):
        res = RunTimeResult()

        cmnd_name = node.cmnd_name.value
        cmnd_params = node.cmnd_params
        cmnd_key_params = node.cmnd_key_params
        text_group = node.text_group

        context.symbols.set(cmnd_name, Command(
            cmnd_params,
            cmnd_key_params,
            text_group
            ))

        return res.success([])

    def _visit_CommandCallNode(self, node, context, flags):
        res = RunTimeResult()

        tokens = []

        cmnd_name_str = node.cmnd_name.value
        command_to_call = context.symbols.get(cmnd_name_str)

        self._push_command_node(node)

        if command_to_call is None:
            # The command is undefined
            return res.failure(RunTimeError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                '\\' + f'"{cmnd_name_str}" is not defined at this point in the code.',
                context
                ))
        elif isinstance(command_to_call, TextGroupNode):
            # Handle when the "command" is actually a parameter that contains
            #   text. For example, in
            #
            #   \hello = (\test) {
            #       \test
            #   }
            #
            #   \test is a actually storing a TextGroupNode when the command
            #   \hello is called, so this method handles returning the TextGroupNode
            #   that that \test contains when \test is called

            result = res.register(self.visit(command_to_call, context, flags))

            if res.error: return res

            if result:
                tokens.extend(result)
        else:
            # Command is defined and we need to call it
            min_args = len(command_to_call.params)
            max_args = min_args + len(command_to_call.key_params)

            num_positional_args = len(node.cmnd_tex_args)
            num_key_args = len(node.cmnd_key_args)
            num_args_given = num_positional_args + num_key_args

            # Check if enough positional arguments were given
            if num_positional_args < min_args:
                return res.failure(InvalidSyntaxError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                    f'The "{cmnd_name_str}" command requires {min_args} argument(s), but {num_positional_args} was/were given.',
                    ))

            # Check if too many arguments were given
            if num_args_given > max_args:
                return res.failure(InvalidSyntaxError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                    f'The "{cmnd_name_str}" command takes {max_args} argument(s) max, but {num_args_given} was/were given.',
                    ))

            cmnd_args = {}

            # Add all the command names first
            cmnd_and_key_param_names = []

            for param in command_to_call.params:
                name = param.identifier.value

                if name in cmnd_and_key_param_names:
                    return res.failure(InvalidSyntaxError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                            f'The argument "{name}" was given more than one time. Every argument can only be given once, either by a key-argument or a positional argument.'
                        ))

                cmnd_and_key_param_names.append(name)

            # Take each Parameter key-value pair (so the key-value pairs
            #   in the definition of the command) and add them to the dict
            for cmnd_key_param in command_to_call.key_params:
                name = cmnd_key_param.key.value

                # Now add the key-params because the positional arguments will
                #   fullfill parameters and key-parameters in the order that
                #   they are in cmnd_and_key_param_names
                if name in cmnd_and_key_param_names:
                    return res.failure(InvalidSyntaxError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                            f'The argument "{name}" was given more than one time. Every argument can only be given once, either by a key-argument or a positional argument.'
                        ))
                cmnd_and_key_param_names.append(name)

                cmnd_args[name] = cmnd_key_param.text_group

            # Now replace those key-value pairs from the definiton of the command
            #   with those given in the call of command
            for key_arg in node.cmnd_key_args:
                # key params CommandKeyParamNode
                key = key_arg.key.value

                if not (key in cmnd_args):
                    return res.failure(InvalidSyntaxError(key_arg.key.start_pos.copy(), key_arg.key.end_pos.copy(),
                        f'"{key}" is not defined in command "{cmnd_name_str}". In other words, this key is not defined as a key-argument in the command\'s definition.',
                        ))

                cmnd_args[key] = key_arg.text_group

            # now take each name from the POSITIONAL-ARGUMENT names provided in
            #   the command's definition and provide the values for them from
            #   the command call
            for param_name, arg in zip(cmnd_and_key_param_names, node.cmnd_tex_args):
                # params are CommandParamNode
                cmnd_args[param_name] = arg.text_group

            # Init py_locals, the python local variables to add to the current
            #   context
            py_locals = {}

            for key, arg in cmnd_args.items():
                # Visit the argument node and get the tokens from it
                new_tokens = res.register(self.visit(arg, context, flags))

                # Convert the tokens to MarkedUpText, something that can be used
                #   in Python
                marked_up_text = Tokenizer.marked_up_text_for_tokens(new_tokens)

                if res.error:
                    return res

                if marked_up_text == '<NONE>':
                    marked_up_text = None

                # Assign each python local to its marked_up_text
                py_locals[key] = marked_up_text

            child_context = context.gen_child(cmnd_name_str, node.start_pos.copy(), py_locals)

            # Just check to make sure that a value has been passed for each needed argument
            for key, value in cmnd_args.items():
                if value == 0:
                    return res.failure(InvalidSyntaxError(node.cmnd_name.start_pos.copy(), node.cmnd_name.end_pos.copy(),
                        f'"{key}", an argument in {cmnd_name_str}, has no value. You need to pass in an argument for it in this call of the command.',
                        ))
                else:
                    child_context.symbols.set(key, value)

            self._push_context(child_context)

            # actually run the command now that its variables have been added to the context
            result = res.register(self.visit(command_to_call.text_group, child_context, flags))
            if res.error: return res

            tokens = result

            self._pop_context()

        self._pop_command_node()

        if len(tokens) > 0:
            # Find the first Token and set space_before to True if the
            #   command call had space_before = True, otherwise set it False
            for token in tokens:
                if isinstance(token, Token):
                    token.space_before = node.cmnd_name.space_before
                    break

        # Tells the Paragraph Node that a Command was called so that it can
        #   decide whether to insert a paragraph break depending on whether
        #   there was one before the Command was called or not
        tokens.insert(0, Interpreter.CommandCalled)

        return res.success(tokens)

    def _visit_TextGroupNode(self, node, context, flags):
        res = RunTimeResult()
        doc_tokens = res.register(self.visit(node.document, context, flags))

        if res.error:
            return res

        for token in doc_tokens:
            if isinstance(token, Token):
                token.space_before = node.ocbrace.space_before
                break

        return res.success(doc_tokens)

    def _visit_PlainTextNode(self, node, context, flags):
        res = RunTimeResult()
        return res.success(node.plain_text)

    # -----------------------------
    # Helper Classes
    class CommandCalled:
        """
        A helper class that just tells the Paragraph Node that a Command was
            called so that it can make an imformed decision on whether to add a
            paragraph break
        """
        pass

# -----------------------------------------------------------------------------
# Compiler Class

class CompilerProxy:
    """
    The actual object that is given to files being compiled named 'compiler'.
        The reason this object is given and not the actual compiler because
        this makes it clear what methods are actually meant to be used in
        the files being compiled.
    """
    def __init__(self, compiler):
        self._compiler = compiler

    # ---------------------------------
    # Methods for Directory/File Finding

    def main_file_path(self):
        """
        The path to the main/input file that the compiler started with.
        """
        return self._compiler.main_file_path()

    def main_file_dir(self):
        """
        The directory that the main/input file is in.
        """
        return self._compiler.main_file_dir()

    def curr_file_path(self):
        """
        The path to the file that is currently being compiled i.e. the file
            that you are in when you call this method.
        """
        return self._compiler.curr_file_path()

    def curr_file_dir(self):
        """
        The directory that the current file being run is in.
        """
        return self._compiler.curr_file_dir()

    # ---------------------------------
    # Methods for importing/inserting files

    def strict_import_file(self, file_path):
        self._compiler.strict_import_file(file_path)

    def std_import_file(self, file_path):
        self._compiler.std_import_file(file_path)

    def import_file(self, file_path):
        self._compiler.import_file(file_path)

    def far_import_file(self, file_path):
        self._compiler.far_import_file(file_path)

    def insert_file(self, file_path):
        self._compiler.insert_file(file_path)

    def strict_insert_file(self, file_path):
        self._compiler.strict_insert_file(file_path)

    def far_insert_file(self, file_path):
        self._compiler.far_insert_file(file_path)

    # ---------------------------------
    # Other Methods

    def placer_class(self):
        return self._compiler.placer_class()

    def set_placer_class(self, placer_class):
        return self._compiler.set_placer_class(placer_class)


class Compiler:
    """
    This object orchestrates the compilation of plaintext files into PDFs
    """
    def __init__(self, input_file_path, path_to_std_dir, print_progess_bars=False):
        self._commands = {}
        self._files_by_path = {}
        assert path.isfile(input_file_path), f'The given path is not to a file or does not exist: {input_file_path}'
        self._input_file_path = input_file_path
        self._input_file_dir = path.dirname(input_file_path)
        self._std_dir_path = path_to_std_dir
        self._print_progress_bars = print_progess_bars

        self._toolbox = ToolBox(self)
        self._compiler_poxy = CompilerProxy(self)

        self._placer_class = NaivePlacer

        self._interpreter_stack = []

        # The globals that will be copied every time a fresh set of globals
        #   is needed
        self._globals = {'__name__': __name__, '__doc__': None, '__package__': None,
            '__loader__': __loader__, '__spec__': None, '__annotations__': None,
            '__builtins__': _copy.deepcopy(globals()['__builtins__']),
            'compiler':self._compiler_poxy, 'toolbox':self._toolbox}

        #   remove any problematic builtins from the globals
        rem_builtins = []
        for key in rem_builtins:
            self._globals['__builtins__'].pop(key)

    # -------------------------------------------------------------------------
    # Main Methods

    def compile_pdf(self):
        """
        Compiles the PDF and returns the PDFDocument that can be used to draw
            the PDF multiple times to different files.
        """
        fresh_context = self._fresh_context(self._input_file_path)

        # Now run the main\input file
        self._insert_file(self._input_file_path, fresh_context, print_progress=self._print_progress_bars)

        return self._placer_class(fresh_context.token_document(), fresh_context.globals(), self._input_file_path, self._print_progress_bars).create_pdf()

    def compile_and_draw_pdf(self, output_pdf_path):
        """
        Convenience function that compiles and draws the PDF
        """
        self.compile_pdf().draw(output_pdf_path, print_progress=self._print_progress_bars)

    # -------------------------------------------------------------------------
    # Helper Methods

    def _fresh_globals(self):
        """
        Returns a fresh set of globals as they are before the program starts compiling.

        These globals are for the python exec and eval methods that are used to
            run python code.
        """
        return {key:val for key, val in self._globals.items()}

    def _fresh_context(self, file_path):
        """
        Returns a fresh context for running a file as if it were the main/input
            file (even if it isn't actually the main/input file).
        """
        parent = None; entry_pos = None; token_document = []; locals = None
        context = Context(file_path, file_path, parent, entry_pos, token_document, self._fresh_globals(), locals, SymbolTable())

        # insert the standard file into the context
        self._insert_file(self._path_to_std_file(STD_LIB_FILE_NAME), context, print_progress=self._print_progress_bars)

        return context

    def _push_interpreter(self):
        """
        Pushes a new Interpreter onto the interpreter stack.
        """
        self._interpreter_stack.append(Interpreter())

    def _pop_interpreter(self):
        """
        Pops the _curr_interpreter off the interpreter stack.
        """
        return self._interpreter_stack.pop()

    def _curr_interpreter(self):
        """
        Returns the current Interpreter.
        """
        _is = self._interpreter_stack
        return None if len(_is) <= 0 else _is[-1]

    def _curr_context(self):
        """
        Returns the current Context.
        """
        ci = self._curr_interpreter()
        return None if ci is None else ci._curr_context

    def _curr_tok_document(self):
        """
        Returns the current document made of tokens, not to be confused with
            the PDFDocument object that is returned by the Placer. The "document"
            returned by this method is a list of Tokens that can be given to
            a Placer to produce a PDFDocument.
        """
        ci = self._curr_interpreter()
        return None if ci is None else ci._curr_document

    def _compiler_import_file(self, file_path, print_progress=False):
        """
        Imports a file. If the file has not already been imported by the compiler,
            this method will read in the file, tokenize, and parse it into
            an Abstract Syntax Tree (AST), before caching the raw_text, tokens,
            and ast in a File object and returning the File object. If the file
            has already been imported, this method will return the cached File
            object.

            To run the file object, the root of the AST must be visited by the
            Interpreter. This can be acheived by doing

            Interpreter().visit_root(file.ast)
        """
        assert path.isfile(file_path), f'Could not import "{file_path}"'
        file_path = path.abspath(file_path)

        # If file already imported, just return the file
        if file_path in self._files_by_path:
            return self._files_by_path[file_path]

        file = File(file_path)
        self._files_by_path[file_path] = file

        try:
            with open(file_path) as f:
                file.raw_text = f.read() # Raw text that the file contains
        except:
            try:
                with open(file_path, encoding='utf-8') as f:
                    file.raw_text = f.read() # Raw text that the file contains

            except:
                try:
                    with open(file_path, encoding='utf-16') as f:
                        file.raw_text = f.read() # Raw text that the file contains
                except:
                    try:
                        with open(file_path, encoding='utf-32') as f:
                            file.raw_text = f.read() # Raw text that the file contains
                    except:
                        raise AssertionError('Could not decode the given file as utf-8, utf-16, or utf-32.')


        file.tokens = Tokenizer(file.file_path, file.raw_text, print_progress_bar=print_progress).tokenize()

        # Returns a ParseResult, so need to see if any errors. If no Errors, then set file.ast to the actual abstract syntax tree
        file.ast = Parser(file.tokens, print_progress_bar=print_progress).parse()

        if file.ast.error is not None:
            raise file.ast.error
        else:
            file.ast = file.ast.node

        return file

    def _run_file(self, file, context, print_progress=False):
        """
        Runs a file, importing it first if need be, and returns the tokens and
            context that that the file generates. By "import", I mean that it
            loads the file into memory, tokenizes it and makes it into an AST,
            not that it does the same thing as the \\import command

        context is the current Context that you want the file to be run in.
        """
        if isinstance(file, str):
            # It should be a file path
            file_obj = self._compiler_import_file(file, print_progress)
        else:
            # It should be a File object
            file_obj = file

        if file_obj.being_run:
            raise AssertionError(f"The given file is already being run (imported or inserted), so you probably have a circular import which is not allowed: {file_obj.file_path}")
        else:
            file_obj.being_run = True

        self._push_interpreter()

        # Save the context's current display_name and file_path
        old_disp_name = context.display_name
        old_path = context.file_path

        # Give the context the display name and file path of the file it is now
        #   going into
        context.display_name = file_obj.file_path
        context.file_path = file_obj.file_path

        # Since just pushed interpreter, self._curr_interpreter() should not be None
        result = self._curr_interpreter().visit_root(file_obj.ast, context, InterpreterFlags(), print_progress)

        # Restore the context's display name and file_path to what they were before
        context.display_name = old_disp_name
        context.file_path = old_path

        self._pop_interpreter()

        if result.error:
            raise result.error

        file_obj.being_run = False

        return result.value # Return the tokens gotten by running the file

    def _insert_file(self, file_path, context, print_progress=False):
        """
        Inserts the file into the current file. This means that the file
            must be run with the current context as if it were directly in the
            file.

        context is the context that this file is being inserted into
        """
        # Since the context is directly given to self._run_file, all of the
        #   commands and whatnot in the global portion of the file will be
        #   added to the given context as if it was in the context directly
        #   and not in another file

        was_global = context.global_level
        context.global_level = True

        i = len(context.token_document())

        self._run_file(file_path, context, print_progress)

        # Want to add a space before the first Token we come accross.
        # Note: the compiler may still not render a space before the token
        #   if the token is at the start of a line. That is why this is safe
        #   to do. We are meely saying "this Token should have a space before
        #   it if it makes sense to have one before it"
        doc = context.token_document()

        ci = self._curr_interpreter()
        if ci and ci.curr_command_node():
            ccc = ci.curr_command_node()

            length = len(doc)

            while True:
                if i >= length:
                    # reached end of Token document without finding a single
                    #   Token
                    break

                curr = doc[i]

                if isinstance(curr, Token):
                    # Found a Token so set whether it has a space before it based
                    #   on the current command that is being run and whether
                    #   the command has a space before it (i.e. if there is
                    #   space before \insert{file_path}, then the first token
                    #   of the inserted text from the file should have a space
                    #   before it, otherwise it should not have a space before
                    #   it)
                    curr.space_before = ccc.cmnd_name.space_before
                    break

                i += 1

        context.global_level = was_global

    def _import_file(self, file_path, context, commands_to_import=None, print_progress=False):
        """
        Imports a file. This is very different from self._insert_file because
            it takes the file, gives it a fresh context, and runs the file.
            The resulting context can be saved to the File object for the file
            because the resulting global context from running the file does
            not depend on any other file's context. In this way, once a file
            is imported once, its resulting tokens and Context can be reused
            over and over again, whereas the tokens and Context from
            self._insert_file cannot be and the file must be re-run every time
            it is inserted into a file, regardless of whether it has been
            inserted into a file before.

        context is the context that you want to import the file into.

        If commands_to_import are given, then only the commands by the names
            specified in the list of strings will be imported. All Python globals
            will still, however, be imported.
        """
        file_obj = self._compiler_import_file(file_path, print_progress)

        if file_obj.import_context is None:
            # Since this file has not yet been run, we will have to run it
            #   now with a fresh context unrelated to any other context

            # Using file_obj.file path in case it is different from the argument file_path
            context_to_import = self._fresh_context(file_obj.file_path)

            tokens = self._run_file(file_obj, context_to_import, print_progress)

            # Since the file was imported, that means it does not depend on the
            #   current context and thus the context can be saved and reused later
            file_obj.import_context = context_to_import

            # I expect most imports to have some global Python code that they
            #   want to be run on the second pass, so that code must be imported
            #   too or else it will never reach the Placer and be run.
            tokens_to_import = []
            for token in tokens:
                if isinstance(token, Token) and token.type in (TT.EXEC_PYTH2, TT.EVAL_PYTH2):
                    tokens_to_import.append(token)

            file_obj.import_tokens = tokens_to_import

        else:
            # Since this file has been imported before, just reuse the same
            #   context as last time because the context is not dependant
            #   on the current context of when/where the file is being run
            context_to_import = file_obj.import_context
            tokens_to_import = file_obj.import_tokens

        try:
            context.import_(context_to_import, tokens_to_import, commands_to_import)
        except AssertionError as e:
            raise AssertionError(f'{file_path} could not be imported because of the following error:{e}')

    def _path_to_std_file(self, file_path):
        """
        Returns the file path as a file path to a standard directory file.
        """
        # Replace the ending of the file path with the one used by all standard files
        split_file_path = file_path.split('.')

        if len(split_file_path) > 1 and split_file_path[-1] == STD_FILE_ENDING:
            split_file_path.pop()

        split_file_path.append(STD_FILE_ENDING)
        file_path = '.'.join(split_file_path)

        # check if the file exists
        file_path = path.abspath(path.join(self._std_dir_path, file_path))
        return file_path

    def _path_rel_to_file(self, file_path, curr_file=True):
        """
        Returns the file path if the given path is relative to the main file
            being run or the current file being run.
        """
        dir = self.curr_file_dir() if curr_file else self.main_file_dir()
        file_path = path.abspath(path.join(dir, file_path))
        return file_path

    def _get_near_path(self, file_path):
        """
        Gets the near path to insert/import. This checks the path relative to
            to the current file first, then checks the file relative to the
            main/input file, and then it checks the standard directory.
        """
        ret_path = cf_rel_path = self._path_rel_to_file(file_path, curr_file=True)

        if not path.isfile(ret_path):
            ret_path = input_rel_path = self._path_rel_to_file(file_path, curr_file=False)

            if not path.isfile(ret_path):
                _file_path, file_name = path.split(file_path)
                ret_path = std_path = self._path_to_std_file(file_path)

                assert path.isfile(std_path), f'Could not get near path for "{file_path}" because neither "{cf_rel_path}", nor "{input_rel_path}", nor "{std_path}" lead to a file and/or exist.'

        return ret_path

    def _get_far_path(self, file_path):
        """
        Gets the far path to insert/import. This checks the standard directory
            first and then checks the path relative to the main/input file
            and then checks the path relative to the current file.
        """
        _file_path, file_name = path.split(file_path)
        ret_path = std_path = self._path_to_std_file(file_path)

        if not path.isfile(ret_path):
            ret_path = input_rel_path = self._path_rel_to_file(file_path, curr_file=False)

            if not path.isfile(ret_path):
                ret_path = cf_rel_path = self._path_rel_to_file(file_path, curr_file=True)

                assert path.isfile(std_path), f'Could not get far path for "{file_path}" because neither "{std_path}", nor "{input_rel_path}", nor "{cf_rel_path}" lead to a file and/or exist.'

        return ret_path

    # ------------------------------------
    # Methods available from CompilerProxy

    # Methods for Inserting and Importing Files

    def insert_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot insert into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._insert_file(self._get_near_path(file_path), cc, print_progress=self._print_progress_bars)

    def strict_insert_file(self, file_path):
        """
        Runs the file at the given file path and inserts it into the current
            document.

        The file path is assumed to be relative to the current file.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot insert into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        # Actually insert the file
        self._insert_file(self._path_rel_to_file(file_path), cc, print_progress=self._print_progress_bars)

    def far_insert_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot far insert into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._insert_file(self._get_far_path(file_path), cc, print_progress=self._print_progress_bars)

    def strict_import_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.

        This file path is assumed to be relative to the main file being run.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot import into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._import_file(self._path_rel_to_file(file_path), cc, print_progress=self._print_progress_bars)

    def import_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot import into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._import_file(self._get_near_path(file_path), cc, print_progress=self._print_progress_bars)

    def std_import_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot import into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._import_file(self._path_to_std_file(file_path), cc, print_progress=self._print_progress_bars)

    def far_import_file(self, file_path):
        """
        Runs the file at the given file_path, importing its commands but not
            inserting its text into the current document.
        """
        file_path = str(file_path)
        cc = self._curr_context()
        assert cc is not None, 'Cannot import into a Non-existent Context. This is a Compiler error, report it the people making the compiler.'

        self._import_file(self._get_far_path(file_path), cc, print_progress=self._print_progress_bars)

    # Methods for retrieving files and directories for the current file.

    def main_file_path(self):
        """
        Returns the file path to the main/first/input file that is/was run.
        """
        return self._input_file_path

    def main_file_dir(self):
        """
        Returns an absolute path to the directory that the main file that is
            being run is in.
        """
        return path.dirname(self.main_file_path())

    def curr_file_path(self):
        """
        Returns an absolute path to the current file that is being run.
        """
        cc = self._curr_context()
        assert cc is not None, f'The current context was None so the current file path could not be retrieved.'
        return cc.file_path

    def curr_file_dir(self):
        """
        Returns an absolute path to the directory that the current file that is
            being run is in.
        """
        return path.dirname(self.curr_file_path())

    # Misc Methods

    def placer_class(self):
        return self._placer_class

    def set_placer_class(self, placer_class):
        """
        Sets the placer class that will be used to place the tokens on the PDF.
            This allows a person to, theoretically, create their own placer in
            a pdfo file and make the compiler use that instead.
        """
        self._placer_class = placer_class

class Command:
    """
    Represents a command in the file.
    """
    __slots__ = ['params', 'key_params', 'text_group']
    def __init__(self, params, key_params, text_group):
        self.params = params
        self.key_params = key_params
        self.text_group = text_group # This will be run for the command



