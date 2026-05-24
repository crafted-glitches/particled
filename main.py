"""Audio Reactive Particle Visualizer.

A real-time particle visualization that reacts to microphone input,
featuring multiple visualization styles.
"""

from __future__ import annotations

import argparse
import os
import threading
import time

# Prefer the NVIDIA GLX driver when both nvidia and Mesa GLX are installed.
# Required on PRIME setups and harmless on single-GPU machines.
os.environ.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
# Disable driver-level vblank sync.  Belt-and-suspenders: on Wayland the
# compositor also enforces its own vsync; the real guard is the borderless-
# window path below (fake-fullscreen) which keeps frames in the compositor's
# normal composition path where swap is non-blocking.
os.environ.setdefault("__GL_SYNC_TO_VBLANK", "0")
# Ask the driver not to queue more than 1 pre-rendered frame.  Default is 2;
# the second queued frame makes swap_buffers() stall on display timing slots.
os.environ.setdefault("__GL_MaxFramesAllowed", "1")
# Force zero swap interval at the GLX application level as an additional hint
# to the driver (independent of the glXSwapInterval call from GLFW).
os.environ.setdefault("__GLX_SWAP_INTERVAL_APP", "0")
# Force the Python glfw package to load its X11/GLX variant instead of the
# Wayland/EGL one.  On Wayland sessions (XDG_SESSION_TYPE=wayland) the package
# defaults to wayland/libglfw.so, but that conflicts with the GLX-specific
# NVIDIA env vars above and also lacks glfwGetX11Window which imgui-bundle
# needs.  With x11/libglfw.so the window is created via XWayland (DISPLAY=:0)
# and is actually visible on screen.
os.environ.setdefault("PYGLFW_LIBRARY_VARIANT", "x11")

import glfw
import moderngl

from particled.audio import AudioMeter
from particled.cli import (
    configure_interactively,
    get_visualization_style,
    choose_display,
)
from particled.compat import (
    Event,
    QUIT, KEYDOWN, VIDEORESIZE,
    K_ESCAPE, K_TAB,
)
from particled.config import Config
from particled.visuals import (
    BaseVisualization,
    ParticleCloudGravitas,
    ParticleCloudImpact,
    PenroseTriangle,
    TorusKnotField,
)
from particled.visuals.gl_renderer import GLRenderer
from particled.visuals.imgui_overlay import ImguiOverlay
from particled.visuals.overlay import AudioGraph
from particled.visuals.param_panels import sections_for, defaults_for
from OpenGL.GL import glFlush

from particled.logger import RunLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_field(style: str, mode: str | None, cfg: Config):
    """Instantiate the correct visualization field."""
    if style == "Torus Knot":
        return TorusKnotField(cfg)
    elif style == "Penrose":
        return PenroseTriangle(cfg)
    elif mode == "Impact":
        return ParticleCloudImpact(cfg)
    else:
        return ParticleCloudGravitas(cfg)


class _FakeScreen:
    """Minimal surface-like wrapper around cfg dimensions for overlay sizing."""

    def __init__(self, cfg: Config):
        self._cfg = cfg

    def get_width(self) -> int:
        return self._cfg.width

    def get_height(self) -> int:
        return self._cfg.height

    def get_size(self) -> tuple[int, int]:
        return (self._cfg.width, self._cfg.height)


# ---------------------------------------------------------------------------
# GLFW event queue  (filled by callbacks, drained each frame)
# ---------------------------------------------------------------------------

_event_queue: list[Event] = []


def _key_cb(window, key, scancode, action, mods):
    if action in (glfw.PRESS, glfw.REPEAT):
        _event_queue.append(Event(type=KEYDOWN, key=key))


def _framebuffer_size_cb(window, width, height):
    _event_queue.append(Event(type=VIDEORESIZE, w=width, h=height))


def _window_close_cb(window):
    _event_queue.append(Event(type=QUIT))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


