"""OpenGL-accelerated particle renderer using ModernGL.

Drop-in GPU replacement for BaseVisualization._render_points and fade_surface.
Uses point sprites with a soft-circle fragment shader, running on your
Quadro M1000M via the OpenGL 4.5 driver stack.

Integration
-----------
In main.py, create the window with the OPENGL flag, then attach the renderer
to BaseVisualization before instantiating any visualization:

    screen = pygame.display.set_mode(
        (cfg.width, cfg.height), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
    )
    ctx = moderngl.create_context()
    gl = GLRenderer(ctx, cfg.width, cfg.height)
    BaseVisualization.gl_renderer = gl   # all subclasses share it

No changes to any visualization class are required.
"""

import numpy as np
import moderngl


_PARTICLE_VERT = """
#version 330 core

in vec2 in_position;
in float in_brightness;
in float in_size;

out float v_brightness;
out vec2  v_center;     // screen-space center of this point (pixels)
out float v_half_size;  // half the point diameter in pixels

uniform vec2 u_resolution;

void main() {
    // Pixel coords -> NDC; flip Y (pygame top-down, GL bottom-up)
    vec2 ndc = (in_position / u_resolution) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);
    float diam = max(1.0, in_size * 2.0);
    gl_PointSize = diam;
    v_brightness = in_brightness;
    // Pass screen-space center so the fragment shader can compute its own
    // point-coord without relying on gl_PointCoord (broken under NVIDIA PRIME).
    v_center    = vec2(in_position.x, u_resolution.y - in_position.y);
    v_half_size = diam * 0.5;
}
"""

_PARTICLE_FRAG = """
#version 330 core

in float v_brightness;
in vec2  v_center;
in float v_half_size;
out vec4 fragColor;

void main() {
    // Recompute point-coord from gl_FragCoord to avoid the gl_PointCoord
    // bug present on NVIDIA PRIME render-offload (always returns vec2(0)).
    vec2 offset = gl_FragCoord.xy - v_center;
    float dist = length(offset) / v_half_size;  // 0 at centre, 1 at edge
    if (dist > 1.0) discard;
    float alpha = 1.0 - smoothstep(0.5, 1.0, dist);
    fragColor = vec4(v_brightness, v_brightness, v_brightness, alpha);
}
"""

_FADE_VERT = """
#version 330 core

in vec2 in_position;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

_FADE_FRAG = """
#version 330 core

out vec4 fragColor;
uniform float u_alpha;

void main() {
    fragColor = vec4(0.0, 0.0, 0.0, u_alpha);
}
"""

# ── overlay shaders ────────────────────────────────────────────────────────────
# Composite a pygame SRCALPHA surface (uploaded as a GL texture) on top of
# the framebuffer. Used so the settings panel appears correctly in GL mode.

_OVERLAY_VERT = """
#version 330 core

in vec2 in_position;   // NDC: full-screen quad (-1..1)
out vec2 v_uv;

