"""In-window parameter adjustment overlay.

A semi-transparent panel containing labelled sliders for every parameter
exposed by the active visualization style. Toggle with Tab; interact with
mouse or keyboard while open.

Usage (in main.py):
    overlay = build_overlay(cfg, style, mode)
    # in event loop:
    overlay.handle_event(event)
    # after field.draw():
    overlay.draw(screen)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

_FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_FONT_PRIMARY  = _FONTS_DIR / "ShureTechMonoNerdFont-Regular.ttf"
_FONT_FALLBACK = _FONTS_DIR / "JetBrainsMonoNLNerdFont-Regular.ttf"


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Load ShureTechMono (futuristic), falling back to JetBrainsMono, then sysfont."""
    for path in (_FONT_PRIMARY, _FONT_FALLBACK):
        if path.exists():
            return pygame.font.Font(str(path), size)
    return pygame.font.SysFont("monospace", size, bold=bold)

# ── colours ───────────────────────────────────────────────────────────────────
_BG        = (15, 15, 20, 210)      # panel background (RGBA)
_TRACK     = (60, 60, 70)
_FILL      = (180, 180, 200)
_HANDLE    = (255, 255, 255)
_LABEL     = (200, 200, 210)
_VALUE     = (255, 255, 255)
_HEADER    = (150, 150, 165)
_HINT      = (90, 90, 100)
_SECTION   = (100, 100, 120)
_RESET_BG  = (60, 40, 40, 200)
_RESET_FG  = (220, 120, 120)

# ── layout constants ───────────────────────────────────────────────────────────
_PAD        = 14
_SLIDER_H   = 6
_ROW_H      = 38
_HANDLE_R   = 8
_PANEL_W    = 320
_FONT_SZ    = 13
_HEAD_SZ    = 11
_TITLE_SZ   = 15
_SEL_H      = 24          # height of each selector row
_SEL_ARR_W  = 18          # click-width allocated to ‹ and › arrows

# ── style / mode registry ─────────────────────────────────────────────────────
_STYLES    = ["Particle Cloud", "Torus Knot", "Penrose"]
_MODES_FOR = {"Particle Cloud": ["Gravitas", "Impact"]}


@dataclass
class SliderDef:
    """Definition of a single slider in the overlay.

    Attributes:
        label: Display name shown above the track.
        attr: Attribute name on the Config object.
        lo: Minimum value.
        hi: Maximum value.
        step: Snap granularity (float for floats, 1 for ints).
        fmt: Format string for the value label.

    """

    label: str
    attr: str
    lo: float
    hi: float
    step: float
    fmt: str = "{:.2f}"

    def int_fmt(self) -> bool:
        """Return True when step is a whole number."""
        return self.step >= 1 and self.step == int(self.step)


@dataclass
class SectionDef:
    """A titled group of sliders."""

    title: str
    sliders: list[SliderDef]


class Slider:
    """Rendered, interactive slider bound to a Config attribute.

    Args:
        defn: Slider definition with label, attr, range, etc.
        cfg: Config object to read from and write to.
        x: Left edge of the slider in panel-local coordinates.
        y: Top of the slider row in panel-local coordinates.
        width: Width of the track in pixels.

    """

    def __init__(self, defn: SliderDef, cfg: Any, x: int, y: int, width: int):
        self.defn = defn
        self.cfg = cfg
        self.x = x
        self.y = y
        self.width = width
        self._dragging = False
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None

    def _init_fonts(self):
        if self._font is None:
            self._font = _load_font(_FONT_SZ)
            self._small_font = _load_font(_HEAD_SZ)

    # ── value helpers ──────────────────────────────────────────────────────────

    @property
    def value(self) -> float:
        return float(getattr(self.cfg, self.defn.attr))

    @value.setter
    def value(self, v: float):
        d = self.defn
        v = max(d.lo, min(d.hi, v))
        # snap to step
        steps = round((v - d.lo) / d.step)
        v = d.lo + steps * d.step
        v = max(d.lo, min(d.hi, v))
        if d.int_fmt():
            setattr(self.cfg, d.attr, int(round(v)))
        else:
            setattr(self.cfg, d.attr, round(v, 6))

    def _t(self) -> float:
        """Normalised position [0, 1]."""
        d = self.defn
        return (self.value - d.lo) / (d.hi - d.lo) if d.hi != d.lo else 0.0

    def _handle_x(self) -> int:
        """Pixel offset from track start (self.x), not including self.x."""
        return int(self._t() * self.width)

    # ── interaction ────────────────────────────────────────────────────────────

    def hit_handle(self, px: int, py: int, panel_offset: tuple[int, int]) -> bool:
        """Return True if the point is within the handle's hit area."""
        ox, oy = panel_offset
        hx = ox + self.x + self._handle_x()
        hy = oy + self.y + 20 + _SLIDER_H // 2
        return math.hypot(px - hx, py - hy) <= _HANDLE_R + 4

    def start_drag(self):
        self._dragging = True

    def stop_drag(self):
        self._dragging = False

    @property
    def dragging(self) -> bool:
        return self._dragging

    def drag_to(self, px: int, panel_ox: int):
        """Update value from an absolute mouse X position."""
        rel = px - panel_ox - self.x
        t = max(0.0, min(1.0, rel / self.width))
        d = self.defn
        self.value = d.lo + t * (d.hi - d.lo)

    def nudge(self, direction: int):
        """Move one step left (−1) or right (+1)."""
        self.value = self.value + direction * self.defn.step

    # ── drawing ────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, panel_ox: int, panel_oy: int):
        self._init_fonts()
        d = self.defn
        ox, oy = panel_ox + self.x, panel_oy + self.y

        # label
        lbl = self._small_font.render(d.label, True, _LABEL)
        surface.blit(lbl, (ox, oy))

        # value
        if d.int_fmt():
            val_str = str(int(round(self.value)))
        else:
            val_str = d.fmt.format(self.value)
        val_surf = self._font.render(val_str, True, _VALUE)
        surface.blit(val_surf, (ox + self.width - val_surf.get_width(), oy))

        # track
        ty = oy + 20 + _SLIDER_H // 2
        pygame.draw.line(surface, _TRACK, (ox, ty), (ox + self.width, ty), _SLIDER_H)
        hx = ox + self._handle_x()
        pygame.draw.line(surface, _FILL, (ox, ty), (hx, ty), _SLIDER_H)

        # handle
        pygame.draw.circle(surface, _HANDLE, (hx, ty), _HANDLE_R)


