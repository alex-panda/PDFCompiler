import copy
from collections import UserString
from markup import Markup, MarkupStart, MarkupEnd
from tools import assert_instance

def copy_markups(markups):
    new_marks = {}


    # A dictionary of MarkupEnds with the keys being their old MarkupEnds that they are a copy of
    markup_ends = {}

    # A dictionary of Markup starts with the keys being the old MarkupEnds that they are the corresponding copy for
    markup_starts = {}

    for key, markup_list in markups.items():

        new_markups = []
        for m in markup_list:
            if isinstance(m, MarkupStart):
                if m.markup_end in markup_starts:
                    new_markups.append(markup_starts.pop(m.markup_end))
                else:
                    new_markup = m.markup.copy()
                    new_markup_end = MarkupEnd(new_markup)
                    new_markups.append(MarkupStart(new_markup, new_markup_end))
                    markup_ends[m.markup_end] = new_markup_end

            elif isinstance(m, MarkupEnd):
                if m in markup_ends:
                    new_markup_end = markup_ends.pop(m)
                    new_markup_end.undo_dict = None if m.undo_dict is None else m.undo_dict.copy()
                    new_markups.append(new_markup_end)
                else:
                    new_markup = m.markup.copy()
                    new_markup_end = MarkupEnd(new_markup)
                    new_markups.append(new_markup_end)

                    new_markup_start = MarkupStart(new_markup, new_markup_end)
                    markup_starts[m] = new_markup_start

            else:
                raise AssertionError(f'This is not a MarkupStart or MarkupEnd yet it was in the Markups for a MarkedUpText object: {m}')

        new_marks[key] = new_markups

    assert len(markup_ends) == 0, f'Not all markup ends were copied, these were not copied: {markup_ends}'
    assert len(markup_starts) == 0, f'Not all markup starts were copied, these were not copied: {markup_starts}'

    return new_marks


