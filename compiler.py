import copy as _copy
import os
from decimal import Decimal
from collections import namedtuple as named_tuple

from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes as pagesizes

from constants import CMND_CHARS, END_LINE_CHARS, ALIGN, TT, TT_M

# -----------------------------------------------------------------------------
# Helper Global Functions

def assure_decimal(val):
    if isinstance(val, (float, int)):
        return Decimal(val)
    else:
        return val

def str_till(pattern, start_pos, string):
    """
    Returns the string until the match, and the match itself, or None, None if
        there was no match.
    """
    match = pattern.search(string, start_pos)

    if match:
        return string[start_pos:match.start()], match
    else:
        return None, None

def is_escaped(pos, text, chars_that_can_be_escaped):
    if not (text[pos] in chars_that_can_be_escaped):
        return False

    # Use a modulus to determine whether this character is escaped
    i = 0
    while (0 <= (pos - (i + 1))) and (text[pos - (i + 1)] == '\\'):
        i += 1

    # if the number of backslashes behind this character is odd, then this one will be escaped
    return ((i % 2) == 1)


def is_escaping(pos, text, chars_that_can_be_escaped):

    # If it is escaping something else then it too is escaped
    if text[pos] == '\\' and pos + 1 < len(text) and text[pos + 1] in chars_that_can_be_escaped:
        return True
    return False


def exec_python(code, exec_globals):
    """
    Executes python code and returns the value stored in 'ret' if it was
        specified as a global variable.
    """
    exec(code, exec_globals)
    if 'ret' in exec_globals:
        return exec_globals.pop('ret')
    else:
        return ''


def eval_python(code:str, exec_globals:dict):
    return eval(code)


def string_with_arrows(text, pos_start, pos_end):
    """
    Produces a string that has arrows under the problem area specified by
        pos_start and pos_end.

    Example:

    class My!Class:
          ^^^^^^^^
    """
    result = ''

    # Calculate indices
    idx_start = max(text.rfind('\n', 0, pos_start.idx), 0)
    idx_end = text.find('\n', idx_start + 1)

    if idx_end < 0:
        idx_end = len(text)

    # Generate each line
    line_count = pos_end.ln - pos_start.ln + 1
    for i in range(line_count):
        # Calculate line columns
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1

        # Append to result
        result += line + '\n'
        result += ' ' * col_start + '^' * (col_end - col_start)

        # Re-calculate indices
        idx_start = idx_end
        idx_end = text.find('\n', idx_start + 1)

        if idx_end < 0:
            idx_end = len(text)

        return result.replace('\t', '')

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
        result += f'    {self.error_name} Occured: {self.details}\n'
        result += '\n' + string_with_arrows(self.pos_start.file_text, self.pos_start, self.pos_end)
        return result

class PythonError(Error):
    def __init__(self, pos_start, pos_end, details, python_error):
        self._python_error = python_error
        super().__init__(pos_start, pos_end, 'Python Code Produced An Exception', details)

    def as_string(self):
        string = super().as_string()

        string += '\nHere is the Python Error:\n\n'
        string += f'{self.python_error}'

class ExpectedValidCmndNameError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Expected Valid Command Name', details)

class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)

class ExpectedCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Expected Character', details)

class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=''):
        super().__init__(pos_start, pos_end, 'Invalid Syntax', details)

class RTError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, 'Runtime Error', details)
        self.context = context

    def as_string(self):
        result  = self.generate_traceback()
        result += f'{self.error_name}: {self.details}'
        result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return result

    def generate_traceback(self):
        result = ''
        pos = self.pos_start
        ctx = self.context

        while ctx:
            result = f'  File {pos.fn}, line {str(pos.ln + 1)}, in {ctx.display_name}\n' + result
            pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return 'Traceback (most recent call last):\n' + result

# -----------------------------------------------------------------------------
# Position Class

class Position:
    """
    Position in a Tokenized file or a file that is being tokenized.
    """
    def __init__(self, idx, ln, col, file_path, file_text):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.file_path = file_path # The path tot he file that this is a position in
        self.file_text = file_text # The text of the file this is a position in

    def advance(self, current_char=None):
        self.idx += 1
        self.col += 1

        if current_char == '\n':
            self.ln += 1
            self.col = 0

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.file_path, self.file_text)

# -----------------------------------------------------------------------------
# File Class

class File:
    def __init__(self, file_path):
        self.file_path = file_path # Path to file
        self.raw_text = None
        self.tokens = None # The tokens that make up the File once it has been tokenized

# -----------------------------------------------------------------------------
# Token Class

