"""Dear ImGui-based parameter overlay.

Replaces the PIL-backed OverlayPanel with GPU-rendered Dear ImGui widgets.
No surface allocations, no tobytes() uploads — ImGui draws directly into the
OpenGL framebuffer via the C++ imgui_impl_glfw + imgui_impl_opengl3 backends
(no PyOpenGL involved).

Usage in main.py::

    from particled.visuals.imgui_overlay import ImguiOverlay

    # After glfw.make_context_current():
    overlay = ImguiOverlay(window, cfg, style, mode, sections_factory, defaults_factory)

    # In render loop — AFTER all moderngl draws, BEFORE swap_buffers():
    overlay.render()

    # Tab key → overlay.toggle_visible()
    # Style/mode change detection:
    if overlay.consume_changed():
        field = _make_field(overlay.style, overlay.mode, cfg)

    # On exit:
    overlay.shutdown()
"""

from __future__ import annotations

import ctypes
import importlib.util
import time
from pathlib import Path
from typing import Any, Callable


def _preload_bundled_glfw() -> None:
    """Pre-load the X11 GLFW library before importing imgui_bundle.

    imgui-bundle's C++ extension (_imgui_bundle.so) needs ``glfwGetX11Window``
    and other GLX-related symbols that exist only in the X11 build of GLFW.
    We first try the Python ``glfw`` package's own ``x11/libglfw.so`` (same
    instance Python uses, so imgui and Python share one GLFW state machine).
    If not found, fall back to imgui-bundle's own bundled ``libglfw.so.3``.

    RTLD_GLOBAL makes the symbols globally visible so that ``_imgui_bundle.so``
    can find them when it is dlopen'd by the Python import machinery.
    """
    # Prefer the Python glfw package's x11 variant (same GLFW instance as Python)
    spec = importlib.util.find_spec("glfw")
    if spec and spec.origin:
        x11_path = Path(spec.origin).parent / "x11" / "libglfw.so"
        if x11_path.exists():
            ctypes.CDLL(str(x11_path), mode=ctypes.RTLD_GLOBAL)
            return
    # Fallback: imgui-bundle's own bundled libglfw
    spec = importlib.util.find_spec("imgui_bundle")
    if spec and spec.origin:
        glfw_path = Path(spec.origin).parent / "libglfw.so.3"
        if glfw_path.exists():
            ctypes.CDLL(str(glfw_path), mode=ctypes.RTLD_GLOBAL)


_preload_bundled_glfw()

from imgui_bundle import imgui  # noqa: E402
from imgui_bundle.imgui import backends as _imgui_backends  # noqa: E402

# Style/mode registry (mirrors overlay.py constants)
_STYLES: list[str] = ["Particle Cloud", "Torus Knot", "Penrose"]
_MODES_FOR: dict[str, list[str]] = {"Particle Cloud": ["Gravitas", "Impact"]}


def _fmt_to_printf(fmt: str) -> str:
    """Convert a Python format spec like ``'{:.2f}'`` to a printf spec ``'%.2f'``."""
    return fmt.replace("{:", "%").replace("}", "")