class MarkedUpText(UserString):
    """
    A peice of text that has been marked up so that it has ranges of text
        that are different things such as Bold, Italics, a different Color, etc.
    """
    def __init__(self, text=None):
        """
        text can be either a str or MarkedUpText. If str, the new MarkedUpText
            will have the text as its text. If MarkedUpText, the new MarkedUpText
            will be a copy of the one given to it.
        """

        if text:
            if isinstance(text, MarkedUpText):
                super().__init__(text.data)
                self._markups = copy_markups(text._markups)
            else:
                super().__init__(str(text))
                self._markups = {}
        else:
            super().__init__('')
            self._markups = {}

    @property
    def _text(self):
        return self.data

    def markup(self, start_index=None, end_index=None):
        """
        Returns a Markup object that marks up this Text from the start index
            to the end_index. If both the start and end index are None, then
            the text contained by this MarkedUpText will be marked up.
        """
        m = Markup()
        self.add_markup(m, start_index, end_index)
        return m

    def add_markup(self, new_markup, start_index=None, end_index=None):
        """
        A method that adds a markup to the MarkedUpText. If both start_index
            and end_index are none, the markup will be applied to the entire
            string. If only one of them are specified, the markup will start
            and end at that index. If both are specified, then the new_markup
            will start at the start_index and end at the end_index.

        Each markup starts at the start_index and ends at the end_index and
            includes them in its range. In other words, if you markup a range
            from 2-20, 2 and 20 are both included in that range and will be
            changed according to that markup.
        """
        assert start_index is None or isinstance(start_index, int), f'The starting index of a markup must be of type int. {start_index} is not an int.'
        assert end_index is None or isinstance(end_index, int), f'The ending index of a markup must be of type int. {end_index} is not an int.'

        if start_index is None and end_index is None:
            start_index = 0
            end_index = 0 if len(self.data) == 0 else len(self.data) - 1
        elif start_index is None and end_index is not None:
            start_index = end_index
        elif start_index is not None and end_index is None:
            end_index = start_index

        ms, me = new_markup.markup_start_and_end()

        # add start markup
        # Must insert it at first position to make sure that the order of MarkupStarts
        #   is a mirror image of their corresponding MarkupEnds
        if start_index in self._markups:
            self._markups[start_index].insert(0, ms)
        else:
            self._markups[start_index] = [ms]

        # add end markup
        if end_index in self._markups:
            self._markups[end_index].append(me)
        else:
            self._markups[end_index] = [me]

    def add_markup_start_or_end(self, markup_start_or_end, index):
        """
        Adds the given MarkupStart or MarkupEnd to text at the given index.
        """
        assert isinstance(index, int), f'Index must be an int. Was given: {index}'
        assert isinstance(markup_start_or_end, (MarkupStart, MarkupEnd)), f'markup_start_or_end must be of type MarkupStart or MarkupEnd, but {markup_start_or_end} was given.'

        if index in self._markups:
            self._markups[index].append(markup_start_or_end)
        else:
            val = [markup_start_or_end]
            self._markups[index] = val

    def markups_for_index(self, index:int):
        """
        Returns the list of MarkupStart or MarkupEnd objects for the given index,
            or None if there are None.
        """
        return self._markups.get(index, None)

    def _unsupported(self):
        raise NotImplementedError(f'This method is not implemented for the {self.__class__.__name__} class.')

    # -----------------------------------
    # String methods that needed to be overwritten but are supported

    def strip(self, chars=' '):
        # TODO
        self._unsupported()

    def copy(self):
        return MarkedUpText(self)

    def clear(self):
        self.data = ''
        self._markups = {}

    def join(self, iteratable):
        end_str = MarkedUpText()
        for i, item in enumerate(iteratable):
            if i > 0:
                end_str += f'{item}'
            end_str += self.copy()

        return end_str

    def __add__(self, other):
        new = self.copy()

        if isinstance(other, MarkedUpText):
            new_markups = {}

            self_len = len(new.data)

            # "key" is the index that the list of "Markup" objects is at
            for key, markup in copy_markups(other._markups).items():
                new_idx = key + self_len

                # Each "markup" is a list of Markup objects but _markups
                #   is a dict of markups in markup_index:[markup_obj, ...] pairs
                if new_idx in new._markups:
                    new._markups[new_idx].extend(markup)
                else:
                    new._markups[new_idx] = markup

            new.data += other.data

        elif isinstance(other, str):
            new.data += other
        else:
            raise Exception(f'{other} cannot be added to {self.__class__.__name__}')

        return new

    def __mult__(self, other):
        new = MarkedUpText()

        if isinstance(other, int):
            for i in range(other):
                new += self

            return new

        raise Exception(f'{self.__class__.__name__} cannot be multiplied by {other}')

    def __iadd__(self, other):
        """
        self += other
        """
        if isinstance(other, MarkedUpText):
            new_markups = {}

            self_len = len(self.data)

            for key, markup in copy_markups(other._markups).items():
                new_idx = key + self_len

                if new_idx in self._markups:
                    self._markups[new_idx].extend(markup)
                else:
                    self._markups[new_idx] = markup

            self.data += other.data

        elif isinstance(other, str):
            self.data += other
        else:
            raise Exception(f'{other} cannot be added to {self.__class__.__name__}')


        return self

    def __imul__(self, other):
        """
        self *= other
        """

        if isinstance(other, int):
            old = self.copy()

            for i in range(other):
                self += old

        else:
            raise Exception(f'{self.__class__.__name__} cannot be multiplied by {other}')

        return self

    def __eq__(self, o):
        """
        Returns true if this object is equal tot he other object, and False
            otherwise.

        For the MarkedUpText class, only the data (the actual string that the
            MarkedUpText is marking up) is compared. This is so that options
            are easy to do because you can just do

            if marked_up_text == 'command_option_name':
                ...
        """
        if isinstance(o, MarkedUpText) or issubclass(type(o), MarkedUpText):
            return self.data == o.data
        elif isinstance(o, str):
            return self.data == o
        else:
            return False

    def __nq__(self, o):
        return not (self == o)

    def __repr__(self):
        return f'{self.__class__.__name__}(text={self.data})'

    # -----------------------------------
    # String methods that are unsupported

    def append(self, other):
        self._unsupported()

    def zfill(self, width):
        self._unsupported()

    def translate(self, table):
        self._unsupported()

    def pop(self, obj):
        self._unsupported()

    def center(self, width=None, fillchar=None):
        self._unsupported()

    def reverse(self):
        self._unsupported()

    def rsplit(self, chars=' '):
        self._unsupported()

    def split(self, sep=None, maxsplit=-1):
        self._unsupported()

    def splitlines(self, keepends=False):
        self._unsupported()

    def expandtabs(self):
        self._unsupported()
