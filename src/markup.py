from constants import ALIGNMENT, SCRIPT, STRIKE_THROUGH, UNDERLINE

def assert_bool(val):
    assert isinstance(val, (bool, None)), f'Can only be True, False, or None. {val} was given instead.'

class Markup:
    """
    A Markup for a range of MarkedUpText.
    """
    def __init__(self):
        from placer.templates import TextInfo
        self._text_info = TextInfo()
        self._paragraph_break = None # Only applies to the start of the markup

        self._second_pass_python = []

    def set_paragraph_break(self, boolean):
        assert_bool(boolean)
        self._paragraph_break = boolean

    def paragraph_break(self):
        return self._paragraph_break

    def add_callback(self, function):
        """
        Functions that you want to be called when this Markup is reached.
            Nothing is passed to the Function.
        """
        self._callbacks.append(function)

    def markup_start(self):
        return MarkupStart(self)

    def markup_end(self):
        return MarkupEnd(self)

    def copy(self):
        m = Markup()
        m._text_info = self._text_info.copy()
        m.paragraph_break = self._paragraph_break
        return m

    # --------------------------------
    # Methods for accessing fields

    # Enum Fields

    def text_info(self):
        return self._text_info

    def set_text_info(self, text_info):
        from placer.templates import TextInfo
        assert isinstance(text_info, TextInfo), f'Text info must be of type TextInfo, not {text_info}.'
        self._text_info = text_info

    # Other Fields

    def python(self):
        return self._second_pass_python

    def add_python(self, python_token):
        self._second_pass_python.append(python_token)

    def callbacks(self):
        return self._callbacks

    def add_callback(self, callback_function):
        self._callbacks.append(callback_function)


class MarkupStart:
    __slots__ = ['markup']
    def __init__(self, markup):
        self.markup = markup

    def copy(self):
        return MarkupStart(self.markup)

class MarkupEnd:
    __slots__ = ['markup']
    def __init__(self, markup):
        self.markup = markup

    def copy(self):
        return MarkupEnd(self.markup)


