from decimal import Decimal
from constants import WHITE_SPACE_CHARS, OUT_TAB
from constants import PB_SUFFIX, PB_NUM_DECS, PB_LEN, PB_UNFILL, PB_FILL, PB_NUM_TABS, PB_NAME_SPACE, PB_PREFIX_SPACE
import os

def assure_decimal(val):
    return Decimal(val)

def calc_prog_bar_refresh_rate(total):
    """
    Calculate how often the progress bar should refresh (will do % refresh_rate
        to figure out whether to print_progress_bar). Basically, printing to
        the screen is very costly as far as time is concerned so this method
        calculates the minimum interval of updating the progress bar that will
        actually make a distance (a number in the percentage decimal number
        changed)

    total is the total number that the progress bar is iterating to.
    """
    # Number of times each decimal needs to be updaated
    dec_refresh = (10 ** PB_NUM_DECS)

    # The 100 is how how often the 100 part of the 100.00% needs to be updated
    rate = total // (100 * (1 if dec_refresh <= 0 else dec_refresh))

    # The + 1 is so that it will never be 0, because number % 0 raises an error
    return rate + 1

def prog_bar_prefix(prefix, file_path, align='^', suffix=':'):
    """
    Create the correct prefix for each progress bar.
    """
    file_path = file_path.split('\\')[-1].split('/')[-1]
    file_path = file_path if len(file_path) <= PB_NAME_SPACE else file_path[-PB_NAME_SPACE:]
    prefix = ('{' + (f':>{PB_PREFIX_SPACE}') + '}').format(prefix)
    new_prefix = (OUT_TAB * PB_NUM_TABS) + prefix
    new_prefix += (' {' + (f':{align}{PB_NAME_SPACE}') + '}').format(file_path) + suffix
    return new_prefix

# Print iterations progress
def print_progress_bar (iteration, total, prefix='', suffix=PB_SUFFIX, decimals=PB_NUM_DECS, length=PB_LEN, unfill=PB_UNFILL, fill=PB_FILL):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        unfil       - Optional  : bar not-filled character (Str)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{:." + str(decimals) + "f}").format(100 * (iteration / float(total)))

    num_cols = os.get_terminal_size().columns
    full_len = len(prefix) + length + len(percent) + len(suffix) + len(" || % ") + 1

    draw_bar = True
    if num_cols < full_len:
        length -= full_len - num_cols

        if length <= 0:
            draw_bar = False

            length = (-length) - 3
            pref_len = len(prefix)
            if length < pref_len:
                prefix = prefix[length - pref_len:]
            else:
                prefix = ''

    elif num_cols > full_len:
        spaces_to_fill = (num_cols - full_len)
        suffix += ' ' * (4 if spaces_to_fill >= 4 else spaces_to_fill)

    if draw_bar:
        filledLength = length * iteration // total
        bar = ' |' + fill * filledLength + unfill * (length - filledLength) + '| '
    else:
        bar = ' '

    if iteration < total:
        print(f'\r{prefix}{bar}{percent}% {suffix}', end='')
    else:
        print(f'\r{prefix}{bar}{percent}% {suffix}', end='\n')

def assert_instance(obj, types, var_name=None, or_none=True):
    if not (isinstance(obj, types) or (or_none and obj is None)):
        if var_name is None:
            var_name = 'This'
        string = f'{var_name} is supposed to be one of these types: {types}'

        if or_none:
            string += ' or None'

        string += f'\nbut it was {obj}'
        raise AssertionError(string)


def assert_subclass(obj, types, var_name=None, or_none=True):
    obj = type(obj)
    if not issubclass(obj, types) or (or_none and obj is None):
        if var_name is None:
            var_name = 'This'
        string = f'{var_name} is supposed to be a subclass of {types}'

        if or_none:
            string += ' or None'

        string += f'\nbut it was {obj}'
        raise AssertionError(string)


def draw_str(canvas_obj, point_obj, string:str):
    """
    Draws a string at the given Point on the given canvas.
    """
    #print(f'{point_obj}, {string}')
    canvas_obj.drawString(float(point_obj.x()), float(point_obj.y()), string)


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
    try:
        exec(code, exec_globals, exec_locals)
    except Exception as e:
        import traceback
        e.exc_trace = traceback.format_exc()
        return e

    if 'ret' in exec_globals:
        return str(exec_globals.pop('ret'))
    else:
        return None


def eval_python(code:str, eval_globals:dict, eval_locals:dict=None):
    """
    Avaluates Python and returns a string of the output.
    """
    try:
        res = eval(code, eval_globals, eval_locals)
    except Exception as e:
        import traceback
        e.exc_trace = traceback.format_exc()
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
