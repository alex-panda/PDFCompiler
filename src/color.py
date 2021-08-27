from tools import trimmed, str_to_tuple
from constants import COLORS

class Color:
    def __init__(self, red:int, green:int, blue:int, alpha:int=255):
        self.set_red(red)
        self.set_green(green)
        self.set_blue(blue)
        self.set_alpha(alpha)

    def red(self):
        return self._red

    def set_red(self, red):
        assert isinstance(red, int) and 0 <= red <= 255, f'The red of an rgba color must be an integer between 0 and 255, not {red}'
        self._red = red

    def green(self):
        return self._green

    def set_green(self, green):
        assert isinstance(green, int) and 0 <= green <= 255, f'The green of an rgba color must be an integer between 0 and 255, not {green}'
        self._green = green

    def blue(self):
        return self._blue

    def set_blue(self, blue):
        assert isinstance(blue, int) and 0 <= blue <= 255, f'The blue of an rgba color must be an integer between 0 and 255, not {blue}'
        self._blue = blue

    def alpha(self):
        return self._alpha

    def set_alpha(self, alpha):
        assert isinstance(alpha, int) and 0 <= alpha <= 255, f'The alpha of an rgba color must be an integer between 0 and 255, not {alpha}'
        self.alpha = alpha

    def rgb(self):
        return self.red(), self.green(), self.blue()

    def rgba(self):
        return self.red(), self.green(), self.blue(), self.alpha()

    @staticmethod
    def from_hex_str(hex_str:str, false_on_fail:bool=False):
        """
        Returns a Color object from a hex value string.

        If false_on_fail is True, then this method will return false if it
            cannot convert the color.
        """
        hex_str = trimmed(str(hex_str)).upper().replace('#', '').replace('0x', '')

        try:
            if len(hex_str) == 6:
                # Must be without an alpha value
                c = Color(*tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4)))
                return c
            elif len(hex_str) == 8:
                # must have an alpha value
                c = Color(*tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4, 6)))
                return c
        except:
            pass

        if false_on_fail:
            return False
        raise ValueError(f'{hex_str} could not be interpreted as a Hex value and converted into a Color')

    @staticmethod
    def from_cmyk_str(string, false_on_fail=False):
        """
        Takes a color in a CMYK tuple and converts it to an rgb Color.
        """
        try:
            as_tuple = str_to_tuple(trimmed(str(string)))
            assert len(as_tuple) == 4, f'{as_tuple} must be atleast 4 elements long'
            c, m, y, k = tuple(int(t) for t in as_tuple)

            black = ((1 - k) / 100)
            r = int(255 * ((1 - c) / 100) * black)
            g = int(255 * ((1 - m) / 100) * black)
            b = int(255 * ((1 - y) / 100) * black)

            return Color(r, g, b)
        except AssertionError:
            if false_on_fail:
                return False
            raise
        except:
            pass

        if false_on_fail:
            return False
        raise ValueError(f'{string} could not be turned into a Color')

    def to_cmyk(self):
        """
        Returns a tuple of values in CMYK (c, m, y, k) format
        """
        r, g, b = self.rgb()
        k = 1 - (max(r, g, b) / 255)
        c = (1 - (r / 255) - k) / (1 - k)
        m = (1 - (g / 255) - k) / (1 - k)
        y = (1 - (b / 255) - k) / (1 - k)
        return (c, m, y, k)

    @staticmethod
    def from_str(string, false_on_fail=False):
        """
        Returns a color object from the given string if possible, or raises a
            value error if it cannot be decoded

        if false_on_fail, then the method returns False when failing to decode
            the string rather than raising an error
        """
        string = trimmed(string)

        if string.upper() in COLORS:
            return Color.from_str(COLORS[string.upper()])

        if '#' in string or '0x' in string:
            try:
                return Color(*tuple(int(c) for c in str_to_tuple(string)))
            except:
                pass

        try:
            return  Color.from_hex_str(string)
        except:
            pass

        try:
            return Color.from_cmyk_str(string)
        except:
            pass

        if false_on_fail:
            return False
        raise ValueError(f'{string} could not be turned into a Color')

    def copy(self):
        return Color(self.red(), self.green(), self.blue(), self.alpha())

    def __repr__(self):
        return f'{self.__class__.__name__}(r={self.red()}, g={self.green()}, b={self.blue()})'