class _AsyncSwap:
    """Background-thread glfwSwapBuffers with a wall-clock timeout.

    glfwSwapBuffers on XWayland/GLX can block for 500ms–5s when the Wayland
    compositor (gnome-shell) cannot consume our frame promptly.  A block
    ≥ ~490ms triggers an i915 preemption timeout → GPU hang → system freeze.

    This class runs the swap on a dedicated daemon thread and waits at most
    _TIMEOUT_S seconds in the main loop.  If the compositor is slower than
    that, the main loop continues and the thread finishes the swap on its own;
    the next frame is still rendered and the display catches up naturally.

    glFlush() MUST be called on the main thread before invoking swap() so
    that glXSwapBuffers on the swap thread has no pending commands to flush
    (its implicit glXWaitGL becomes a no-op).  On NVIDIA/GLX Linux,
    glXSwapBuffers uses the drawable handle rather than the calling thread's
    current context, so calling it from a non-current thread is safe in
    practice after a preceding glFlush.
    """

    _TIMEOUT_S = 0.400  # < 490ms i915 preemption threshold; 90ms of headroom

    def __init__(self, window) -> None:
        self._window = window
        self._req = threading.Semaphore(0)
        self._done = threading.Event()
        self._alive = True
        self._busy = False
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.name = "swap-thread"
        self._thread.start()

    def _run(self) -> None:
        while True:
            self._req.acquire()
            if not self._alive:
                return
            glfw.swap_buffers(self._window)
            with self._lock:
                self._busy = False
                self._done.set()

    def swap(self) -> tuple[float, bool]:
        """Request a buffer swap; wait up to _TIMEOUT_S.

        Returns:
            (elapsed_ms, completed) — completed is False when the swap thread
            was still busy from a previous call (frame dropped) or when the
            timeout elapsed before the compositor acknowledged.
        """
        t0 = time.perf_counter()
        with self._lock:
            if self._busy:
                # Previous swap still pending (compositor very backed up).
                # Drop this frame rather than queuing a second blocked swap.
                return (time.perf_counter() - t0) * 1000.0, False
            self._busy = True
            self._done.clear()
        self._req.release()
        completed = self._done.wait(timeout=self._TIMEOUT_S)
        return (time.perf_counter() - t0) * 1000.0, completed

    def shutdown(self) -> None:
        """Signal the swap thread to exit and wait for it."""
        self._alive = False
        self._req.release()
        self._thread.join(timeout=2.0)


