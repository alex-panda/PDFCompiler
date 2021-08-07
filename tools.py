from decimal import Decimal
from constants import WHITE_SPACE_CHARS

def assure_decimal(val):
    return Decimal(val)

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


def is_escaping(pos:int, text:str, chars_that_can_be_escaped:list):

    # If it is escaping something else then it too is escaped
    if text[pos] == '\\' and pos + 1 < len(text) and text[pos + 1] in chars_that_can_be_escaped:
        return True
    return False

def trimmed(string):
    """
    Returns a version of the given string with the white space on either side
        of it trimmed off.
    """
    if string == '':
        return string

    first_index = None
    last_index = None

    for i, ch in enumerate(string):

        if ch in WHITE_SPACE_CHARS:
            continue

        first_index = i
        break

    for i, ch in enumerate(reversed(string)):

        if ch in WHITE_SPACE_CHARS:
            continue

        last_index = len(string) - i
        break

    if first_index is None or last_index is None:
        return ''
    else:
        return string[first_index:last_index]


def exec_python(code, exec_globals:dict, exec_locals:dict=None):
    """
    Executes python code and returns the value stored in 'ret' if it was
        specified as a global variable.
    """
    if exec_locals is None:
        exec_locals = {}

    try:
        exec(code, exec_globals, exec_locals)
    except Exception as e:
        return e

    if 'ret' in exec_globals:
        return str(exec_globals.pop('ret'))
    else:
        return None


def eval_python(code:str, eval_globals:dict, eval_locals:dict=None):
    """
    Avaluates Python and returns a string of the output.
    """
    if eval_locals is None:
        eval_locals = {}

    try:
        res = eval(code, eval_globals, eval_locals)
    except Exception as e:
        return e

    return str(res)


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
