from constants import ALIGNMENT, SCRIPT, STRIKE_THROUGH, UNDERLINE

def assert_bool(val):
    assert isinstance(val, (bool, None)), f'Can only be True, False, or None. {val} was given instead.'

class Markup:
    """
    A Markup for a range of MarkedUpText.
    """
    def __init__(self):
        # Enum Fields (Accept enum values from Constants)
        self._alignment = None
        self._underlined = None
        self._strikethrough = None
        self._script = None # Normal script, subscript, superscript

        # Boolean (True/False) Fields
        self._bold = None
        self._italics = None
        self._paragraph_break = None # Only applies to the start of the markup

        self._callbacks = []

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
        m.alignment = self._alignment
        m.underlined = self._underlined
        m.strikethrough = self._strikethrough
        m.script = self._script

        m.bold = self._bold
        m.italics = self._italics
        m.paragraph_break = self._paragraph_break

        m.callbacks = [f for f in self._callbacks]

    # --------------------------------
    # Methods for accessing fields

    # Enum Fields

    def alignment(self):
        return self._alignment

    def set_alignment(self, val):
        self._alignment = ALIGNMENT.validate(val)

    def script(self):
        return self._script

    def set_script(self, val):
        self._script = SCRIPT.validate(val)

    def strike_through(self):
        return self._strike_through

    def set_strike_through(self, val):
        self._strike_through = STRIKE_THROUGH.validate(val)

    def underline(self):
        return self._underline

    def set_underline(self, val):
        self._underline = UNDERLINE.validate(val)

    # Bool Fields

    def paragraph_break(self):
        return self._paragraph_break

    def set_paragraph_break(self, boolean=True):
        assert_bool(boolean)
        self._paragraph_break = boolean

    def bold(self):
        return self._paragraph_break

    def set_bold(self, boolean=True):
        assert_bool(boolean)
        self._paragraph_break = boolean

    def bold(self):
        return self._paragraph_break

    def set_italics(self, boolean=True):
        assert_bool(boolean)
        self._italics = boolean


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


