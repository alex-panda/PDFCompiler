import copy
import os

from constants import TT, CMND_CHARS, TT_M

# -----------------------------------------------------------------------------
# Helper Global Functions

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

class IllegalCmndNameError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Command Name', details)

class PythonError(Error):
    def __init__(self, pos_start, pos_end, details, python_error):
        self._python_error = python_error
        super().__init__(pos_start, pos_end, 'Python Code Produced An Exception', details)

    def as_string(self):
        string = super().as_string()

        string += '\nHere is the Python Error:\n\n'
        string += f'{self.python_error}'

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
    def __init__(self, idx, ln, col, file_path, file_text):
        self.idx = idx
        self.ln = ln
        self.col = col
        self.file_path = file_path # The path tot he file that this is a position in
        self.file_text = file_text # The text of the file this is a position in

    def advance(self, current_char):
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
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def add_char(self, char):
        self.value.append(char)

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
        tokens = []
        self._plain_text = ''
        what_can_be_escaped = {'{', '}', '=', '\\'}

        tokens.append(Token(TT.FILE_START, '<FILE START>'))

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
            elif cc == '{':
                t = Token(TT.OCBRACE, '{')
                self._advance()
            elif cc == '}':
                t = Token(TT.CCBRACE, '}')
                self._advance()
            elif cc == '=':
                t = Token(TT.EQUAL_SIGN, '=')
                self._advance()
            elif cc == '\\':
                t = self._parse_cntrl_seq()
            else:
                self._plain_text_char()

            # Actually append the token
            if t is not None:
                if len(self._plain_text) > 0:
                    tokens.append(Token(TT.PLAIN_TEXT, self._plain_text))
                    self._plain_text = ''

                if isinstance(t, Token):
                    tokens.append(t)
                else:
                    # t must be a list of tokens
                    tokens.extend(t)

        if len(self._plain_text) > 0:
            tokens.append(Token(TT.PLAIN_TEXT, self._plain_text))

        tokens.append(Token(TT.FILE_END, '<FILE END>'))

        return tokens

    # -------------------------------------------------------------------------
    # Parsing Methods

    def _parse_cntrl_seq(self):
        """
        Parse a control sequence.
        """
        t = None

        # First Pass Python -----------------------
        if self._matches(TT_M.ONE_LINE_PYTH_1PASS_EXEC_START):
            # The rest of the line (or until '<\\', '<1\\', '\n', '\r\n') is python for first pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_1PASS_EXEC_END, 1)

        elif self._matches(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_START):
            # All of it is python for first pass until '<-\\' or '<-1\\'
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_1PASS_EXEC_END, 1)

        elif self._matches(TT_M.ONE_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_1PASS_EVAL_END, 2, use_eval=True)

        elif self._matches(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_1PASS_EVAL_END, 2, use_eval=True)

        # Second Pass Python ----------------------
        elif self._matches(TT_M.ONE_LINE_PYTH_2PASS_EXEC_START):
            # The rest of the line (or until '<2\\') is python for second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_2PASS_EXEC_END, 2)

        elif self._matches(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_START):
            # All of it is python for first pass until '<-2\\'
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_2PASS_EXEC_END, 2)

        elif self._matches(TT_M.ONE_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.ONE_LINE_PYTH_2PASS_EVAL_END, 2, use_eval=True)

        elif self._matches(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_START):
            # The rest of the line (or until '<?\\') is python for eval expression in second pass
            t = self._parse_python(TT_M.MULTI_LINE_PYTH_2PASS_EVAL_END, 2, use_eval=True)

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

        tokens.append(Token(TT.BACKSLASH, '\\'))
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
                    raise IllegalCmndNameError(problem_start, self._pos.copy(),
                            f'All commands must specify a valid name with all characters of it in {CMND_CHARS} "{self._text[curr_idx]}" is not one of them. You either forgot to designate a valid command name or forgot to escape the backslash before this character.')

                tokens.append(Token(TT.CMND_NAME, cmnd_name))

                return tokens

    def _parse_python(self, end_codes, pass_num, use_eval=False):
        """
        Parses the string from self._pos as python code until one of the end_codes
            are reached.
        """
        python_str = ''

        while self._current_char is not None:
            if self._matches(end_codes):
                # since found a match, self._matches will advance past the
                #   match it made
                break
            else:
                # Since python has not ended yet, just add the given char to it
                python_str += self._current_char
                self._advance()

        if pass_num == 1:
            if use_eval:
                return Token(TT.EVAL_PYTH1, python_str)
            else:
                return Token(TT.EXEC_PYTH1, python_str)
        else:
            if use_eval:
                return Token(TT.EVAL_PYTH2, python_str)
            else:
                return Token(TT.EXEC_PYTH2, python_str)

    # -------------------------------------------------------------------------
    # Other Helper Methods

    def _plain_text_char(self):
        """
        The current char is a plain_text character
        """
        self._plain_text += self._current_char
        self._advance()

    def _matches(self, matches:list, advance_past_on_match=True):
        """
        Sees if the text from the current position forward matches the given string.
        """
        for str_to_match in matches:
            if ((self._pos.idx + len(str_to_match)) < len(self._text)) \
                    and (str_to_match == self._text[self._pos.idx:self._pos.idx + len(str_to_match)]):

                if advance_past_on_match:
                    self._advance(len(str_to_match))

                return True
        return False

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
                '__builtins__': copy.deepcopy(globals()['__builtins__'].__dict__)}

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
