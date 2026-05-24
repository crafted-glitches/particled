"""pygame-compatible 2-D drawing layer built on Pillow + GLFW.

Drop-in replacement for the subset of pygame used by this project:
  - Surface / Rect / draw / font / image
  - Event types and key constants (GLFW key codes)

Import as::

    from particled import compat as pygame

and the rest of the code needs no changes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont as _PilFont

# ---------------------------------------------------------------------------
# Constants that overlay.py / main.py use as flags
# ---------------------------------------------------------------------------

SRCALPHA = 1  # flag value (accepted but ignored — all Surfaces use RGBA)

# ---------------------------------------------------------------------------
# Colour helper
# ---------------------------------------------------------------------------


def _to_rgba(color: tuple) -> tuple:
    """Expand (r,g,b) to (r,g,b,255); pass (r,g,b,a) through."""
    if len(color) == 3:
        return (int(color[0]), int(color[1]), int(color[2]), 255)
    return (int(color[0]), int(color[1]), int(color[2]), int(color[3]))


# ---------------------------------------------------------------------------
# Rect
# ---------------------------------------------------------------------------


class Rect:
    """Minimal pygame.Rect replacement."""

    __slots__ = ("x", "y", "width", "height")

    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = int(x)
        self.y = int(y)
        self.width = int(w)
        self.height = int(h)

    # ── properties expected by overlay.py ─────────────────────────────────

    @property
    def topleft(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def right(self) -> int:
        return self.x + self.width

    def get_rect(self) -> "Rect":
        return Rect(0, 0, self.width, self.height)

    def collidepoint(self, pos: tuple) -> bool:
        x, y = pos
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def __iter__(self):
        return iter((self.x, self.y, self.width, self.height))

    def __repr__(self) -> str:
        return f"Rect({self.x}, {self.y}, {self.width}, {self.height})"


# ---------------------------------------------------------------------------
# Surface  (PIL Image wrapper)
# ---------------------------------------------------------------------------


class Surface:
    """pygame.Surface replacement backed by a Pillow RGBA Image."""

    def __init__(self, size: tuple[int, int], flags: int = 0):
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        self._img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self._draw_ctx: ImageDraw.ImageDraw | None = None

    # ── internal helpers ───────────────────────────────────────────────────

    def _get_draw(self) -> ImageDraw.ImageDraw:
        if self._draw_ctx is None:
            self._draw_ctx = ImageDraw.Draw(self._img, "RGBA")
        return self._draw_ctx

    def _invalidate(self) -> None:
        """Call after any paste / structural change to invalidate draw cache."""
        self._draw_ctx = None

    # ── pygame-compatible API ──────────────────────────────────────────────

    def get_size(self) -> tuple[int, int]:
        return self._img.size

    def get_width(self) -> int:
        return self._img.width

    def get_height(self) -> int:
        return self._img.height

    def get_rect(self) -> Rect:
        return Rect(0, 0, self._img.width, self._img.height)

    def fill(self, color: tuple) -> None:
        self._invalidate()
        rgba = _to_rgba(color)
        # Replace image with a fresh solid-color image (fastest fill)
        self._img = Image.new("RGBA", self._img.size, rgba)

    def blit(
        self,
        src: "Surface",
        dest: tuple | Rect,
        area: tuple | None = None,
    ) -> None:
        """Composite *src* onto *self* at *dest*."""
        self._invalidate()
        if isinstance(dest, Rect):
            x, y = dest.x, dest.y
        elif hasattr(dest, "__iter__"):
            it = iter(dest)
            x, y = int(next(it)), int(next(it))
        else:
            x, y = int(dest[0]), int(dest[1])

        src_img = src._img
        if area is not None:
            ax, ay, aw, ah = area
            src_img = src_img.crop((ax, ay, ax + aw, ay + ah))

        # Alpha-composite only the affected region — O(src_w × src_h) instead
        # of O(full_surface).  The original pygame blit was hardware-accelerated
        # (SDL2); PIL is CPU-side so we must avoid full-surface composites.
        if src_img.mode == "RGBA":
            sw, sh = src_img.size
            dw, dh = self._img.size
            # Clamp to destination bounds
            x0, y0 = max(x, 0), max(y, 0)
            x1 = min(x + sw, dw)
            y1 = min(y + sh, dh)
            if x1 <= x0 or y1 <= y0:
                return  # fully out-of-bounds
            # Crop src to the visible sub-region
            crop_src = src_img.crop((x0 - x, y0 - y, x1 - x, y1 - y))
            dst_region = self._img.crop((x0, y0, x1, y1))
            composited = Image.alpha_composite(dst_region, crop_src)
            self._img.paste(composited, (x0, y0))
        else:
            self._img.paste(src_img, (x, y))

    def tobytes(self) -> bytes:
        """Return raw RGBA bytes (row-major, top-to-bottom) for GL upload."""
        return self._img.tobytes()

    # Allow reading back as Image (used by GLRenderer.composite_surface)
    @property
    def _pil_image(self) -> Image.Image:
        return self._img


# ---------------------------------------------------------------------------
# draw  (namespace mirroring pygame.draw)
# ---------------------------------------------------------------------------


class draw:
    """Static-method namespace replacing pygame.draw.*"""

    @staticmethod
    def line(
        surface: Surface,
        color: tuple,
        start_pos: tuple,
        end_pos: tuple,
        width: int = 1,
    ) -> None:
        d = surface._get_draw()
        d.line(
            [
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])),
            ],
            fill=_to_rgba(color),
            width=max(1, int(width)),
        )

    @staticmethod
    def circle(
        surface: Surface,
        color: tuple,
        center: tuple,
        radius: int | float,
        width: int = 0,
    ) -> None:
        d = surface._get_draw()
        cx, cy = int(center[0]), int(center[1])
        r = max(1, int(radius))
        box = [cx - r, cy - r, cx + r, cy + r]
        rgba = _to_rgba(color)
        if width == 0:
            d.ellipse(box, fill=rgba)
        else:
            d.ellipse(box, outline=rgba, width=max(1, int(width)))

    @staticmethod
    def rect(
        surface: Surface,
        color: tuple,
        rect: tuple | Rect,
        width: int = 0,
        border_radius: int = 0,
    ) -> None:
        d = surface._get_draw()
        if isinstance(rect, Rect):
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
        else:
            x, y, w, h = int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])
        rgba = _to_rgba(color)
        box = [x, y, x + w, y + h]
        if border_radius > 0:
            if width == 0:
                d.rounded_rectangle(box, radius=border_radius, fill=rgba)
            else:
                d.rounded_rectangle(
                    box, radius=border_radius, outline=rgba, width=max(1, int(width))
                )
        else:
            if width == 0:
                d.rectangle(box, fill=rgba)
            else:
                d.rectangle(box, outline=rgba, width=max(1, int(width)))

    @staticmethod
    def lines(
        surface: Surface,
        color: tuple,
        closed: bool,
        points: Sequence[tuple],
        width: int = 1,
    ) -> None:
        if len(points) < 2:
            return
        d = surface._get_draw()
        pts = [(int(p[0]), int(p[1])) for p in points]
        rgba = _to_rgba(color)
        d.line(pts, fill=rgba, width=max(1, int(width)))
        if closed:
            d.line([pts[-1], pts[0]], fill=rgba, width=max(1, int(width)))


# ---------------------------------------------------------------------------
# font  (namespace mirroring pygame.font)
# ---------------------------------------------------------------------------


class Font:
    """pygame.font.Font replacement backed by PIL ImageFont."""

    def __init__(self, path: str | Path | None, size: int, bold: bool = False):
        self._size = size
        if path and Path(path).exists():
            try:
                self._pil_font = _PilFont.truetype(str(path), size)
                return
            except Exception:
                pass
        # Fallback to a bundled bitmap font (always available)
        try:
            self._pil_font = _PilFont.load_default(size=size)
        except TypeError:
            # Pillow < 10 doesn't accept size= on load_default
            self._pil_font = _PilFont.load_default()

    def render(self, text: str, antialias: bool, color: tuple) -> Surface:
        """Return a Surface with *text* drawn on a transparent background."""
        rgba = _to_rgba(color)
        try:
            bbox = self._pil_font.getbbox(text)
        except AttributeError:
            # Very old Pillow fallback
            w, h = self._pil_font.getsize(text)  # type: ignore[attr-defined]
            bbox = (0, 0, w, h)

        left, top, right, bottom = bbox
        w = max(1, right - left)
        h = max(1, bottom - top)

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        d.text((-left, -top), text, fill=rgba, font=self._pil_font)

        s = Surface.__new__(Surface)
        s._img = img
        s._draw_ctx = None
        return s

    def size(self, text: str) -> tuple[int, int]:
        """Return (width, height) of *text* in this font."""
        try:
            bbox = self._pil_font.getbbox(text)
            return (max(0, bbox[2] - bbox[0]), max(0, bbox[3] - bbox[1]))
        except AttributeError:
            return self._pil_font.getsize(text)  # type: ignore[attr-defined]


class font:
    """pygame.font module replacement."""

    @staticmethod
    def Font(path: str | Path | None, size: int, bold: bool = False) -> "Font":
        return Font(path, size, bold)

    @staticmethod
    def SysFont(name: str, size: int, bold: bool = False) -> "Font":
        # Try common system mono paths; fall back to PIL default
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        ]
        for p in candidates:
            if Path(p).exists():
                return Font(p, size, bold)
        return Font(None, size, bold)


# ---------------------------------------------------------------------------
# image  (subset used by gl_renderer.composite_surface)
# ---------------------------------------------------------------------------


class image:
    """pygame.image module replacement."""

    @staticmethod
    def tobytes(surface: Surface, fmt: str = "RGBA", flipped: bool = False) -> bytes:
        """Return raw pixel bytes from *surface* (RGBA, top-to-bottom)."""
        img = surface._img
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        if flipped:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return img.tobytes()


# ---------------------------------------------------------------------------
# surfarray  (stub — only the CPU render path in base.py uses this, and that
# path is never reached when cfg.use_gl=True, which is always the case)
# ---------------------------------------------------------------------------


class surfarray:
    """Stub replacement for pygame.surfarray."""

    @staticmethod
    def pixels2d(surface: "Surface"):
        raise NotImplementedError(
            "surfarray.pixels2d is not available without pygame-ce; "
            "use GL mode (cfg.use_gl=True) instead."
        )


# ---------------------------------------------------------------------------
# Event system  (GLFW-based key codes + simple Event dataclass)
# ---------------------------------------------------------------------------

# Import glfw lazily so compat.py can be imported before glfw.init()
try:
    import glfw as _glfw

    # Key codes — map to GLFW integer values
    K_ESCAPE = _glfw.KEY_ESCAPE      # 256
    K_TAB    = _glfw.KEY_TAB         # 258
    K_g      = _glfw.KEY_G           # 71
    K_G      = _glfw.KEY_G
    K_LEFT   = _glfw.KEY_LEFT        # 263
    K_RIGHT  = _glfw.KEY_RIGHT       # 262
    K_UP     = _glfw.KEY_UP          # 265
    K_DOWN   = _glfw.KEY_DOWN        # 264
    K_PAGEUP = _glfw.KEY_PAGE_UP     # 266
    K_PAGEDOWN = _glfw.KEY_PAGE_DOWN # 267
    K_s      = _glfw.KEY_S           # 83
    K_w      = _glfw.KEY_W           # 87

except ImportError:
    # glfw not installed yet — define placeholder ints so module import works
    K_ESCAPE   = 256
    K_TAB      = 258
    K_g        = 71
    K_G        = 71
    K_LEFT     = 263
    K_RIGHT    = 262
    K_UP       = 265
    K_DOWN     = 264
    K_PAGEUP   = 266
    K_PAGEDOWN = 267
    K_s        = 83
    K_w        = 87

# Event type strings
QUIT            = "quit"
KEYDOWN         = "keydown"
MOUSEBUTTONDOWN = "mousebuttondown"
MOUSEBUTTONUP   = "mousebuttonup"
MOUSEMOTION     = "mousemotion"
MOUSEWHEEL      = "mousewheel"
VIDEORESIZE     = "videoresize"


@dataclass
class Event:
    """Unified event object (replaces pygame.event.Event)."""

    type: str
    key: int = 0
    pos: tuple = field(default_factory=lambda: (0, 0))
    button: int = 0
    # MOUSEWHEEL: scroll delta
    x: float = 0.0
    y: float = 0.0
    # VIDEORESIZE: new dimensions
    w: int = 0
    h: int = 0
    rel: tuple = field(default_factory=lambda: (0, 0))