class Token:
    def __init__(self, type, value, start_pos, end_pos):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.type = type
        self.value = value

    def __repr__(self):
        """
        This is what is called when you print this object since __str__ is undefined.
        """
        return f'Token("<{self.type}>":{self.value})'

# -----------------------------------------------------------------------------
# Tokenizer Class

class Tokenizer:
    """
    Takes raw text and tokenizes it.
    """
    def __init__(self, file_path, file_text):
        super().__init__()
        self._text = file_text
        self._pos = Position(-1, 0, -1, file_path, file_text)
        self._current_char = None
        self._plain_text = ''
        self._plain_text_start_pos = None
        self._tokens = []
        self._advance()

    def _advance(self, num=1):
        """Advances to the next character in the text if it should advance."""
        for i in range(num):
            self._pos.advance(self._current_char)
            self._current_char = self._text[self._pos.idx] if self._pos.idx < len(self._text) else None

            if self._current_char is None:
                break

    def tokenize(self):
        """
        Turn the raw text into tokens that the compiler can use.
        """
        self._tokens = []
        self._plain_text = ''
        what_can_be_escaped = {'{', '}', '=', '\\', '%'}

        self._tokens.append(Token(TT.FILE_START, '<FILE START>', self._pos.copy(), self._pos.copy()))

        # By default, all text is plain text until something says otherwise
        while self._current_char is not None:
            cc = self._current_char
            #print(cc, end='')
            t = None

            # NOTE: the parse methods will return None if the text is plain text
            #   and the parse method did not actually apply

            if is_escaped(self._pos.idx, self._text, what_can_be_escaped):
                self._plain_text_char()
            elif is_escaping(self._pos.idx, self._text, what_can_be_escaped):
                self._advance() # Just advance because it is just escaping something else
            elif self._match(END_LINE_CHARS):
                # self._match will advance past '\n' or '\r\n'
                pos_start = self._pos.copy()

                if self._match(END_LINE_CHARS):

                    while self._match(END_LINE_CHARS):
                        # self._match will automatically keep advancing past the '\n' and '\r\n' it finds
                        pass # Do nothing, just eat the END_LINE_CHARS now that we know that there is a PARAGRAPH_BREAK

                    t = Token(TT.PARAGRAPH_BREAK, None, pos_start, self._pos.copy())
            elif cc == ' ':
                self._try_plain_text_token()

                # Now eat all the spaces till next non-space
                while (self._current_char is not None) and (self._current_char == ' '):
                    self._advance()
            elif cc == '{':
                t = Token(TT.OCBRACE, '{', self._pos.copy(), self._pos.copy())
                self._advance()
            elif cc == '}':
                t = Token(TT.CCBRACE, '}', self._pos.copy(), self._pos.copy())
                self._advance()
            elif cc == '=':
                t = Token(TT.EQUAL_SIGN, '=', self._pos.copy(), self._pos.copy())
                self._advance()
            elif cc == '%':
                # The rest of the comment is a comment
                self._parse_comment()
            elif cc == '\\':
                t = self._parse_cntrl_seq()
            else:
                self._plain_text_char()

            # Actually append the token
            if t is not None:

                self._plain_text.strip(' ')

                self._try_plain_text_token()

                if isinstance(t, Token):
                    self._tokens.append(t)
                else:
                    # t must be a list of tokens
                    self._tokens.extend(t)

        self._plain_text.strip(' ')

        self._try_plain_text_token()

        self._tokens.append(Token(TT.FILE_END, '<FILE END>', self._pos.copy(), self._pos.copy()))

        return self._tokens

    # -------------------------------------------------------------------------
    # Parsing Methods

    def _parse_comment(self):
        """
        Parses a comment, basically just eating any characters it finds until
            the comment is done.
        """
        pos_start = self._pos.copy()
        if self._match(['%->']):
            found_match = False
            pos_end = self._pos.copy()

            # it's a continous comment, so parse until <-% is found
            while self._current_char is not None:
                if self._match(['<-%']):
                    found_match = True
                    break
                else:
                    self._advance()

            if self._current_char is None and not found_match:
                raise InvalidSyntaxError(pos_start, pos_end, 'You commented out the rest of your file because there was no matching "<-%" to end the comment.')

        else:
            # it's a one-line comment, so parse until one of END_LINE_CHARS are found

            self._advance() # Advance past '%'

            while self._current_char is not None:
                if self._match(END_LINE_CHARS):
                    break
                else:
                    self._advance()

    def _parse_cntrl_seq(self):
        """
        Parse a control sequence.
        """
        t = None

        pos_start = self._pos.copy()

        # First Pass Python -----------------------
        if self._match(TT_M.ONE_LINE_PYTH_1PASS_EXEC_START):
            # The rest of the line (or until '<\\', '<1\\', '\n', '\r\n') is python for first pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_1PASS_EXEC_END, 1, pos_start)

        elif self._match(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_START):
            # All of it is python for first pass until '<-\\' or '<-1\\'
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_END, 1, pos_start)

        elif self._match(TT_M.ONE_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_1PASS_EVAL_END, 2, pos_start, use_eval=True)

        elif self._match(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_END, 2, pos_start, use_eval=True)

        # Second Pass Python ----------------------
        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EXEC_START):
            # The rest of the line (or until '<2\\') is python for second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_2PASS_EXEC_END, 2, pos_start)

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_START):
            # All of it is python for first pass until '<-2\\'
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_END, 2, pos_start)

        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, use_eval=True)

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, use_eval=True)

        # Command --------------------------
        else:
            # It is a command, so parse it
            t = self._parse_command()

        return t

    def _parse_command(self):
        """
        Parse a command.
        """
        cmnd_name = ''
        tokens = []

        start_pos = self._pos.copy()

        #tokens.append(Token(TT.BACKSLASH, '\\'))
        self._advance() # advance past '\\'

        problem_start = self._pos.copy()

        while self._current_char is not None:
            cc = self._current_char

            if cc in CMND_CHARS:
                cmnd_name += cc
                self._advance()
            else:
                if len(cmnd_name) == 0:
                    curr_idx = self._pos.idx
                    self._advance()

                    raise ExpectedValidCmndNameError(problem_start, self._pos.copy(),
                            f'All commands must specify a valid name with all characters of it in {CMND_CHARS} "{self._text[curr_idx]}" is not one of them. You either forgot to designate a valid command name or forgot to escape the backslash before this character.')

                tokens.append(Token(TT.CMND_NAME, cmnd_name, start_pos, start_pos))

                return tokens

    def _parse_python(self, end_codes, pass_num, pos_start, use_eval=False):
        """
        Parses the string from self._pos as python code until one of the end_codes
            are reached.
        """
        python_str = ''

        pos_end = self._pos.copy()
        match_found = False

        while self._current_char is not None:
            if self._match(end_codes):
                # since found a match, self._match will advance past the
                #   match it made
                match_found = True
                break
            else:
                # Since python has not ended yet, just add the given char to it
                python_str += self._current_char
                self._advance()

            if self._current_char is None and not match_found:
                raise InvalidSyntaxError(pos_start, pos_end, 'You made the rest of your file Python because there was no matching character sequence to end this Python section of your document.')

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

    # -------------------------------------------------------------------------
    # Other Helper Methods

    def _try_plain_text_token(self):
        """
        Create a plain_text token given what is in self._plain_text
        """
        if len(self._plain_text) > 0:
            self._tokens.append(Token(TT.PLAIN_TEXT, self._plain_text, self._plain_text_start_pos, self._pos.copy()))
            self._plain_text = ''

    def _plain_text_char(self):
        """
        The current_char is a plain_text character
        """
        if self._plain_text_start_pos is None:
            self._plain_text_start_pos = self._pos.copy()
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

