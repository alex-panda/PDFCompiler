"""
This is the main file that holds the Tokenizer, Parser, and Interpreter
    that actually compile the PDF.
"""
import os
import re
import copy as _copy
from decimal import Decimal

from reportlab.lib.units import inch, cm, mm, pica, toLength
from reportlab.lib import units, colors, pagesizes as pagesizes

from constants import CMND_CHARS, END_LINE_CHARS, ALIGN, TT, TT_M, WHITE_SPACE, NON_END_LINE_WHITE_SPACE
from tools import assure_decimal, is_escaped, is_escaping, exec_python, eval_python, string_with_arrows
from placer import Placer

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

class RunTimeError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, 'Run-Time Error', details)
        self.context = context

    def as_string(self):
        return Error.as_string(self)

    def generate_traceback(self):
        result = ''
        pos = self.pos_start
        ctx = self.context

        while ctx is not None:
            result = f'  File {pos.file_path}, line {str(pos.ln + 1)}, in {ctx.display_name}\n' + result
            pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return 'Traceback (most recent call last):\n' + result

class PythonException(RunTimeError):
    def __init__(self, pos_start, pos_end, details, python_error, context):
        self.python_error = python_error
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

        if current_char == '\n':
            self.ln += 1
            self.col = 0

        return self

    def copy(self):
        return Position(self.idx, self.ln, self.col, self.file_path, self.file_text)

# -----------------------------------------------------------------------------
# File Class

class File:
    __slots__ = ['file_path', 'raw_text', 'tokens', 'ast']
    def __init__(self, file_path):
        self.file_path = file_path # Path to file
        self.raw_text = None
        self.tokens = None # The tokens that make up the File once it has been tokenized
        self.ast = None

# -----------------------------------------------------------------------------
# Token Class

