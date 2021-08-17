from compiler import Compiler, Error
from constants import OUT_TAB, STD_DIR
import os

def main(input_file_path, output_file_path=None, print_progress_bars=False):
    """
    Takes a file path to the input plaintext file and a file path to the output
        file.

    Returns the error if the file was not successfully compiled and a string containing
         the file path to the new file otherwise.
    """

    input_file_path = os.path.abspath(input_file_path)

    if output_file_path is None:
        output_file_path = input_file_path.split('.')

        if len(output_file_path) > 1:
            output_file_path[-1] = 'pdf'
        else:
            output_file_path.append('pdf')

        output_file_path = '.'.join(output_file_path)

    try:
        c = Compiler(input_file_path, os.path.abspath(STD_DIR), print_progress_bars)
        c.compile_and_draw_pdf(output_file_path)
    except Error as e:
        return e
    return output_file_path


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description='A program that compiles pdfs from plain-text files.')
    p.add_argument('input_file_path', type=str,
            help='The path to the main file that you are compiling from.')
    p.add_argument('-o', '--output_file_path', type=str, nargs='?', const=None,
            help='The path to the output file you want. Without this, the output file is just the input file path with the ending changed to .pdf')
    #p.add_argument('-f', '--verbosity', type=int,
            #help='The level of logging you want.')
    #p.add_argument('-c', '--continous', action="store_true",
            #help='Continuouly compile the file every time it is resaved.')
    p.add_argument('-np', '--no_progress', action="store_true",
            help='Gets rid of the progress bars that are normally shown whenever you compile the PDF.')
    args = p.parse_args()

    input_file_path = os.path.abspath(os.path.expandvars(os.path.expanduser(args.input_file_path)))

    if not os.path.exists(input_file_path):
        raise AssertionError(f'The given path does not exist: {input_file_path}')

    if not os.path.isfile(input_file_path):
        raise AssertionError(f'The given path is not a path to a file that exists: {input_file_path}')

    from time import time

    start_time = time()

    print(f'\nCompiling file at\n{OUT_TAB}{input_file_path}')

    if args.no_progress:
        print(f'{OUT_TAB}.\n{OUT_TAB}.\n{OUT_TAB}.')

    res = main(args.input_file_path, args.output_file_path, not args.no_progress)

    if not isinstance(res, str):
        print('\n\nAn Error Occured\n', end='')
        print(f'{OUT_TAB}A fatal error occured while compiling your PDF. Your PDF was not compiled fully.\n\n', end='')
        print(res.as_string())

    else:
        print(f'\n{OUT_TAB}File Compiled Successfully! Compiled File created at:\n{OUT_TAB}{OUT_TAB}{res}')

        end_time = time()

        from tools import time_to_str
        print(f'{OUT_TAB}{OUT_TAB}The full compilation took {time_to_str(end_time - start_time).lower()}.')