class Parser:
    pass

# -----------------------------------------------------------------------------
# PDF Class and Related Classes

class PDF:
    def __init__(self):
        self._writing = False

    def begin_pdf(self):
        self._writing = True

    def pause_pdf(self):
        self._writing = False

    def resume_pdf(self):
        self._writing = True

    def end_pdf(self):
        self._writing = False

class Subscriptable:
    """
    A class that allows you to designate code to run when emit() is run.
    """
    def __init__(self):
        pass

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

    def __add__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() - other.x(), self.y() - other.y())

    def __mult__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() * other.x(), self.y() * other.y())

    def __div__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() / other.x(), self.y() / other.y())

    def _assure_point(self, other):
        if isinstance(other, Point):
            return other
        raise ValueError(f'Tried to compare a point to some other thing that is not a point.\nThe other thing: {other}')

class Placer:
    """
    The object that actually places tokens onto the PDF depending on the
        templates it is using.
    """
    def __init__(self):
        self._page_count = 0
        self._default_page = PDFPageTemplate()
        self._default_paragraph = PDFParagraphTemplate()

    def default_page(self):
        return self._default_page

    def default_paragraph(self):
        return self._default_paragraph

    def page_count(self):
        return self._page_count

class Template:
    def __init__(self):
        self._margins = Margins()
        self._point = Point() # This is the placement of the upper-left-hand corner of the Template
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
            they are additive. So if you
        """
        return self._margins

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

class PDFPageTemplate(Template):
    """
    Describes how the current page should look.
    """
    def __init__(self):
        super().__init__()
        self.margins().set_all(0, 0, 0, 0)

class PDFParagraphTemplate(Template):
    """
    Describes how a paragraph should look. It does not contain text,
        it just describes how the text should be placed.
    """
    def __init__(self):
        super().__init__()
        self._alignment = ALIGN.LEFT

        # Paragraphs also have margins that will be added to the margins
        #   provided by the page. So if paragraph left margin is 1in and
        #   page left margin is 1in, the paragraph will be offset from the
        #   left corner of the page by 2 inches

        # The offsets that each LINE of the paragraph will have. These
        #   concrete offsets take precidence over the repeating left
        #   offsets (concrete offsets will be used if both concrete and
        #   repeating offsets apply to the same line). index 0 is line 1 of the
        #   paragraph
        self._concrete_left_offsets   = [Decimal(1 * inch)]
        self._concrete_right_offsets  = []

        self._repeating_left_offsets  = []
        self._repeating_right_offsets = []

    def alignment(self):
        """
        Paragraph alignment, i.e. ALIGN.RIGHT, .LEFT, .CENTER, or .JUSTIFY
        """
        return self._alignment

    def set_alignment(self, new_alignment):
        if not isinstance(new_alignment, ALIGN):
            raise TypeError(f'You tried to set the alignment of the text to {new_alignment}, which is not in the ALIGN Enum required.')
        self._align = new_alignment

class PDFParagraphLineTemplate(Template):
    def __init__(self):
        super().__init__()

class PDFWordTemplate(Template):
    """
    A template for each word in a Line of a Paragraph of a Page in the PDF.
    """
    def __init__(self):
        super().__init__()

class Font:
    def __init__(self):
        self.font_name

class Margins:
    """
    Describes the margins of something.
    """
    def __init__(self, left=0, right=0, top=0, bottom=0):
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

PAGE_SIZES = ( \
        'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10',
        'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10',
        'C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10',
        'LETTER', 'LEGAL', 'ELEVENSEVENTEEN', 'JUNIOR_LEGAL', 'HALF_LETTER',
        'GOV_LETTER', 'GOV_LEGAL', 'TABLOID', 'LEDGER'
    )

UNITS = ('inch', 'cm', 'mm', 'pica')

COLORS = ('transparent', 'aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure',
'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 'blueviolet', 'brown',
'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue',
'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan', 'darkgoldenrod',
'darkgray', 'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen',
'darkorange', 'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue',
'darkslategray', 'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink',
'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite',
'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray',
'grey', 'green', 'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo',
'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon',
'lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgreen',
'lightgrey', 'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue',
'lightslategray', 'lightslategrey', 'lightsteelblue', 'lightyellow', 'lime',
'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue',
'mediumorchid', 'mediumpurple', 'mediumseagreen', 'mediumslateblue',
'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue',
'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace',
'olive', 'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod',
'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff',
'peru', 'pink', 'plum', 'powderblue', 'purple', 'red', 'rosybrown', 'royalblue',
'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue',
'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'white', 'whitesmoke',
'yellow', 'yellowgreen', 'fidblue', 'fidred', 'fidlightblue')

class ToolBox:
    """
    A toolbox of various useful things like Constants and whatnot
    """
    def __init__(self):
        page_sizes = [getattr(pagesizes, page_size) for page_size in PAGE_SIZES]
        self._page_sizes = named_tuple('PageSizes', PAGE_SIZES)(*[(Decimal(h), Decimal(w)) for h, w in page_sizes])
        self._page_sizes_dict = {page_size:getattr(self._page_sizes, page_size) for page_size in PAGE_SIZES}

        self._units = named_tuple('Units', UNITS)(*[Decimal(getattr(units, unit)) for unit in UNITS])
        self._units_dict = {unit:getattr(self._units, unit) for unit in UNITS}

        self._colors = named_tuple('Units', COLORS)(*[getattr(colors, color) for color in COLORS])
        self._colors_dict = {color:getattr(colors, color) for color in COLORS}

        self._alignments = named_tuple('Units', [val.lower() for val in ALIGN.values()])(*[getattr(ALIGN, alignment.upper()) for alignment in ALIGN.values()])
        self._alignments_dict = {alignment.lower():getattr(self._alignments, alignment.lower()) for alignment in ALIGN.values()}

    def colors(self):
        return self._colors

    def color_by_name(self, color_name_str):
        return self._colors_dict[color_name_str.lower()]

    def page_sizes(self):
        return self._page_sizes

    def page_size_by_name(self, page_size_str):
        return self._page_sizes_dict[page_size_str.upper()]

    def units(self):
        return self._units

    def units_by_name(self, unit_name_str):
        return self._units_dict[unit_name_str.lower()]

    def alignments(self):
        self._alignments

    def alignments_by_name(self, alignment_name):
        return self._alignments_dict[alignment_name.lower()]

    def str_to_length(self, length_as_str):
        """
        Takes a length as a string, such as '4pica' or '4mm' and converts it
            into a Decimal of the specified size.
        """
        return assure_decimal(toLength(length_as_str))

    def assure_landscape(self, page_size):
        """
        Returns a tuple of the given page_size in landscape orientation, even
            if it is already/given in landscape orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.landscape(page_size)
        return (assure_decimal(h), assure_decimal(w))

    def assure_portrait(self, page_size):
        """
        Returns a tuple of the given page_size in portrait orientation, even
            if it is already/given in portrait orientation.

        Returns a tuple of form (hieght:Decimal, width:Decimal)
        """
        h, w = pagesizes.portrait(page_size)
        return (assure_decimal(h), assure_decimal(w))

