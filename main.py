from compiler import Compiler, Error
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
        c = Compiler(input_file_path, print_progress_bars)
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
    #p.add_argument('--continous', action="store_true"
            #help='Continuouly compile file every time it is resaved.')
    p.add_argument('-np', '--no_progress', action="store_false",
            help='Gets rid of the progress bars that are normally shown whenever you compile the PDF.')
    args = p.parse_args()

    #print('Beginning File Compilition!')

    input_file_path = os.path.abspath(args.input_file_path)

    from time import time
    start_time = time()

    print(f'\nCompiling file at\n\t{input_file_path}', end='')

    if args.no_progress:
        print('\n\t.\n\t.\n\t.')
    else:
        print('\n', end='')

    res = main(args.input_file_path, args.output_file_path, not args.no_progress)

    if not isinstance(res, str):
        print('\n\nAn Error Occured\n', end='')
        print('\tA fatal error occured while compiling your PDF. Your PDF was not compiled fully.\n\n', end='')
        print(res.as_string())
    else:
        print(f'File Compiled Successfully! Compiled File created at:\n\t{res}')
        end_time = time()
        print('\tIt took {0:0.1f} seconds.'.format(end_time - start_time))
