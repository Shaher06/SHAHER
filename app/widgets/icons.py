"""Vector icons drawn with Kivy canvas primitives (no image files, scale to any size/colour).
Every icon is drawn inside a unit square; `rtl_flip` icons mirror in right-to-left layouts."""
import math

from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.properties import ListProperty, StringProperty
from kivy.uix.widget import Widget

from app import i18n
from app.widgets import theme


def _pts(x, y, w, pts):
    out = []
    for px, py in pts:
        out += [x + px * w, y + py * w]
    return out


def _line(canvas_add, pts, width, close=False):
    canvas_add(Line(points=pts, width=width, cap="round", joint="round", close=close))


def _star(cx, cy, r):
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts += [cx + rad * math.cos(ang), cy + rad * math.sin(ang)]
    return pts


def draw(name, add, x, y, w, lw, color):
    """Draw icon `name` in the square (x, y, w, w)."""
    P = lambda *pts: _pts(x, y, w, pts)
    L = lambda pts, close=False: _line(add, pts, lw, close)
    if name == "home":
        L(P((.12, .48), (.5, .85), (.88, .48))); L(P((.22, .42), (.22, .14), (.78, .14), (.78, .42)))
        L(P((.42, .14), (.42, .38), (.58, .38), (.58, .14)))
    elif name == "list":
        for yy in (.76, .5, .24):
            L(P((.3, yy), (.88, yy))); add(Ellipse(pos=(x + .1 * w, y + yy * w - lw), size=(2 * lw, 2 * lw)))
    elif name == "habits":
        add(Line(circle=(x + .5 * w, y + .5 * w, .34 * w, 40, 330), width=lw, cap="round"))
        L(P((.66, .88), (.5, .84), (.58, .68)))
    elif name == "settings":
        for yy, kx in ((.76, .3), (.5, .68), (.24, .45)):
            L(P((.1, yy), (.9, yy))); add(Ellipse(pos=(x + kx * w - .09 * w, y + yy * w - .09 * w), size=(.18 * w, .18 * w)))
    elif name == "plus":
        L(P((.5, .18), (.5, .82))); L(P((.18, .5), (.82, .5)))
    elif name == "check":
        L(P((.18, .52), (.42, .26), (.84, .74)))
    elif name == "edit":
        L(P((.2, .2), (.28, .5), (.76, .98 - .22), (.9 - .08, .52), (.5, .12), (.2, .2)))
        L(P((.28, .5), (.5, .12)))
    elif name == "archive":
        add(Line(rounded_rectangle=(x + .12 * w, y + .62 * w, .76 * w, .2 * w, 2), width=lw))
        L(P((.18, .62), (.18, .16), (.82, .16), (.82, .62))); L(P((.4, .42), (.6, .42)))
    elif name == "trash":
        L(P((.14, .8), (.86, .8))); L(P((.38, .8), (.38, .9), (.62, .9), (.62, .8)))
        L(P((.24, .8), (.3, .12), (.7, .12), (.76, .8))); L(P((.42, .6), (.42, .3))); L(P((.58, .6), (.58, .3)))
    elif name == "calendar":
        add(Line(rounded_rectangle=(x + .12 * w, y + .12 * w, .76 * w, .7 * w, 3), width=lw))
        L(P((.12, .6), (.88, .6))); L(P((.32, .72), (.32, .9))); L(P((.68, .72), (.68, .9)))
    elif name == "clock":
        add(Line(circle=(x + .5 * w, y + .5 * w, .38 * w), width=lw)); L(P((.5, .5), (.5, .74))); L(P((.5, .5), (.68, .4)))
    elif name == "bell":
        L(P((.2, .3), (.28, .42), (.3, .66), (.4, .8), (.6, .8), (.7, .66), (.72, .42), (.8, .3), (.2, .3)))
        L(P((.42, .2), (.58, .2)))
    elif name == "search":
        add(Line(circle=(x + .43 * w, y + .57 * w, .28 * w), width=lw)); L(P((.64, .36), (.86, .14)))
    elif name == "back":
        pts = P((.62, .18), (.3, .5), (.62, .82)) if not i18n.is_rtl() else P((.38, .18), (.7, .5), (.38, .82))
        L(pts)
    elif name == "chevron":     # points to the "forward" side
        L(P((.38, .18), (.7, .5), (.38, .82)) if i18n.is_rtl() is False else P((.62, .18), (.3, .5), (.62, .82)))
    elif name == "star":
        add(Line(points=_star(x + .5 * w, y + .5 * w, .42 * w), width=lw, joint="round", close=True))
    elif name == "star_fill":
        add(Line(points=_star(x + .5 * w, y + .5 * w, .42 * w), width=lw, joint="round", close=True))
        add(Line(points=_star(x + .5 * w, y + .5 * w, .22 * w), width=lw, joint="round", close=True))
    elif name == "alert":
        L(P((.5, .86), (.9, .16), (.1, .16)), close=True); L(P((.5, .4), (.5, .6))); add(Ellipse(pos=(x + .46 * w, y + .24 * w), size=(.08 * w, .08 * w)))
    elif name == "download":
        L(P((.5, .85), (.5, .3))); L(P((.3, .5), (.5, .28), (.7, .5))); L(P((.14, .12), (.86, .12)))
    elif name == "upload":
        L(P((.5, .15), (.5, .7))); L(P((.3, .5), (.5, .72), (.7, .5))); L(P((.14, .12), (.86, .12)))
    elif name == "close":
        L(P((.22, .22), (.78, .78))); L(P((.22, .78), (.78, .22)))
    elif name == "moon":
        add(Line(circle=(x + .5 * w, y + .5 * w, .34 * w, 25, 305), width=lw, cap="round"))
    elif name == "sun":
        add(Line(circle=(x + .5 * w, y + .5 * w, .18 * w), width=lw))
        for i in range(8):
            a = i * math.pi / 4
            L([x + (.5 + .3 * math.cos(a)) * w, y + (.5 + .3 * math.sin(a)) * w,
               x + (.5 + .42 * math.cos(a)) * w, y + (.5 + .42 * math.sin(a)) * w])
    elif name == "sparkle":
        L(P((.5, .1), (.58, .42), (.9, .5), (.58, .58), (.5, .9), (.42, .58), (.1, .5), (.42, .42)), close=True)
    elif name == "move":      # reschedule: calendar with arrow
        L(P((.15, .5), (.85, .5))); L(P((.62, .72), (.88, .5), (.62, .28)))
    elif name == "info":
        add(Line(circle=(x + .5 * w, y + .5 * w, .38 * w), width=lw)); L(P((.5, .3), (.5, .52))); add(Ellipse(pos=(x + .46 * w, y + .62 * w), size=(.08 * w, .08 * w)))
    else:
        add(Line(rounded_rectangle=(x + .2 * w, y + .2 * w, .6 * w, .6 * w, 3), width=lw))


class Icon(Widget):
    name = StringProperty("")
    color = ListProperty([0, 0, 0, 1])

    def __init__(self, name="", color=None, size_dp=22, **kwargs):
        from kivy.metrics import dp
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(size_dp), dp(size_dp)))
        kwargs.setdefault("pos_hint", {"center_y": .5})
        super().__init__(**kwargs)
        self.color = list(color or theme.TEXT)
        self.name = name
        self.bind(pos=self._draw, size=self._draw, name=self._draw, color=self._draw)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        side = min(self.width, self.height)
        x, y = self.x + (self.width - side) / 2, self.y + (self.height - side) / 2
        with self.canvas:
            Color(*self.color)
            draw(self.name, self.canvas.add, x, y, side, max(1.4, side * 0.085), self.color)
