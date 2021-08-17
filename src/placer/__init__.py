from placer.placer import Placer as Placer
from placer.placers.naiveplacer import NaivePlacer as NaivePlacer

def print_tokens(tokens):
    """
    Prints all given tokens for debug purposes.
    """
    broke_par = True
    suppress_next_space = True

    from constants import TT
    from compiler import Token
    from markup import MarkupStart, MarkupEnd

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