class Token:
    __slots__ = ['start_pos', 'end_pos', 'type', 'value']
    def __init__(self, type, value, start_pos, end_pos=None):
        self.start_pos = start_pos

        if end_pos is None:
            end_pos = self.start_pos.copy()
            end_pos.advance() # Necessary if you want errors to display the errors correctly because they use start_pos - end_pos
            self.end_pos = end_pos
        else:
            self.end_pos = end_pos

        self.type = type
        self.value = value

        if type == TT.WORD and value == '':
            raise Exception(f'An empty string has been made into a Token. This is a compiler problem. {self}')

    def matches(self, token_type, value):
        """
        Checks if the given token_type and value matches this one.
        """
        return self.type == token_type and self.value == value

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

    @staticmethod
    def plaintext_tokens_for_str(string):
        """
        If you want to write plaintext to the placer and the string to be
            interpreted only as plaintext, then this is what you use to
            tokenize the string. Just take the return-ed string from this
            method and give it to the place_text method of the Placer.
        """
        tokens = []
        idx = -1
        cc = None

        def next_tok(idx):
            idx += 1
            return string[idx] if idx < len(string) else None, idx

        def try_append_word(curr_word):
            curr_word = re.sub('(\s)+', '', curr_word)
            if len(curr_word) > 0:
                tokens.append(Token(TT.WORD, curr_word, DUMMY_POSITION.copy()))

        cc, idx = next_tok(idx)

        # Eat all end line chars at beginning so no paragraph break at beginning
        while (cc is not None) and (cc in END_LINE_CHARS):
            cc, idx, = next_tok(idx)

        curr_word = ''
        while cc is not None:
            if cc in NON_END_LINE_WHITE_SPACE:
                cc, idx = next_tok(idx)

                try_append_word(curr_word)
                curr_word = ''

                while (cc is not None) and (cc in NON_END_LINE_WHITE_SPACE):
                    cc, idx, = next_tok(idx)

                continue

            elif cc in END_LINE_CHARS:
                cc, idx = next_tok(idx)

                try_append_word(curr_word)
                curr_word = ''

                if cc in END_LINE_CHARS:
                    tokens.append(Token(TT.PARAGRAPH_BREAK, TT.PARAGRAPH_BREAK, DUMMY_POSITION.copy()))
                    cc, idx = next_tok(idx)

                    while (cc is not None) and (cc in END_LINE_CHARS):
                        cc, idx, = next_tok(idx)

                continue
            else:
                curr_word += cc
                cc, idx = next_tok(idx)

        try_append_word(curr_word)

        return tokens

    def tokenize(self):
        """
        Turn the raw text into tokens that the compiler can use.
        """
        self._tokens = []
        self._plain_text = ''
        what_can_be_escaped = {'{', '}', '=', '\\'}

        self._tokens.append(Token(TT.FILE_START, '<FILE START>', self._pos.copy()))

        # By default, all text is plain text until something says otherwise
        while self._current_char is not None:
            cc = self._current_char

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
                self._try_word_token()

                if self._match(END_LINE_CHARS):

                    while self._match(END_LINE_CHARS):
                        # self._match will automatically keep advancing past the '\n' and '\r\n' it finds
                        pass # Do nothing, just eat the END_LINE_CHARS now that we know that there is a PARAGRAPH_BREAK

                    t = Token(TT.PARAGRAPH_BREAK, None, pos_start, self._pos.copy())
            elif cc in NON_END_LINE_WHITE_SPACE:
                self._try_word_token()
                self._advance()
            elif cc == '{':
                t = Token(TT.OCBRACE, '{', self._pos.copy())
                self._advance()
            elif cc == '}':
                t = Token(TT.CCBRACE, '}', self._pos.copy())
                self._advance()
            elif cc == '=':
                t = Token(TT.EQUAL_SIGN, '=', self._pos.copy())
                self._advance()
            elif cc == '\\':
                t = self._tokenize_cntrl_seq()
            else:
                self._plain_text_char()

            # Actually append the token
            if t is not None:

                self._try_word_token()

                if isinstance(t, Token):
                    self._tokens.append(t)
                else:
                    # t must be a list of tokens
                    self._tokens.extend(t)

        self._try_word_token()

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
        #   single-line matches because shorter methods will match before longer
        #   matches, even if the longer match would have worked had it been tried

        # Multi-line Python
        if self._match(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_START):
            # All of it is python for first pass until '<-\\' or '<-1\\'
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_END, 1, pos_start)

        elif self._match(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_END, 2, pos_start, use_eval=True)

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_START):
            # All of it is python for first pass until '<-2\\'
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_END, 2, pos_start)

        elif self._match(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._tokenize_python(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, use_eval=True)

        # Multi-line Python ----------------------
        elif self._match(TT_M.ONE_LINE_PYTH_1PASS_EXEC_START):
            # The rest of the line (or until '<\\', '<1\\', '\n', '\r\n') is python for first pass
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_1PASS_EXEC_END, 1, pos_start, one_line=True)

        elif self._match(TT_M.ONE_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_1PASS_EVAL_END, 2, pos_start, one_line=True, use_eval=True)

        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EXEC_START):
            # The rest of the line (or until '<2\\') is python for second pass
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_2PASS_EXEC_END, 2, pos_start, one_line=True)

        elif self._match(TT_M.ONE_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._tokenize_python(TT_M.ONE_LINE_PYTH_2PASS_EVAL_END, 2, pos_start, one_line=True, use_eval=True)

        # Comment ----------------------
        elif self._match(TT_M.MULTI_LINE_COMMENT_START):
            t = self._tokenize_comment(pos_start, one_line=False)

        elif self._match(TT_M.SINGLE_LINE_COMMENT_START):
            t = self._tokenize_comment(pos_start, one_line=True)

        # Command --------------------------
        else:
            # It is a command, so parse it
            t = self._tokenize_command()

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
                return Token(TT.PASS1EVAL, python_str, pos_start, pos_end)
            else:
                return Token(TT.PASS1EXEC, python_str, pos_start, pos_end)
        else:
            if use_eval:
                return Token(TT.PASS2EVAL, python_str, pos_start, pos_end)
            else:
                return Token(TT.PASS2EXEC, python_str, pos_start, pos_end)

    def _tokenize_comment(self, pos_start, one_line=False):
        """
        Parses a comment, basically just eating any characters it finds until
            the comment is done.
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

    def _tokenize_command(self):
        """
        Parse a command.
        """
        cmnd_name = ''
        tokens = []

        start_pos = self._pos.copy()

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

    # -------------------------------------------------------------------------
    # Other Helper Methods

    def _try_word_token(self):
        """
        Create a WORD token given what is in self._plain_text
        """
        self._plain_text = re.sub('(\s)+', '', self._plain_text)

        if len(self._plain_text) > 0:
            self._tokens.append(Token(TT.WORD, self._plain_text, self._plain_text_start_pos, self._pos.copy()))
            self._plain_text = ''
            self._plain_text_start_pos = None

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
    __slots__ = ['start_pos', 'end_pos', 'paragraph_break', 'paragraphs']
    def __init__(self, paragraph_break, paragraphs):
        self.paragraph_break = paragraph_break # Token
        self.paragraphs = paragraphs # List of ParagraphNodes

        if paragraph_break:
            self.start_pos = paragraph_break.start_pos
        elif len(paragraphs) > 0:
            self.start_pos = paragraphs[0].start_pos
        else:
            self.start_pos = DUMMY_POSITION.copy()

        if len(paragraphs) > 0:
            self.end_pos = paragraphs[0].end_pos
        elif paragraph_break:
            self.end_pos = paragraph_break.end_pos
        else:
            self.end_pos = DUMMY_POSITION.copy()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.paragraph_break}, {self.paragraphs})'

class ParagraphNode:
    __slots__ = ['start_pos', 'end_pos', 'writing', 'paragraph_break']
    def __init__(self, writing, paragraph_break):
        self.writing = writing # WritingNode
        self.paragraph_break = paragraph_break # Token

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
    __slots__ = ['error', 'node', 'last_registered_advance_count', 'advance_count', 'to_reverse_count']
    def __init__(self):
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self):
        """
        Registers that the Parser advanced a token so that that advancement
            can be undone later if need be.
        """
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, res):
        """
        Registers a result, returning the error if there was one or
            returning the node if the result wis successful.
        """
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        if res.error:
            self.error = res.error
        return res.node

    def register_try(self, res):
        """
        Returns None if the given result did not work and the Node of
            the result if it did.
        """
        if res.error:
            self.to_reverse_count = res.advance_count
            return None
        return self.register(res)

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
    def __init__(self, tokens):
        self._tokens = tokens
        self._tok_idx = -1
        self._current_tok = None
        self._advance()

    def parse(self):
        """
        Returns a ParseResult with either an error in res.error or a node in
            res.node
        """
        if self._current_tok.type == TT.FILE_START:
            res = self._file()
        else:
            res = self._document()
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

    def _reverse(self, amount=1):
        self._tok_idx -= amount
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
            return res.failure(InvalidSyntaxError(start_pos, start_pos.copy().advance(),
                f'Reached the end of the file but there was no FILE_END Token. The file must have Invalid Syntax or the compiler is having issues.\n\nALL TOKENS: {self._tokens}\n\nLAST TOKEN SEEN: {self._current_tok}'))

        return res.success(FileNode(file_start, document, file_end))

    def _document(self):
        res = ParseResult()
        paragraphs = []

        paragraph_break = self._paragraph_break(res)

        while True:
            # pargraph will be None if the try failed, otherwise it will be the
            #   new ParagraphNode
            paragraph = res.register_try(self._paragraph())

            # If, when we tried to make another paragraph, it failed,
            #   that means that there are no more paragraphs left in the
            #   document, so undo the try by going back the number of
            #   tokens that the try went forward
            if paragraph is None:
                self._reverse(res.to_reverse_count)
                break
            else:
                paragraphs.append(paragraph)

        return res.success(DocumentNode(paragraph_break, paragraphs))

    def _paragraph(self):
        res = ParseResult()

        start_pos = self._current_tok.start_pos.copy()

        # Check for Writing
        writing = res.register_try(self._writing())

        if writing is None:
            self._reverse(res.to_reverse_count)
            return res.failure(
                        InvalidSyntaxError(start_pos, self._current_tok.end_pos.copy(),
                            f'A Paragraph must have writing in it. This is not a Paragraph.')
                    )

        # Check for Paragraph Break
        paragraph_break = self._paragraph_break(res)

        # writing should be a WritingNode and paragraph_break is a Token of
        #   type PARAGRAPH_BREAK
        return res.success(ParagraphNode(writing, paragraph_break))

    def _writing(self):
        res = ParseResult()

        start_pos = self._current_tok.start_pos.copy()

        writing = res.register_try(self._python())

        if writing is None:
            self._reverse(res.to_reverse_count)

            writing = res.register_try(self._plain_text())

            if writing is None:
                self._reverse(res.to_reverse_count)

                return res.failure(InvalidSyntaxError(start_pos, self._current_tok.end_pos.copy(),
                            f'Expected Python or PlainText here, but got neither.')
                        )

        # writing should be either a PythonNode or a PlainTextNode
        return res.success(WritingNode(writing))

    def _python(self):
        res = ParseResult()

        cc = self._current_tok
        type = self._current_tok.type

        # Python Switch Statement
        try:
            python = {
                TT.PASS1EXEC: cc,
                TT.PASS1EVAL: cc,
                TT.PASS2EXEC: cc,
                TT.PASS2EVAL: cc
            }[cc.type]
        except KeyError:
            return res.failure(InvalidSyntaxError(cc.start_pos.copy(), cc.start_pos.copy().advance(),
                    'Expected a Token of Type PASS1EXEC, PASS1EVAL, PASS2EXEC, or PASS1EVAL but did not get one.')
                )

        self._advance(res)

        # python should be a single python Token of type PASS1EXEC or PASS2EXEC
        #   or PASS1EVAL or PASS2EVAL
        return res.success(PythonNode(python))

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
                    TT.OCBRACE: cc,
                    TT.CCBRACE: cc,
                    TT.EQUAL_SIGN: cc,
                    TT.WORD: cc
                }[cc.type]

                # If I remember correctly, you cannot directly wrap the dict
                #   in this append method because it appends the error
                #   to the list when there is an error, which is problematic
                plain_text.append(new_tok)
            except KeyError:
                break

            self._advance(res)

        if len(plain_text) == 0:
            return res.failure(InvalidSyntaxError(start_pos.copy(), start_pos.advance().copy(),
                        'Expected atleast 1 WORD, BACKSLASH, OCBRACE, CCBRACE, or EQUAL_SIGN Token.'
                    )
                )

        # plain_text is a list of OCBRACE, CCBRACE, EQUAL_SIGN, and WORD Tokens
        #   in any order.
        return res.success(PlainTextNode(plain_text))

    # -------------------------------------------------------------------------
    # Non-Rule Lesser Help Methods

    def _paragraph_break(self, parse_result):
        """
        A helper method that, unlike the other methods, just exists because
            there are multiple rules with PARAGRAPH_BREAK? in them. This
            method does that, returning None if the current token is not
            a PARAGRAPH_BREAK and the PARAGRAPH_BREAK Token if there is one.
            If a PARAGRAPH_BREAK token is found, the method also advances past
            past it.
        """
        par_break = None
        if self._current_tok.type == TT.PARAGRAPH_BREAK:
            par_break = self._advance(parse_result)

        return par_break

# -----------------------------------------------------------------------------
# Interpreter and Related Classes

class Context:
    """
    Provides Context for every command/amount of python code that is run. By
        that I mean that the Context determines what commands and variables are
        available and when.
    """
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        """
        Context could be a function if in a function or the entire program
            (global) if not in a function.
        """
        self.display_name = display_name # the function/program name
        self.parent = parent # Parent context if there is one
        self.parent_entry_pos = parent_entry_pos # the position in the code where the context changed (where was the function called)

        self.commands_symbol_table = None
        self.python_symbol_table = None

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def get(self, name):
        value = self.symbols.get(name, None)
        if value == None and self.parent:
          return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbols[name] = value

    def remove(self, name):
        del self.symbols[name]

class RunTimeResult:
    """
    Wraps a return value in the Interpreter so that, when a visit method
        finishes visiting a Node, it can tell the Node that visited it various
        things such as whether to return immediately or not.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = None
        self.error = None
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False

    def register(self, res):
        """
        Register the returned result from a Node you just visited. This way,
            if you should return because an error occured or something, you can.
        """
        self.error = res.error
        self.func_return_value = res.func_return_value
        self.loop_should_continue = res.loop_should_continue
        self.loop_should_break = res.loop_should_break
        return res.value

    def success(self, value):
        self.reset()
        self.value = value
        return self

    def success_return(self, value):
        self.reset()
        self.func_return_value = value
        return self

    def success_continue(self):
        self.reset()
        self.loop_should_continue = True
        return self

    def success_break(self):
        self.reset()
        self.loop_should_break = True
        return self

    def failure(self, error):
        self.reset()
        self.error = error
        return self

    def contains_error(self):
        return (self.error is not None)

    def should_return(self):
        # Note: this will allow you to continue and break outside the current function
        return (
          self.error or
          self.func_return_value or
          self.loop_should_continue or
          self.loop_should_break
        )

class InterpreterFlags:
    """
    Flags for the Interpreter so that it can know what to do when an AST is
        passed to it.
    """
    def __init__(self, pass_num=1, placer=None, file=None):
        self.pass_num = pass_num # what pass this is in the compile
        self.placer = placer # will be None if no text is supposed to be placed on a PDF


class Interpreter:
    """
    The interpreter visits each node in the Abstract Syntax Tree generated
        by the Parser and actually runs the corresponding code for the
        node.

    What is returned by each visit is what the visited node wants the parent
        node to set as its node.
    """
    def __init__(self, compiler):
        self._compiler = compiler

    def visit(self, node, context):
        method_name = f'_visit_{type(node).__name__}'
        method = getattr(self, method_name, self._no_visit_method)
        return method(node, context)

    def _no_visit_method(self, node, context):
        raise Exception(f'No _visit_{type(node).__name__} method defined in Interpreter')

    # ------------------------------
    # Rule Implementations

    def _visit_FileNode(self, node, context):
        res = RunTimeResult()
        result = res.register(self.visit(node.document, context))

        if res.contains_error():
            return res

        return res.success(result)

    def _visit_DocumentNode(self, node, context):
        res = RunTimeResult()

        for paragraph in node.paragraphs:
            res.register(self.visit(paragraph, context))

            if res.contains_error():
                return res

        return res

    def _visit_ParagraphNode(self, node, context):
        res = RunTimeResult()

        # Visit the writing (could be Plaintext, Python, or a Command call)
        written_str = res.register(self.visit(node.writing, context))

        if res.contains_error():
            return res

        # No new line if the writing node did not produce any new plaintext
        if written_str == '':
            return res.success(written_str)

        if self._compiler._pass_num == 2 and node.paragraph_break is not None:
            self._compiler._placer.new_paragraph()

        return res.success(written_str)

    def _visit_WritingNode(self, node, context):
        res = RunTimeResult()
        written_str = res.register(self.visit(node.writing, context))
        if res.contains_error(): return res
        return res.success(written_str)

    def _visit_PythonNode(self, node, context):
        res = RunTimeResult()
        python_token = node.python
        tt = python_token.type

        python_result = 0

        # Execute or eval python so that anything in it can be placed on
        #   the PDF when this node is visited the 2nd time.
        if tt == TT.PASS1EXEC:
            python_result = exec_python(python_token.value, self._compiler._globals)
        elif tt == TT.PASS1EVAL:
            python_result = eval_python(python_token.value, self._compiler._globals)

        # Execute or eval python and have it placed on the PDF now
        elif tt == TT.PASS2EXEC:
            if self._compiler._pass_num == 2:
                python_result = exec_python(python_token.value, self._compiler._globals)
        elif tt == TT.PASS2EVAL:
            if self._compiler._pass_num == 2:
                python_result = eval_python(python_token.value, self._compiler._globals)
        else:
            raise Exception(f"The following token was found in a PythonNode, it is not supposed to be in a PythonNode: {python}")


        # exec_python and eval_python functions only return either a string
        #   or None. None if nothing was returned by the exec_function,
        #   otherwise a string version of what was returned. Thus, if one of the
        #   functions was run, then python_result will be not be 0
        if python_result != 0:
            node.python_string = python_result

        if isinstance(python_result, Exception) or issubclass(type(python_result), Exception):
            return res.failure(PythonException(node.start_pos.copy(), node.end_pos.copy(), 'An error occured while running your Python code.', python_result, context))

        elif node.python_string is not None and self._compiler._pass_num == 2:
            plaintext_tokens = Tokenizer.plaintext_tokens_for_str(node.python_string)

            if len(plaintext_tokens) > 0:
                self._compiler._placer.place_text(plaintext_tokens)

            return res.success(node.python_string)

        return res

    def _visit_PlainTextNode(self, node, context):
        res = RunTimeResult()

        if self._compiler._pass_num == 2:
            self._compiler._placer.place_text(node.plain_text)
            res.success(node.plain_text)

        return res


# -----------------------------------------------------------------------------
# Compiler Class

class Compiler:
    def __init__(self, file_path_to_start_file, output_file_path):
        self._start_file = file_path_to_start_file
        self._commands = {}
        self._files_by_path = {}

        self._pass_num = 1 # Will be 2 when the compiler is making its second pass
        self._interpreter = Interpreter(self)
        self._placer = Placer()
        self._init_globals()
        self._init_commands()

    def _init_globals(self):
        self._globals = {'__name__': __name__, '__doc__': None, '__package__': None,
                '__loader__': __loader__, '__spec__': None, '__annotations__': {},
                '__builtins__': _copy.deepcopy(globals()['__builtins__'].__dict__)}

        # Now remove any problematic builtins from the globals
        rem_builtins = []
        [self._globals['__builtins__'].pop(key) for key in rem_builtins]

    def _init_commands(self):
        self.add_command("def", "\>c.add_command(cmnd_name, code_to_run, args, kwargs)",
                args=('cmnd_name', 'code_to_run'), kwargs={'cmnd_args':None, 'cmnd_kwargs':None})

    # -------------------------------------------------------------------------
    # Main Methods

    def compile_pdf(self):
        """
        Compiles the PDF starting at self._start_file
        """
        file = self._import_file(self._start_file)
        result = self._interpreter.visit(file.ast, Context(file.file_path))

        if result.contains_error():
            raise result.error

        self._pass_num = 2
        result = self._interpreter.visit(file.ast, Context(file.file_path))

        if result.contains_error():
            raise result.error

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
        """
        Imports a file, tokenizing it and determining its Abstract Syntax
            Tree (AST) before returning it. To run the file, the AST
            must be run by the Interpreter.
        """
        file_path = os.path.abspath(file_path)

        if file_path in self._files_by_path:
            return self._files_by_path[file_path]

        file = File(file_path)
        self._files_by_path[file_path] = file

        with open(file_path) as f:
            file.raw_text = f.read() # Raw text that the file contains

        file.tokens = Tokenizer(file.file_path, file.raw_text).tokenize()
        #print(file.tokens)
        file.ast = Parser(file.tokens).parse()

        if file.ast.error is not None:
            raise file.ast.error
        else:
            file.ast = file.ast.node

        return file

    def _ast_for_text(self, text:str, file_name='TextFile'):
        """
        Tokenizes and creates an AST for a given string, returning the root
            node of the AST.
        """
        tokens = Tokenizer(file_name, text).tokenize()
        ast = Parser(tokens).parse()

        return ast

class Command:
    """
    Represents a command in the file.
    """
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
        print('A fatal error occured while compiling your PDF. Your PDF was not completely compiled.\n')
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