class OverlayPanel:
    """Semi-transparent parameter panel drawn on top of the visualization.

    Toggle visibility with Tab. Style and mode selectors at the top allow
    switching effects live. Sliders below are scrollable.

    Args:
        cfg: Config object; sliders read/write it directly.
        sections_factory: Callable(style, mode) -> list[SectionDef].
        style: Initial visualization style.
        mode: Initial sub-mode or None.

    """

    def __init__(
        self,
        cfg: Any,
        sections_factory: Any,
        style: str,
        mode: str | None,
        defaults_factory: Any = None,
    ):
        self.cfg = cfg
        self._sections_factory = sections_factory
        self._defaults_factory = defaults_factory
        self._style_idx = _STYLES.index(style) if style in _STYLES else 0
        _modes = _MODES_FOR.get(self.style, [])
        self._mode_idx = _modes.index(mode) if (mode and mode in _modes) else 0
        self.sections = sections_factory(self.style, self.mode)
        self.changed = False
        self.visible = True
        self._sliders: list[Slider] = []
        self._focused: int = 0
        self._drag_slider: Slider | None = None
        self._panel_rect = pygame.Rect(0, 0, _PANEL_W, 0)
        self._scroll = 0
        self._dirty = True
        self._title_band_h = 0
        self._font: pygame.font.Font | None = None
        self._title_font: pygame.font.Font | None = None
        # Screen-space hit rects for selector arrows (populated during draw)
        self._style_lt = pygame.Rect(0, 0, 0, 0)
        self._style_rt = pygame.Rect(0, 0, 0, 0)
        self._mode_lt  = pygame.Rect(0, 0, 0, 0)
        self._mode_rt  = pygame.Rect(0, 0, 0, 0)
        self._reset_rect = pygame.Rect(0, 0, 0, 0)  # screen-space reset button

    # ── style / mode ───────────────────────────────────────────────────────────

    @property
    def style(self) -> str:
        return _STYLES[self._style_idx]

    @property
    def mode(self) -> str | None:
        modes = _MODES_FOR.get(self.style, [])
        return modes[self._mode_idx] if modes else None

    def consume_changed(self) -> bool:
        """Return and clear the changed flag."""
        c = self.changed
        self.changed = False
        return c

    def _change_style(self, direction: int):
        self._style_idx = (self._style_idx + direction) % len(_STYLES)
        self._mode_idx = 0
        self.sections = self._sections_factory(self.style, self.mode)
        self._sliders = []
        self.changed = True
        self._dirty = True

    def _change_mode(self, direction: int):
        modes = _MODES_FOR.get(self.style, [])
        if not modes:
            return
        self._mode_idx = (self._mode_idx + direction) % len(modes)
        self.sections = self._sections_factory(self.style, self.mode)
        self._sliders = []
        self.changed = True
        self._dirty = True

    def _reset_to_defaults(self):
        """Apply canonical defaults for the current style/mode to cfg."""
        if self._defaults_factory is None:
            return
        defaults = self._defaults_factory(self.style, self.mode)
        for attr, val in defaults.items():
            setattr(self.cfg, attr, val)
        self.changed = True
        self._dirty = True

    def _init_fonts(self):
        if self._font is None:
            self._font = _load_font(_HEAD_SZ)
            self._title_font = _load_font(_TITLE_SZ)

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build(self, screen_h: int):
        """(Re)build slider list and panel surface at current screen height."""
        self._init_fonts()
        self._sliders = []
        track_w = _PANEL_W - _PAD * 2

        # Title band: title + hint + style row + optional mode row + divider gap
        has_mode = bool(_MODES_FOR.get(self.style))
        title_band = (
            _PAD + _TITLE_SZ + 4       # title
            + _HEAD_SZ + 8             # hint
            + _SEL_H                   # style selector
            + (_SEL_H if has_mode else 0)  # mode selector
            + 10                       # divider + gap
        )
        self._title_band_h = title_band

        y = title_band
        for sec in self.sections:
            y += 22
            for sdef in sec.sliders:
                sl = Slider(sdef, self.cfg, _PAD, y, track_w)
                self._sliders.append(sl)
                y += _ROW_H
            y += 6

        total_h = y + _PAD
        visible_h = min(total_h, screen_h - 40)
        self._panel_rect = pygame.Rect(10, 20, _PANEL_W, visible_h)
        self._max_scroll = max(0, total_h - visible_h)
        self._total_h = total_h
        # clamp focus index after section rebuild
        if self._sliders:
            self._focused = min(self._focused, len(self._sliders) - 1)
        self._dirty = True

    def _ensure_built(self, screen: pygame.Surface):
        if not self._sliders:
            self._build(screen.get_height())

    # ── event handling ─────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event, screen: pygame.Surface) -> bool:
        """Process a pygame event; return True if consumed."""
        self._ensure_built(screen)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.visible = not self.visible
            self._dirty = True
            return True

        if not self.visible:
            return False

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(self._max_scroll, self._scroll - event.y * 20))
            self._dirty = True
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Reset button
            if self._reset_rect.collidepoint(pos):
                self._reset_to_defaults()
                return True
            # Style / mode selector arrows (screen-space rects set during draw)
            if self._style_lt.collidepoint(pos):
                self._change_style(-1)
                return True
            if self._style_rt.collidepoint(pos):
                self._change_style(1)
                return True
            if self._mode_lt.collidepoint(pos):
                self._change_mode(-1)
                return True
            if self._mode_rt.collidepoint(pos):
                self._change_mode(1)
                return True
            # Slider handles — oy accounts for the title band blit offset
            ox = self._panel_rect.x
            oy = self._panel_rect.y + self._title_band_h - self._scroll
            for i, sl in enumerate(self._sliders):
                if sl.hit_handle(pos[0], pos[1], (ox, oy)):
                    sl.start_drag()
                    self._drag_slider = sl
                    self._focused = i
                    self._dirty = True
                    return True
            if self._panel_rect.collidepoint(pos):
                return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag_slider:
                self._drag_slider.stop_drag()
                self._drag_slider = None
                return True

        if event.type == pygame.MOUSEMOTION:
            if self._drag_slider and self._drag_slider.dragging:
                self._drag_slider.drag_to(event.pos[0], self._panel_rect.x)
                self._dirty = True
                return True

        if event.type == pygame.KEYDOWN and self._sliders:
            if event.key in (pygame.K_LEFT, pygame.K_DOWN):
                self._sliders[self._focused].nudge(-1)
                self._dirty = True
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_UP):
                self._sliders[self._focused].nudge(1)
                self._dirty = True
                return True
            if event.key in (pygame.K_PAGEDOWN, pygame.K_s):
                self._focused = min(len(self._sliders) - 1, self._focused + 1)
                self._dirty = True
                return True
            if event.key in (pygame.K_PAGEUP, pygame.K_w):
                self._focused = max(0, self._focused - 1)
                self._dirty = True
                return True

        return False

    # ── drawing ────────────────────────────────────────────────────────────────

    def _draw_selector(
        self,
        surf: pygame.Surface,
        py: int,
        label: str,
        value: str,
    ) -> tuple[pygame.Rect, pygame.Rect]:
        """Draw a  ‹ Label: Value ›  row; return (left_arrow_rect, right_arrow_rect) in screen space."""
        self._init_fonts()
        f = self._font
        px = _PAD
        pr = self._panel_rect

        lbl_surf = f.render(f"{label}:", True, _HEADER)
        surf.blit(lbl_surf, (px, py + (_SEL_H - lbl_surf.get_height()) // 2))
        lbl_w = lbl_surf.get_width() + 6

        avail_w = _PANEL_W - _PAD * 2 - lbl_w

        lt_surf = f.render("‹", True, _FILL)
        lt_x = px + lbl_w
        surf.blit(lt_surf, (lt_x, py + (_SEL_H - lt_surf.get_height()) // 2))

        val_surf = f.render(value, True, _VALUE)
        mid_x = lt_x + _SEL_ARR_W + (avail_w - 2 * _SEL_ARR_W - val_surf.get_width()) // 2
        surf.blit(val_surf, (mid_x, py + (_SEL_H - val_surf.get_height()) // 2))

        rt_surf = f.render("›", True, _FILL)
        rt_x = px + lbl_w + avail_w - rt_surf.get_width()
        surf.blit(rt_surf, (rt_x, py + (_SEL_H - rt_surf.get_height()) // 2))

        # Convert clip_surf-local coords to screen space
        lt_rect = pygame.Rect(pr.x + lt_x, pr.y + py, _SEL_ARR_W + 4, _SEL_H)
        rt_rect = pygame.Rect(pr.x + rt_x - 4, pr.y + py, _SEL_ARR_W + 8, _SEL_H)
        return lt_rect, rt_rect

    def draw(self, screen: pygame.Surface):
        if not self.visible:
            return
        self._ensure_built(screen)
        self._init_fonts()

        pr = self._panel_rect
        clip_surf = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
        clip_surf.fill(_BG)

        # Title
        title = self._title_font.render("Parameters  [Tab]", True, _VALUE)
        clip_surf.blit(title, (_PAD, _PAD))

        # Reset button — top-right of panel
        reset_label = self._font.render("↺ reset", True, _RESET_FG)
        reset_w = reset_label.get_width() + 10
        reset_h = reset_label.get_height() + 4
        reset_x = _PANEL_W - _PAD - reset_w
        reset_y = _PAD
        reset_surf = pygame.Surface((reset_w, reset_h), pygame.SRCALPHA)
        reset_surf.fill(_RESET_BG)
        reset_surf.blit(reset_label, (5, 2))
        clip_surf.blit(reset_surf, (reset_x, reset_y))
        self._reset_rect = pygame.Rect(
            pr.x + reset_x, pr.y + reset_y, reset_w, reset_h
        )

        # Hint
        hint = self._font.render("drag / \u2190\u2192 adjust  \u2022  W/S focus", True, _HINT)
        clip_surf.blit(hint, (_PAD, _PAD + _TITLE_SZ + 4))

        # Selector rows
        sel_y = _PAD + _TITLE_SZ + 4 + _HEAD_SZ + 6

        self._style_lt, self._style_rt = self._draw_selector(
            clip_surf, sel_y, "Style", self.style
        )
        sel_y += _SEL_H

        modes = _MODES_FOR.get(self.style, [])
        if modes:
            self._mode_lt, self._mode_rt = self._draw_selector(
                clip_surf, sel_y, "Mode", self.mode or ""
            )
            sel_y += _SEL_H
        else:
            self._mode_lt = pygame.Rect(0, 0, 0, 0)
            self._mode_rt = pygame.Rect(0, 0, 0, 0)

        # Divider
        div_y = sel_y + 3
        pygame.draw.line(clip_surf, _SECTION, (_PAD, div_y), (_PANEL_W - _PAD, div_y))

        # Scrollable inner surface
        inner = pygame.Surface((_PANEL_W, self._total_h), pygame.SRCALPHA)
        inner.fill((0, 0, 0, 0))

        y_cursor = self._title_band_h
        sl_idx = 0
        for sec in self.sections:
            sec_lbl = self._font.render(f"\u2500\u2500 {sec.title} \u2500\u2500", True, _SECTION)
            inner.blit(sec_lbl, (_PAD, y_cursor))
            y_cursor += 22
            for _ in sec.sliders:
                sl = self._sliders[sl_idx]
                if sl_idx == self._focused:
                    pygame.draw.rect(
                        inner,
                        (40, 40, 60, 120),
                        (_PAD - 4, y_cursor - 2, _PANEL_W - _PAD, _ROW_H - 2),
                        border_radius=4,
                    )
                sl.draw(inner, 0, 0)
                y_cursor += _ROW_H
                sl_idx += 1
            y_cursor += 6

        title_band = self._title_band_h
        clip_surf.blit(
            inner, (0, title_band),
            (0, self._scroll, pr.width, pr.height - title_band),
        )

        pygame.draw.rect(clip_surf, (80, 80, 100), clip_surf.get_rect(), 1, border_radius=6)
        screen.blit(clip_surf, pr.topleft)