# -----------------------------------------------------------------------------
# Compiler Class

class Compiler:
    def __init__(self, file_path_to_start_file, output_file_path):
        self._start_file = file_path_to_start_file
        self._commands = {}
        self._files_by_path = {}

        self._init_globals()
        self._init_commands()

    def _init_globals(self):
        self._globals = {'__name__': __name__, '__doc__': None, '__package__': None,
                '__loader__': __loader__, '__spec__': None, '__annotations__': {},
                '__builtins__': _copy.deepcopy(globals()['__builtins__'].__dict__)}

        # Now remove any problematic builtins from the globals
        rem_builtins = []
        [self._globals['__builtins__'].__dict__.pop(key) for key in rem_builtins]

    def _init_commands(self):
        self.add_command("def", "\>c.add_command(cmnd_name, code_to_run, args, kwargs)",
                args=('cmnd_name', 'code_to_run'), kwargs={'cmnd_args':None, 'cmnd_kwargs':None})

    # -------------------------------------------------------------------------
    # Main Methods

    def compile_pdf(self):
        """
        Compiles the PDF starting at self._start_file
        """
        print(self._import_file(self._start_file).tokens)

    def add_command(self, cmnd_name, code_to_run, args:tuple=None, kwargs:dict=None):
        args = tuple() if args is None else args
        kwargs = {} if kwargs is None else kwargs
        # TODO

    def run_command(self, command):
        # TODO
        pass

    # -------------------------------------------------------------------------
    # Helper Methods

    def _import_file(self, file_path):
        file_path = os.path.abspath(file_path)

        if file_path in self._files_by_path:
            return self._files_by_path[file_path]

        file = File(file_path)
        self._files_by_path[file_path] = file

        with open(file_path) as f:
            file.raw_text = f.read() # Raw text that the file contains

        file.tokens = Tokenizer(file.file_path, file.raw_text).tokenize()

        return file


