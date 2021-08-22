from tools import assure_decimal
from decimal import Decimal

class Shape:
    def __init__(self, line_cap=2, line_join=2, miter_limit=4):
        self.set_line_cap(line_cap)
        self.set_line_join(line_join)
        self.set_miter_limit(miter_limit)

    def line_cap(self):
        return self._line_cap

    def set_line_cap(self, line_cap:int):
        """
        The line cap is what the end of a line looks like if it is not attached
            to another line.

        0=butt, 1=round, 2=square
        """
        assert isinstance(line_cap, int) and 0 <= line_cap <= 2, f'Line cap must be between 0 and 2 inclusive, not {line_cap}'
        self._line_cap = line_cap

    def line_join(self):
        return self._line_join

    def set_line_join(self, line_join:int):
        """
        The line cap is what the end of a line looks like if it is attached to
            another line.

        0=mitre, 1=round, 2=bevel
        """
        assert isinstance(line_join, int) and 0 <= line_join <= 2, f'Line join must be between 0 and 2 inclusive, not {line_join}'
        self._line_join = line_join

    def miter_limit(self):
        return self._miter_limit

    def set_miter_limit(self, miter_limit:int):
        """
        When mitre line joins get closer and closer to 180 degrees, they get
            more and more "spiky". The miter limit sets how spiky mitre line
            joins CAN be.

        miter_limit should be an integer.
        """
        assert isinstance(miter_limit, int), f'Miter limit must be an integer'
        self._miter_limit = miter_limit

    def copy():
        raise NotImplementedError()

    def draw_on_canvas(self, canvas):
        canvas.setLineCap(self.line_cap())
        canvas.setLineJoin(self.line_join())
        canvas.setMiterLimit(self.miter_limit())

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
        return self._x, self._y

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

class Line(Shape):
    def __init__(self, x1, y1, x2=None, y2=None, width=1, line_cap=2, line_join=2, miter_limit=4):
        """
        Accepts either Line(x1, y1, x2, y2) or Line(Point(x1, y1), Point(x2, y2))
        """
        super().__init__(line_cap, line_join, miter_limit)
        if x2 and y2:
            self.set_point1(x1)
            self.set_point2(y1)
        else:
            self.set_point1(x1, y1)
            self.set_point2(x2, y2)

        self.set_width(width)

    def width(self):
        return self._width

    def set_width(self, width):
        assert width >= 0 and isinstance(width, (float, Decimal, int)), f'The width of a line must be of type float, Decmial, or int and and must be greater than or equal to 0, not {width}'
        self._width = width

    def point1(self):
        return self._point1

    def set_point1(self, x, y=None):
        """
        Accepts either set_point1(x, y) or set_point1(Point(x, y))
        """
        if y:
            self._point1 = x.copy()
        else:
            self._point1 = Point(x, y)

    def point2(self):
        return self._point2

    def set_point1(self, x, y=None):
        """
        Accepts either set_point1(x, y) or set_point1(Point(x, y))
        """
        if y:
            self._point2 = x.copy()
        else:
            self._point2 = Point(x, y)

    def copy(self):
        return Line(*self._point1.xy(), *self._point2.xy())

    def draw_on_canvas(self, canvas):
        super().draw_on_canvas(canvas)
        canvas.setLineWidth(float(self.width()))
        canvas.line(*self._point1.xy(), *self._point2.xy())

class Rectangle(Shape):
    """
    A rectangle with a point that shows its offset from the upper-left hand
        corner of the ENTIRE PDF and a Height and Width that show the area of
        the PDF that the rectangle takes up.
    """
    def __init__(self, x=0, y=0, w=0, h=0, p=None, stroke=1, fill=0, line_cap=2, line_join=2, miter_limit=4):
        super().__init__(line_cap, line_join, miter_limit)
        self._stroke = stroke
        self._fill = fill
        self.set_all(x, y, w, h, p)

    def set_stroke(self, stroke=1):
        self._stroke = stroke

    def stroke(self):
        return self._stroke

    def set_fill(self, fill=0):
        self._fill = fill

    def fill(self):
        return self._fill

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

    def size(self):
        return self.width(), self.height()

    def set_size(self, width, height=None):
        if height is None:
            self.set_width(width[0])
            self.set_height(width[1])
        else:
            self.set_width(width)
            self.set_height(height)

    def set_all(self, x=0, y=0, w=0, h=0, p=None):
        """
        Sets the Rectangle's placement and dimensions. Either takes
            x, y, height, width or height, width, p=point
        """
        if p is not None:
            self.set_point(p)
            # If p is specified, x and y should be the height and width
            self.set_height(x)
            self.set_width(y)
        else:
            self.set_point(Point(x, y))
            self.set_width(w)
            self.set_height(h)

    # Things that cannot be set but are provided for convenience

    def top(self):
        return self.y()

    def bottom(self):
        return self.y() + self.height()

    def left(self):
        return self.x()

    def right(self):
        return self.x() + self.width()

    def top_left(self):
        return Point(self.left(), self.top())

    def top_right(self):
        return Point(self.right(), self.top())

    def bottom_left(self):
        return Point(self.left(), self.bottom())

    def bottom_right(self):
        return Point(self.right(), self.bottom())

    def center(self):
        return Point(self.left() + (self.width() / 2), self.top() + (self.height() / 2))

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
        return Rectangle(self.x(), self.y(), self.width(), self.height())

    def clear(self):
        self.set_all(0, 0, 0, 0)

    def draw_on_canvas(self, canvas):
        Shape.draw_on_canvas(self, canvas)
        canvas.rect(*self.point().xy(), self.width(), self.height(), self.stroke(), self.fill())

    def __eq__(self, o):
        return isinstance(o, Rectangle) and self.point() == o.point() and self.size() == o.size()

    def __repr__(self):
        return f'{type(self).__name__}({self.point()}, {self.size()})'