class ImguiOverlay:
    """Dear ImGui parameter panel bound to a GLFW window.

    Args:
        window:           GLFW window handle (from glfw.create_window).
        cfg:              Config object; sliders read/write it directly.
        style:            Initial visualization style name.
        mode:             Initial sub-mode name, or None.
        sections_factory: Callable(style, mode) → list[SectionDef].
        defaults_factory: Callable(style, mode) → dict[str, Any], or None.
    """

    def __init__(
        self,
        window: Any,
        cfg: Any,
        style: str,
        mode: str | None,
        sections_factory: Callable,
        defaults_factory: Callable | None = None,
    ) -> None:
        self._cfg = cfg
        self._sections_factory = sections_factory
        self._defaults_factory = defaults_factory
        self.visible: bool = True
        self._changed: bool = False

        self._style_idx = _STYLES.index(style) if style in _STYLES else 0
        _modes = _MODES_FOR.get(self.style, [])
        self._mode_idx = _modes.index(mode) if (mode and mode in _modes) else 0

        imgui.create_context()

        # Disable imgui .ini persistence (no file written to cwd)
        imgui.get_io().set_ini_filename("")

        # C++ backends: no PyOpenGL involved.
        # install_callbacks=True — imgui installs its own GLFW callbacks and
        # chains any previously-registered ones, giving ImGui mouse/keyboard.
        window_address = ctypes.cast(window, ctypes.c_void_p).value
        _imgui_backends.glfw_init_for_opengl(window_address, True)
        _imgui_backends.opengl3_init("#version 330")

        self._apply_theme()

    # ── theme ──────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        imgui.style_colors_dark()
        s = imgui.get_style()
        s.window_rounding = 6.0
        s.frame_rounding  = 3.0
        s.grab_rounding   = 3.0
        s.frame_padding   = (6.0, 3.0)
        s.item_spacing    = (8.0, 5.0)

        # Semi-transparent dark background matching the PIL overlay aesthetic
        C = imgui.Col_
        sc = s.set_color_
        sc(C.window_bg,        (0.06, 0.06, 0.09, 0.88))
        sc(C.frame_bg,         (0.14, 0.14, 0.20, 1.00))
        sc(C.frame_bg_hovered, (0.22, 0.22, 0.32, 1.00))
        sc(C.frame_bg_active,  (0.28, 0.28, 0.40, 1.00))
        sc(C.slider_grab,      (0.75, 0.75, 0.88, 1.00))
        sc(C.slider_grab_active, (1.00, 1.00, 1.00, 1.00))
        sc(C.button,           (0.38, 0.20, 0.20, 1.00))
        sc(C.button_hovered,   (0.55, 0.28, 0.28, 1.00))
        sc(C.header,           (0.20, 0.20, 0.30, 1.00))
        sc(C.header_hovered,   (0.28, 0.28, 0.42, 1.00))
        sc(C.header_active,    (0.35, 0.35, 0.52, 1.00))
        sc(C.title_bg,         (0.08, 0.08, 0.12, 1.00))
        sc(C.title_bg_active,  (0.12, 0.12, 0.18, 1.00))

    # ── properties ─────────────────────────────────────────────────────────────

    @property
    def style(self) -> str:
        return _STYLES[self._style_idx]

    @property
    def mode(self) -> str | None:
        modes = _MODES_FOR.get(self.style, [])
        return modes[self._mode_idx] if modes else None

    # ── control API ────────────────────────────────────────────────────────────

    def toggle_visible(self) -> None:
        """Toggle overlay visibility (bound to Tab in main loop)."""
        self.visible = not self.visible

    def consume_changed(self) -> bool:
        """Return and clear the style/mode changed flag."""
        c = self._changed
        self._changed = False
        return c

    # ── render ─────────────────────────────────────────────────────────────────

    def render(self) -> dict[str, float]:
        """Draw the ImGui frame. Call AFTER all moderngl draws, BEFORE swap_buffers.

        Returns:
            Dict of per-sub-call timings in milliseconds:
            ``glfw_new_frame``, ``ogl_new_frame``, ``imgui_new_frame``,
            ``draw``, ``imgui_render``, ``ogl_render``.
        """
        _t = time.perf_counter
        t0 = _t()
        _imgui_backends.glfw_new_frame()
        t_glfw_new_frame = (_t() - t0) * 1000.0

        t0 = _t()
        _imgui_backends.opengl3_new_frame()
        t_ogl_new_frame = (_t() - t0) * 1000.0

        t0 = _t()
        imgui.new_frame()
        t_imgui_new_frame = (_t() - t0) * 1000.0

        t0 = _t()
        if self.visible:
            imgui.set_next_window_pos((10, 20), imgui.Cond_.first_use_ever)
            imgui.set_next_window_size((300, 600), imgui.Cond_.first_use_ever)
            imgui.begin("Parameters  [Tab]")

            self._draw_selectors()
            imgui.separator()
            self._draw_sections()

            if self._defaults_factory is not None:
                imgui.separator()
                if imgui.button("  Reset to defaults  "):
                    defaults = self._defaults_factory(self.style, self.mode)
                    for attr, val in defaults.items():
                        setattr(self._cfg, attr, val)

            imgui.end()
        t_draw = (_t() - t0) * 1000.0

        t0 = _t()
        imgui.render()
        t_imgui_render = (_t() - t0) * 1000.0

        t0 = _t()
        _imgui_backends.opengl3_render_draw_data(imgui.get_draw_data())
        t_ogl_render = (_t() - t0) * 1000.0

        return {
            "glfw_new_frame": t_glfw_new_frame,
            "ogl_new_frame":  t_ogl_new_frame,
            "imgui_new_frame": t_imgui_new_frame,
            "draw":           t_draw,
            "imgui_render":   t_imgui_render,
            "ogl_render":     t_ogl_render,
        }

    def _draw_selectors(self) -> None:
        """Style and mode combo boxes."""
        changed, new_idx = imgui.combo("Style", self._style_idx, _STYLES)
        if changed and new_idx != self._style_idx:
            self._style_idx = new_idx
            self._mode_idx = 0
            self._changed = True

        modes = _MODES_FOR.get(self.style, [])
        if modes:
            changed, new_idx = imgui.combo("Mode", self._mode_idx, modes)
            if changed and new_idx != self._mode_idx:
                self._mode_idx = new_idx
                self._changed = True

    def _draw_sections(self) -> None:
        """Collapsing section headers with sliders."""
        sections = self._sections_factory(self.style, self.mode)
        cfg = self._cfg

        for sec in sections:
            flags = imgui.TreeNodeFlags_.default_open
            if imgui.collapsing_header(sec.title, flags):
                for sdef in sec.sliders:
                    val = float(getattr(cfg, sdef.attr))
                    if sdef.int_fmt():
                        changed, nv = imgui.slider_int(
                            sdef.label, int(round(val)),
                            int(sdef.lo), int(sdef.hi),
                        )
                        if changed:
                            setattr(cfg, sdef.attr, int(nv))
                    else:
                        fmt = _fmt_to_printf(sdef.fmt)
                        changed, nv = imgui.slider_float(
                            sdef.label, val, sdef.lo, sdef.hi, format=fmt,
                        )
                        if changed:
                            setattr(cfg, sdef.attr, float(nv))

    # ── cleanup ────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Destroy the ImGui renderer and context. Call before window close."""
        _imgui_backends.opengl3_shutdown()
        _imgui_backends.glfw_shutdown()
        imgui.destroy_context()