class Command:
    def __init__(self, name:str, args:list, kwargs, content_tokens:list):
        self._name = name
        self._args = args
        self._kwargs = kwargs
        self._content_tokens = content_tokens

    def run(self, *args, **kwargs):
        pass

import argparse


def run(start_file_path, out_file_path):
    try:
        c = Compiler(start_file_path, out_file_path)
        c.compile_pdf()
    except Error as e:
        print('\nFATAL ERROR')
        print('A fatal error occured while compiling your PDF. Your PDF was not fully compiled.')
        print(e.as_string())



def main():
    p = argparse.ArgumentParser(description='A program that compiles pdfs from ' \
            'plain-text files.')
    p.add_argument('in_file_path', type=str,
            help='The path to the main file that you are compiling from.')
    p.add_argument('-o', '--out_file_path', type=str,
            help='The path to the output file you want. Without this, the output file is just the input file path with the ending changed to .pdf')
    #p.add_argument('-f', '--verbosity', type=int,
            #help='The level of logging you want.')
    #p.add_argument('--continous', action="store_true"
            #help='Continuouly compile file every time it is resaved.')
    args = p.parse_args()

    if args.out_file_path:
        run(args.in_file_path, args.out_file_path)
    else:
        out_file_path = args.in_file_path.split('\\.')

        if len(out_file_path) > 0:
            out_file_path[-1] = 'pdf'
        else:
            out_file_path.append('pdf')

        out_file_path = '.'.join(out_file_path)

        run(args.in_file_path, out_file_path)


if __name__ == "__main__":
    main()