from reportlab.pdfgen.pathobject import PDFPathObject as _Path

class Path(_Path, Shape):
    def __init__(self, line_cap=2, line_join=2, miter_limit=4):
        _Path.__init__(self)
        Shape.__init__(self, line_cap, line_join, miter_limit)

    def draw_on_canvas(self, canvas):
        Shape.draw_on_canvas(self, canvas)
        canvas.drawPath(self)

    # The below methods exist to essentially overide the Path's methods and make
    #   the method names conform to the API because the Path methods are in
    #   lowerCamelCase but this API uses snake_case

    def move_to(self, x, y=None):
        if y is None:
            # for Point(x, y)
            _Path.moveTo(*x.xy())
        else:
            _Path.moveTo(x, y)

    def line_to(self, x, y=None):
        if y is None:
            # for Point(x, y)
            assert isinstance(x, Point), f'x must be a Point if y is not given, not {x}'
            _Path.lineTo(*x.xy())
        else:
            _Path.lineTo(x, y)

    def curve_to(self, x1, y1, x2, y2=None, x3=None, y3=None):
        """
        Draws a curve from the first point, through the second point, and to
            the third point.
        """
        if y2 is None and x3 is None and y3 is None:
            # for curve_to(Point(x1, y1), Point(x2, y2), Point(x3, y3))
            assert isinstance(x1, Point) and isinstance(y1, Point) and isinstance(x2, Point), f'x1, y1, x2 must be Points if y2, x3, and y3 are None, not {x1}, {y1}, {x2}'
            _Path.curveTo(*x1.xy(), *y1.xy(), *x2.xy())
        else:
            _Path.curveTo(x1, y1, x2, y2, x3, y3)

    def arc(self, x1,y1, x2=None,y2=None, start_ang=0, extent=90):
        """
        Draw a partial ellipse inscribed within the rectangle x1,y1,x2,y2,
        starting at startAng degrees and covering extent degrees. Angles
        start with 0 to the right (+x) and increase counter-clockwise.
        These should have x1<x2 and y1<y2.
        """
        if x2 is None and y2 is None:
            # for when given rect(Point(x1, y1), Point(x2, y2), start_ang, extent)
            assert isinstance(x1, Point) and isinstance(y1, Point), f'x1, y1 must be Points if x2 and y2 are None, not {x1}, {y1}'
            _Path.arcTo(self, *x1.xy(), *y1.xy(), start_ang, extent)
        else:
            _Path.arc(self, x1,y1, x2,y2, start_ang, extent)

    def arc_to(self, x1,y1, x2=None,y2=None, start_ang=0, extent=90):
        """
        Like arc, but draws a line from the current point to
        the start if the start is not the current point.
        """
        if x2 is None and y2 is None:
            # for when given rect(Point(x1, y1), Point(x2, y2), start_ang, extent)
            assert isinstance(x1, Point) and isinstance(y1, Point), f'x1, y1 must be Points if x2 and y2 are None, not {x1}, {y1}'
            _Path.arcTo(self, *x1.xy(), *y1.xy(), start_ang, extent)
        else:
            _Path.arcTo(self, x1,y1, x2,y2, start_ang, extent)

    def rect(self, x, y, width=None, height=None):
        """
        Adds a rectangle to the path
        """
        if width is None and height is None:
            # for when given rect(Point(x, y), (width, height))
            assert isinstance(x, Point) and isinstance(y, iter) and len(y) == 2, f'x must be a Point and y must be an iterable with 2 elements if width and height are None, not {x}, {y}'
            _Path.rect(self, *x.xy(), *y)
        else:
            _Path.rect(self, x , y, width, height)

    def ellipse(self, x, y, width=None, height=None):
        """adds an ellipse to the path"""
        if width is None and height is None:
            # for when given ellipse(Point(x, y), (width, height))
            assert isinstance(x, Point) and isinstance(y, iter) and len(y) == 2, f'x must be a Point and y must be an iterable with 2 elements if width and height are None, not {x}, {y}'
            _Path.ellipse(self, *x.xy(), *y)
        else:
            _Path.ellipse(self, x, y, width, height)

    def circle(self, x_cen, y_cen, r=None):
        """
        Adds a circle to the path
        """
        if r is None:
            # for circle(Point(x_cen, y_cen), radius)
            assert isinstance(x_cen, Point) and isinstance(y_cen, (int, float, Decimal)), f'x_cen must be a point and y_cen must be an int, float or Decimal if r is None, not {x_cen}, {y_cen}'
            _Path.circle(self, *x_cen.xy(), y_cen)
        else:
            _Path.circle(self, x_cen, y_cen, r)

    def round_rect(self, x, y, width, height=None, radius=None):
        """
        Draws a rectangle with rounded corners. The corners are
        approximately quadrants of a circle, with the given radius.
        """
        if height is None and radius is None:
            # for when given round_rect(Point(x, y), (width, height), radius)
            assert isinstance(x, Point) and isinstance(y, iter) and len(y) == 2 and isinstance(height, (int, float, Decimal)), f'x must be a Point, y must be an iterable with 2 elements, and width must be an int, float, or Decimal if height and radius are None, not {x}, {y}, {width}'
            _Path.roundRect(self, *x.xy(), *y, width)
        else:
            _Path.roundRect(self, x, y, width, height, radius)