void main() {
    // UV: top-left (0,0) -> bottom-right (1,1).
    // Flip Y because pygame origin is top-left; GL texture origin is bottom-left.
    v_uv = vec2(in_position.x * 0.5 + 0.5,
                1.0 - (in_position.y * 0.5 + 0.5));
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

_OVERLAY_FRAG = """
#version 330 core

in vec2 v_uv;
uniform sampler2D u_overlay;
out vec4 fragColor;

void main() {
    fragColor = texture(u_overlay, v_uv);
}
"""

# ── 2-D coloured geometry shader ──────────────────────────────────────────────
# Used for the GPU-side audio graph overlay (background rects, waveform,
# threshold lines, level bar).

_GRAPH2D_VERT = """
#version 330 core

in vec2 in_pos;
in vec4 in_col;
out vec4 v_col;
uniform vec2 u_res;

void main() {
    vec2 ndc = (in_pos / u_res) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_col = in_col;
}
"""

_GRAPH2D_FRAG = """
#version 330 core

in vec4 v_col;
out vec4 fragColor;

void main() { fragColor = v_col; }
"""


# ── module-level geometry helpers ─────────────────────────────────────────────

def _g2d_rect(
    x: float, y: float, w: float, h: float,
    col: tuple[float, float, float, float],
) -> np.ndarray:
    """Return a 4-vertex TRIANGLE_STRIP array for a filled rectangle."""
    r, g, b, a = col
    return np.array([
        [x,     y,     r, g, b, a],
        [x + w, y,     r, g, b, a],
        [x,     y + h, r, g, b, a],
        [x + w, y + h, r, g, b, a],
    ], dtype="f4")


def _g2d_hline(
    x: float, y: float, length: float,
    col: tuple[float, float, float, float],
) -> np.ndarray:
    """Return a 2-vertex LINES array for a horizontal line."""
    r, g, b, a = col
    return np.array([
        [x,          y, r, g, b, a],
        [x + length, y, r, g, b, a],
    ], dtype="f4")


def _g2d_border(
    x: float, y: float, w: float, h: float,
    col: tuple[float, float, float, float],
) -> np.ndarray:
    """Return a 4-vertex LINE_LOOP array for a rectangle outline."""
    r, g, b, a = col
    return np.array([
        [x,     y,     r, g, b, a],
        [x + w, y,     r, g, b, a],
        [x + w, y + h, r, g, b, a],
        [x,     y + h, r, g, b, a],
    ], dtype="f4")


class GLRenderer:
    """GPU particle renderer using ModernGL point sprites.

    Replaces the per-particle pygame.draw.circle loop in BaseVisualization
    with a single VBO upload + draw call per frame. The Quadro M1000M can
    sustain 500k+ particles at 60 fps through this path.

    Attributes:
        ctx: ModernGL context tied to the active OpenGL window.
        width: Current framebuffer width in pixels.
        height: Current framebuffer height in pixels.

    """

    _INITIAL_CAPACITY = 100_000  # pre-allocated particle slots

    def __init__(self, ctx: moderngl.Context, width: int, height: int):
        """Initialise shaders, VBOs, and blend state.

        Args:
            ctx: Active ModernGL context (created after pygame OPENGL window).
            width: Initial framebuffer width in pixels.
            height: Initial framebuffer height in pixels.

        """
        self.ctx = ctx
        self.width = width
        self.height = height

        # --- particle pipeline ---
        self._prog = ctx.program(
            vertex_shader=_PARTICLE_VERT,
            fragment_shader=_PARTICLE_FRAG,
        )
        self._prog["u_resolution"].value = (float(width), float(height))

        # 4 floats per particle: x, y, brightness, size
        self._vbo = ctx.buffer(reserve=self._INITIAL_CAPACITY * 4 * 4)
        self._vao = ctx.vertex_array(
            self._prog,
            [(self._vbo, "2f 1f 1f", "in_position", "in_brightness", "in_size")],
        )
        # Pre-allocated CPU-side interleaved buffer [x, y, brightness, size].
        # Avoids per-frame np.column_stack allocation and .tobytes() copy.
        self._upload_buf = np.empty((self._INITIAL_CAPACITY, 4), dtype="f4")

        # --- fade pipeline (full-screen quad, TRIANGLE_STRIP) ---
        self._fade_prog = ctx.program(
            vertex_shader=_FADE_VERT,
            fragment_shader=_FADE_FRAG,
        )
        quad = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], dtype="f4")
        self._fade_vbo = ctx.buffer(quad.tobytes())
        self._fade_vao = ctx.vertex_array(
            self._fade_prog,
            [(self._fade_vbo, "2f", "in_position")],
        )

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        ctx.enable(moderngl.PROGRAM_POINT_SIZE)

        # --- overlay pipeline (2-D pygame surface → GL texture → full-screen quad) ---
        self._overlay_prog = ctx.program(
            vertex_shader=_OVERLAY_VERT,
            fragment_shader=_OVERLAY_FRAG,
        )
        self._overlay_prog["u_overlay"].value = 0
        self._overlay_vao = ctx.vertex_array(
            self._overlay_prog,
            [(self._fade_vbo, "2f", "in_position")],  # reuse the full-screen quad
        )
        self._overlay_tex: moderngl.Texture | None = None
        self._overlay_tex_size: tuple[int, int] = (0, 0)

        # --- 2-D coloured geometry pipeline (audio graph, etc.) ---
        self._g2d_prog = ctx.program(
            vertex_shader=_GRAPH2D_VERT,
            fragment_shader=_GRAPH2D_FRAG,
        )
        self._g2d_prog["u_res"].value = (float(width), float(height))
        # Pre-allocate enough for 2*240 waveform verts + ~64 for lines/rects
        # 6 floats * 4 bytes = 24 bytes per vertex
        self._g2d_vbo = ctx.buffer(reserve=600 * 24)
        self._g2d_vao = ctx.vertex_array(
            self._g2d_prog,
            [(self._g2d_vbo, "2f 4f", "in_pos", "in_col")],
        )

        # Set the GL viewport explicitly.  Without this, the viewport inherits
        # the raw window creation size (e.g. 1920×1200 from get_video_mode()),
        # which differs from the corrected framebuffer size on rotated displays
        # (e.g. 1200×1920).  In windowed mode a VIDEORESIZE fires immediately
        # and calls resize(), hiding the bug.  In fullscreen mode no resize
        # event fires, so the wrong viewport would persist for the entire run.
        ctx.viewport = (0, 0, width, height)

    def resize(self, width: int, height: int) -> None:
        """Update viewport and projection uniform after a window resize.

        Args:
            width: New framebuffer width in pixels.
            height: New framebuffer height in pixels.

        """
        self.width = width
        self.height = height
        self.ctx.viewport = (0, 0, width, height)
        self._prog["u_resolution"].value = (float(width), float(height))
        self._g2d_prog["u_res"].value = (float(width), float(height))

    def fade(self, alpha: int) -> None:
        """Overlay a semi-transparent black quad to create motion trails.

        Equivalent to fade_surface() but executed entirely on the GPU.

        Args:
            alpha: Opacity of the black overlay (0-255). 0 = no fade /
                infinite trails. 255 = instant clear / no trails.

        """
        if alpha == 0:
            return
        self._fade_prog["u_alpha"].value = alpha / 255.0
        self._fade_vao.render(moderngl.TRIANGLE_STRIP)

    def render(
        self,
        xs: np.ndarray,
        ys: np.ndarray,
        brightness: np.ndarray,
        sizes: np.ndarray,
    ) -> None:
        """Upload particle data and draw as GPU point sprites.

        Packs xs/ys/brightness/sizes into a single interleaved float32 buffer,
        uploads it to the GPU in one call, then issues a single draw call.

        Args:
            xs: Screen-space X coordinates (pixels).
            ys: Screen-space Y coordinates (pixels).
            brightness: Per-particle brightness in [0, 1].
            sizes: Per-particle radius in pixels.

        """
        n = len(xs)
        # Grow the pre-allocated buffer only when particle count increases
        # (rare — only when the user changes num_particles via the slider).
        if n > len(self._upload_buf):
            self._upload_buf = np.empty((n * 2, 4), dtype="f4")
        buf = self._upload_buf[:n]
        buf[:, 0] = xs
        buf[:, 1] = ys
        buf[:, 2] = brightness
        buf[:, 3] = sizes
        n_bytes = buf.nbytes
        if n_bytes > self._vbo.size:
            self._vbo.orphan(n_bytes)
        # buf is a C-contiguous f4 ndarray; moderngl accepts any buffer-protocol
        # object directly, avoiding a redundant .tobytes() copy.
        self._vbo.write(buf)
        self._vao.render(moderngl.POINTS, vertices=n)

    def composite_surface(self, surf: object) -> None:
        """Composite a pygame SRCALPHA surface as a GL texture overlay.

        Call this after render() and before display.flip() to draw the
        settings panel (or any 2-D pygame content) on top of the GL scene.
        Uploads pixel data to a cached texture — no allocation if the surface
        size hasn't changed since the last call.

        Args:
            surf: A compat.Surface (PIL-backed) the same size as the window.
                  Transparent areas (alpha=0) show the underlying GL scene.

        """
        w, h = surf.get_size()
        if self._overlay_tex is None or self._overlay_tex_size != (w, h):
            if self._overlay_tex is not None:
                self._overlay_tex.release()
            self._overlay_tex = self.ctx.texture((w, h), 4)
            self._overlay_tex.filter = moderngl.NEAREST, moderngl.NEAREST
            self._overlay_tex_size = (w, h)

        # tobytes() returns raw RGBA bytes, top-to-bottom — same layout
        # as pygame.image.tobytes(surf, "RGBA", False) that this replaces.
        self._overlay_tex.write(surf.tobytes())
        self._overlay_tex.use(0)
        self._overlay_vao.render(moderngl.TRIANGLE_STRIP)

    def composite_cached(self) -> None:
        """Re-render the overlay from the cached GL texture without re-upload.

        Call this every frame when the overlay panel hasn't changed — avoids
        the ~8 MB PIL alpha_composite + tobytes() + GPU texture write that
        composite_surface() performs.
        """
        if self._overlay_tex is None:
            return
        self._overlay_tex.use(0)
        self._overlay_vao.render(moderngl.TRIANGLE_STRIP)

    # ── 2-D graph primitives ───────────────────────────────────────────────────

    def _g2d_draw(self, verts: np.ndarray, mode: int) -> None:
        """Upload and render a batch of 2-D coloured vertices."""
        data = verts.tobytes()
        n = len(data)
        if n > self._g2d_vbo.size:
            self._g2d_vbo.orphan(n)
        self._g2d_vbo.write(data)
        self._g2d_vao.render(mode, vertices=len(verts))

    def draw_audio_graph(
        self,
        history: list[float],
        threshold: float,
        current_level: float,
        px: int,
        py: int,
        *,
        gw: int = 210,
        gh: int = 80,
        bar_w: int = 8,
        bar_gap: int = 4,
        pad_x: int = 10,
        pad_y: int = 8,
        title_h: int = 18,
        max_level: float = 1.5,
        band_histories: tuple[list[float], list[float], list[float]] | None = None,
        band_levels: tuple[float, float, float] | None = None,
    ) -> None:
        """Draw the audio graph panel directly to the GL framebuffer.

        Replaces the pygame-surface path for the audio graph in GL mode.
        Uploads ~2 KB of vertex data per frame (history buffer as geometry)
        instead of a full-screen texture. The panel background, waveform,
        threshold line, and level bar are all rendered as GPU primitives.

        Args:
            history:       Smoothed RMS level history (oldest first).
            threshold:     Noise threshold value (drawn as orange line).
            current_level: Instantaneous level for the vertical bar.
            px, py:        Top-left corner of the panel in screen pixels.
            gw, gh:        Width/height of the waveform area.
            bar_w:         Width of the instantaneous level bar.
            bar_gap:       Gap between waveform area and bar.
            pad_x, pad_y:  Horizontal/vertical panel padding.
            title_h:       Height reserved for the title row.
            max_level:     Level value that maps to the top of the graph.
        """
        gx   = float(px + pad_x)
        gy   = float(py + pad_y + title_h)
        bx   = gx + gw + bar_gap
        bot  = gy + gh          # bottom y of graph area
        pw   = pad_x + gw + bar_gap + bar_w + pad_x
        ph   = pad_y + title_h + gh + pad_y

        def c(v: int) -> float:
            return v / 255.0

        # Panel background (semi-transparent dark)
        self._g2d_draw(
            _g2d_rect(px, py, pw, ph, (c(15), c(15), c(20), 0.82)),
            moderngl.TRIANGLE_STRIP,
        )

        # Graph area background
        self._g2d_draw(
            _g2d_rect(gx, gy, gw, gh, (c(20), c(20), c(30), 1.0)),
            moderngl.TRIANGLE_STRIP,
        )

        # Reference line at 1.0
        ref_y = gy + gh - 1.0 - (1.0 / max_level) * (gh - 2)
        self._g2d_draw(
            _g2d_hline(gx, ref_y, gw, (c(50), c(50), c(70), 1.0)),
            moderngl.LINES,
        )

        # Waveform: 3 overlaid coloured bands (or fall back to single broadband)
        _BAND_FILL = [
            (c(100), c(40),  c(40),  0.7),   # bass  — red
            (c(40),  c(100), c(40),  0.7),   # mid   — green
            (c(40),  c(60),  c(130), 0.7),   # treble — blue
        ]
        _BAND_EDGE = [
            (c(220), c(80),  c(80),  1.0),
            (c(80),  c(220), c(80),  1.0),
            (c(80),  c(140), c(255), 1.0),
        ]
        if band_histories is not None:
            band_data = list(band_histories)
        else:
            band_data = [history, history, history]  # fallback: all same

        for bh, fill_col, edge_col in zip(band_data, _BAND_FILL, _BAND_EDGE):
            n = len(bh)
            if n >= gw:
                samples = bh[n - gw:]
            else:
                samples = [0.0] * (gw - n) + bh

            fill: list[float] = []
            edge: list[float] = []
            fr, fg, fb, fa = fill_col
            er, eg, eb, ea = edge_col
            for i, lv in enumerate(samples):
                frac = min(lv / max_level, 1.0)
                top_y  = bot - 1.0 - frac * (gh - 1)
                edge_y = bot - 1.0 - frac * (gh - 2)
                xi = gx + i
                fill += [xi, bot,   fr, fg, fb, fa,
                         xi, top_y, fr, fg, fb, fa]
                edge += [xi, edge_y, er, eg, eb, ea]

            if fill:
                self._g2d_draw(np.array(fill, dtype="f4").reshape(-1, 6), moderngl.TRIANGLE_STRIP)
            if edge:
                self._g2d_draw(np.array(edge, dtype="f4").reshape(-1, 6), moderngl.LINE_STRIP)

        # Threshold line (orange) on waveform
        thr_y = gy + gh - 1.0 - min(threshold / max_level, 1.0) * (gh - 2)
        self._g2d_draw(
            _g2d_hline(gx, thr_y, gw, (c(220), c(150), c(40), 1.0)),
            moderngl.LINES,
        )

        # Level bars — three narrow bars, one per band
        self._g2d_draw(
            _g2d_rect(bx, gy, bar_w, gh, (c(30), c(30), c(40), 1.0)),
            moderngl.TRIANGLE_STRIP,
        )
        sub_w = (bar_w - 2) / 3.0
        bands_val = band_levels if band_levels is not None else (current_level,) * 3
        for k, (bv, edge_col) in enumerate(zip(bands_val, _BAND_EDGE)):
            fill_h = min(bv / max_level, 1.0) * (gh - 1)
            if fill_h > 0.5:
                bx_k = bx + k * sub_w
                self._g2d_draw(
                    _g2d_rect(bx_k, gy + gh - fill_h, sub_w, fill_h, edge_col),
                    moderngl.TRIANGLE_STRIP,
                )

        # Borders
        self._g2d_draw(_g2d_border(gx, gy, gw, gh, (c(60), c(60), c(80), 1.0)), moderngl.LINE_LOOP)
        self._g2d_draw(_g2d_border(bx, gy, bar_w, gh, (c(60), c(60), c(80), 1.0)), moderngl.LINE_LOOP)
        self._g2d_draw(_g2d_border(px, py, pw, ph, (c(80), c(80), c(100), 1.0)), moderngl.LINE_LOOP)