def main():
    """Run the audio reactive particle visualizer."""
    parser = argparse.ArgumentParser(description="Audio reactive particle visualizer")
    parser.add_argument(
        "-s", "--selective",
        action="store_true",
        help="Interactively select style and configure parameters before starting",
    )
    args = parser.parse_args()

    # ── Logging ───────────────────────────────────────────────────────────
    log = RunLogger()

    if args.selective:
        style = get_visualization_style()
        cfg, mode = configure_interactively(style)
    else:
        style = "Particle Cloud"
        mode = "Gravitas"
        cfg = Config()

    log.log_config(cfg, style, mode)

    # ── GLFW init ──────────────────────────────────────────────────────────
    if not glfw.init():
        raise RuntimeError("GLFW could not be initialised")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
    glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)

    caption = f"Audio Reactive Particles - {style}"
    if mode:
        caption += f" ({mode})"

    window = glfw.create_window(cfg.width, cfg.height, caption, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("GLFW window could not be created")

    glfw.make_context_current(window)
    # Disable vsync.  With NVIDIA PRIME offload the vsync signal is brokered by
    # the compositor; on dual-monitor setups (or after compositor-forced resizes)
    # glfw.swap_buffers() can block for 0.7–1.6 s waiting for a vsync that is
    # delayed by compositor load.  Frame pacing is handled by the soft sleep cap
    # below instead, which is immune to compositor stalls.
    glfw.swap_interval(0)

    # Non-blocking buffer swap: run glfwSwapBuffers on a daemon thread so the
    # main loop is never stalled longer than _AsyncSwap._TIMEOUT_S by a slow
    # compositor.  Must be created after make_context_current.
    swap_worker = _AsyncSwap(window)

    # Sync to actual framebuffer dimensions — glfw.get_video_mode() returns the
    # raw scan-out resolution which may differ from the compositor-rotated
    # framebuffer on portrait displays (e.g. NVIDIA PRIME + xrandr rotation).
    fb_w, fb_h = glfw.get_framebuffer_size(window)
    if (fb_w, fb_h) != (cfg.width, cfg.height):
        log.info(
            f"[glfw] framebuffer {fb_w}x{fb_h} differs from "
            f"video-mode {cfg.width}x{cfg.height} — using framebuffer dims"
        )
    cfg.width, cfg.height = fb_w, fb_h
    log.info(f"[glfw] window created {cfg.width}x{cfg.height} fullscreen={cfg.fullscreen}")

    # Register callbacks
    glfw.set_key_callback(window, _key_cb)
    glfw.set_framebuffer_size_callback(window, _framebuffer_size_cb)
    glfw.set_window_close_callback(window, _window_close_cb)

    # ── ModernGL + GL renderer ─────────────────────────────────────────────
    ctx = moderngl.create_context()
    log.log_gl_context(ctx)
    gl = GLRenderer(ctx, cfg.width, cfg.height)
    BaseVisualization.gl_renderer = gl

    fake_screen = _FakeScreen(cfg)

    # ── Visualization & overlay ────────────────────────────────────────────
    field = _make_field(style, mode, cfg)
    _last_num_particles = cfg.num_particles

    # ImguiOverlay must be created after make_context_current.
    # GlfwRenderer uses attach_callbacks=False so it polls GLFW state each
    # frame without interfering with our key/framebuffer callbacks.
    overlay = ImguiOverlay(
        window, cfg, style, mode,
        sections_factory=sections_for,
        defaults_factory=defaults_for,
    )
    audio_meter = AudioMeter(cfg, _run_log=log)
    audio_graph = AudioGraph(audio_meter, cfg)
    audio_graph.set_gl(gl)

    # ── Audio ──────────────────────────────────────────────────────────────
    try:
        audio_meter.start()
    except Exception as exc:
        log.error(f"Could not start audio input, continuing without it: {exc}")
        print(f"Could not start audio input, continuing without it: {exc}")

    # ── Initial clear ──────────────────────────────────────────────────────
    # poll_events first so X11/WM processes the window-map request before we
    # attempt the first swap; without this the fullscreen window may never
    # appear on screen.
    glfw.poll_events()
    ctx.clear(0.0, 0.0, 0.0)
    glfw.swap_buffers(window)

    t0 = time.perf_counter()
    target_frame_dt = 1.0 / cfg.fps

    log.info("[loop] entering main loop")

    # Pending resize state — debounce rapid VIDEORESIZE bursts (e.g. 3–4 events
    # fired in quick succession when a second monitor is connected).
    _pending_resize: tuple[int, int] | None = None
    _resize_apply_at: float = 0.0
    _RESIZE_DEBOUNCE = 0.35  # seconds to wait after last resize event

    # ── Main loop ──────────────────────────────────────────────────────────
    running = True
    loop_start = time.perf_counter()
    while running and not glfw.window_should_close(window):
        frame_start = time.perf_counter()
        t = frame_start - t0

        # ── poll events ───────────────────────────────────────────────────
        _t0 = time.perf_counter()
        glfw.poll_events()
        t_poll_ms = (time.perf_counter() - _t0) * 1000.0

        # Drain event queue
        events = _event_queue[:]
        _event_queue.clear()

        for event in events:
            if event.type == QUIT or (
                event.type == KEYDOWN and event.key == K_ESCAPE
            ):
                running = False
            elif event.type == KEYDOWN and event.key == K_TAB:
                overlay.toggle_visible()
            elif event.type == KEYDOWN and audio_graph.handle_event(event, fake_screen):
                pass
            elif event.type == VIDEORESIZE:
                # Accumulate — the same physical resize can produce 3-4 events.
                # We apply the last one only after _RESIZE_DEBOUNCE seconds.
                _pending_resize = (event.w, event.h)
                _resize_apply_at = time.perf_counter() + _RESIZE_DEBOUNCE

        # Apply debounced resize once the burst has settled
        if _pending_resize is not None and time.perf_counter() >= _resize_apply_at:
            w, h = _pending_resize
            _pending_resize = None
            log.log_resize(w, h)
            cfg.width = w
            cfg.height = h
            gl.resize(w, h)
            field = _make_field(overlay.style, overlay.mode, cfg)

        # Rebuild field when overlay style/mode selector changes
        if overlay.consume_changed():
            log.log_style_change(overlay.style, overlay.mode)
            field = _make_field(overlay.style, overlay.mode, cfg)
            _last_num_particles = cfg.num_particles

        # Rebuild field when num_particles slider changes (baked at init)
        if cfg.num_particles != _last_num_particles:
            log.debug(f"[overlay] num_particles changed to {cfg.num_particles}")
            field = _make_field(overlay.style, overlay.mode, cfg)
            _last_num_particles = cfg.num_particles

        # ── trails fade (GPU) ─────────────────────────────────────────────
        _t0 = time.perf_counter()
        gl.fade(cfg.fade_alpha)
        t_fade_ms = (time.perf_counter() - _t0) * 1000.0

        # ── draw visualization ────────────────────────────────────────────
        audio_level = audio_meter.get_level()
        audio_bands = audio_meter.get_band_levels()
        _t0 = time.perf_counter()
        field.draw(fake_screen, t, audio_level, audio_bands)
        t_field_ms = (time.perf_counter() - _t0) * 1000.0

        # ── audio graph (GPU geometry — no PIL) ──────────────────────────
        _t0 = time.perf_counter()
        audio_graph.draw(fake_screen)
        t_agraph_ms = (time.perf_counter() - _t0) * 1000.0

        # ── Dear ImGui overlay (GPU — zero CPU rasterisation) ─────────────
        # Flush particle/fade/graph commands to the GPU pipeline first.
        # Without this, opengl3_render_draw_data's VBO upload can stall
        # 500ms+ waiting for the driver to drain its pending command buffer.
        glFlush()
        _t0 = time.perf_counter()
        imgui_detail = overlay.render()
        t_imgui_ms = (time.perf_counter() - _t0) * 1000.0

        # ── swap ──────────────────────────────────────────────────────────
        # Flush all remaining GL commands so glXSwapBuffers' implicit
        # glXWaitGL is a no-op on the swap thread, then hand off.
        glFlush()
        t_swap_ms, _swap_ok = swap_worker.swap()
        if not _swap_ok:
            log.warning(
                f"[frame {log._frame_count}] swap timed out "
                f"({_AsyncSwap._TIMEOUT_S * 1000:.0f}ms cap) "
                "— frame dropped to protect compositor"
            )

        t_total_ms = (time.perf_counter() - frame_start) * 1000.0

        log.log_frame(
            t_s=t,
            audio_level=audio_level,
            t_poll_ms=t_poll_ms,
            t_fade_ms=t_fade_ms,
            t_field_ms=t_field_ms,
            t_imgui_ms=t_imgui_ms,
            t_imgui_detail=imgui_detail,
            t_agraph_ms=t_agraph_ms,
            t_swap_ms=t_swap_ms,
            t_total_ms=t_total_ms,
        )

        # Soft frame cap — clamp to target FPS without blocking on vsync
        elapsed = time.perf_counter() - frame_start
        remaining = target_frame_dt - elapsed
        if remaining > 0.001:
            time.sleep(remaining)

    # ── Cleanup ────────────────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - loop_start
    log.log_shutdown(log._frame_count, total_elapsed)
    audio_meter.stop()
    swap_worker.shutdown()
    overlay.shutdown()
    glfw.destroy_window(window)
    glfw.terminate()


if __name__ == "__main__":
    main()
