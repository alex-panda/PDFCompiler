from tools import assure_decimal


class Point:
    """
    An (x, y) point.
    """
    def __init__(self, x=0.0, y=0.0):
        self.set_xy(x, y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def set_x(self, x):
        self._x = assure_decimal(x)

    def set_y(self, y):
        self._y = assure_decimal(y)

    def xy(self):
        return self.x(), self.y()

    def set_xy(self, x, y):
        self.set_x(x)
        self.set_y(y)

    def __eq__(self, other):
        return isinstance(other, Point) and self.x() == other.x() and self.y() == other.y()

    def __hash__(self):
        return hash((self.x(), self.y()))

    def __add__(self, other):
        other = self._assure_point(other)
        return Point(self.x() + other.x(), self.y() + other.y())

    def __sub__(self, other):
        other = self._assure_point(other)
        return Point(self.x() - other.x(), self.y() - other.y())

    def __mult__(self, other):
        other = self._assure_point(other)
        return Point(self.x() * other.x(), self.y() * other.y())

    def __div__(self, other):
        other = self._assure_point(other)
        return Point(self.x() / other.x(), self.y() / other.y())

    def __iadd__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() + other.x(), self.y() + other.y())
        return self

    def __isub__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() - other.x(), self.y() - other.y())
        return self

    def __imul__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() * other.x(), self.y() * other.y())
        return self

    def __idiv__(self, other):
        other = self._assure_point(other)
        self.set_xy(self.x() / other.x(), self.y() / other.y())
        return self

    @staticmethod
    def _assure_point(other):
        if isinstance(other, Point):
            return other
        raise ValueError(f'Tried to compare a point to some other object that is not a point.\nThe other object: {other}')

    def copy(self):
        return Point(self.x(), self.y())

    def clear(self):
        self.set_xy(0,0)

    def __repr__(self):
        return f'{type(self).__name__}({self.x()}, {self.y()})'


class Rectangle:
    """
    A rectangle with a point that shows its offset from the upper-left hand
        corner of the ENTIRE PDF and a Height and Width that show the area of
        the PDF that the rectangle takes up.
    """
    def __init__(self, x=0, y=0, h=0, w=0, p=0):
        self.set_all(x, y, h, w, p)

    def point(self):
        return self._point

    def set_point(self, other):
        assert isinstance(other, Point), 'You can only set the point of a Rectangle to Point objects.'
        self._point = other

    def height(self):
        return self._height

    def set_height(self, other):
        self._height = assure_decimal(other)

    def width(self):
        return self._width

    def set_width(self, other):
        self._width = assure_decimal(other)

    def set_size(self, height, width=None):
        if width is None:
            self.set_height(height[0])
            self.set_width(height[1])
        else:
            self.set_height(height)
            self.set_width(width)

    def size(self):
        return self.height(), self.width()

    def set_all(self, x=0, y=0, h=0, w=0, p=0):
        """
        Sets the Rectangle's placement and dimensions. Either takes
            x, y, height, width or height, width, p=point
        """
        if p:
            self.set_point(p)
            # If p is specified, x and y should be the height and width
            self.set_height(x)
            self.set_width(y)
        else:
            self.set_point(Point(x, y))
            self.set_height(h)
            self.set_width(w)

    # Things that cannot be set but are provided for convenience

    def top(self):
        return self.y()

    def bottom(self):
        return self.y() + self.height()

    def left(self):
        return self.x()

    def right(self):
        return self.x() + self.width()

    def fits_inside(self, other_rect):
        """
        Returns True if the given Rectangle will fit inside this one, and False
            otherwise.
        """
        assert isinstance(other_rect, Rectangle), f'other_rect should have been of type Rectangle, not {other_rect}'
        # Get the top left corner and bottom right corner of both rectangles
        #   and see if this rectangle's top-left corner and bottom-right corner
        #   are in the other rectangle's top-left and bottom-right corners
        sx = self.point().x()
        sy = self.point().y()
        sox = sx + self.width()
        soy = sy + self.height()

        ox = other_rect.point().x()
        oy = other_rect.point().y()
        oox = sx + other_rect.width()
        ooy = sy + other_rect.height()

        # Compare top-left corners then bottom-right corners
        return ((sx >= ox and sy >= oy) and (sox <= oox and soy <= ooy))

    def copy(self):
        return Rectangle(self.x(), self.y(), self.height(), self.width())

    def clear(self):
        self.set_all(0, 0, 0, 0)

    def __repr__(self):
        return f'{type(self).__name__}({self.point()}, {self.size()})'

