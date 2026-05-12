"""Audio Reactive Particle Visualizer.

A real-time particle visualization that reacts to microphone input,
featuring multiple visualization styles.
"""

import argparse
import os

# Disable pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Route OpenGL to the discrete NVIDIA GPU on PRIME/Optimus systems.
# Has no effect on single-GPU machines or when already on the correct GPU.
os.environ.setdefault("__NV_PRIME_RENDER_OFFLOAD", "1")
os.environ.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")

import pygame

from particled.audio import AudioMeter
from particled.cli import (
    configure_interactively,
    get_visualization_style,
)
from particled.config import Config
from particled.visuals import (
    BaseVisualization,
    ParticleCloudGravitas,
    ParticleCloudImpact,
    PenroseTriangle,
    TorusKnotField,
    fade_surface,
)
from particled.visuals.overlay import AudioGraph
from particled.visuals.param_panels import build_overlay


def _make_field(style: str, mode: str | None, cfg):
    """Instantiate the correct visualization field."""
    if style == "Torus Knot":
        return TorusKnotField(cfg)
    elif style == "Penrose":
        return PenroseTriangle(cfg)
    elif mode == "Impact":
        return ParticleCloudImpact(cfg)
    else:
        return ParticleCloudGravitas(cfg)


def main():
    """Run the audio reactive particle visualizer."""
    parser = argparse.ArgumentParser(description="Audio reactive particle visualizer")
    parser.add_argument(
        "-s", "--selective",
        action="store_true",
        help="Interactively select style and configure parameters before starting",
    )
    args = parser.parse_args()

    if args.selective:
        style = get_visualization_style()
        cfg, mode = configure_interactively(style)
    else:
        style = "Particle Cloud"
        mode = "Gravitas"
        cfg = Config()  # already has Gravitas defaults baked in

    pygame.init()
    flags = pygame.RESIZABLE
    if cfg.fullscreen:
        flags |= pygame.FULLSCREEN

    if cfg.use_gl:
        flags |= pygame.OPENGL | pygame.DOUBLEBUF
        screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
        import moderngl
        from particled.visuals.gl_renderer import GLRenderer
        ctx = moderngl.create_context()
        gl = GLRenderer(ctx, cfg.width, cfg.height)
        BaseVisualization.gl_renderer = gl
        # Separate SRCALPHA surface for the overlay so we never blit pygame 2-D
        # content to the OpenGL framebuffer directly (that corrupts the scene).
        overlay_surf = pygame.Surface((cfg.width, cfg.height), pygame.SRCALPHA)
    else:
        screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
        gl = None
        overlay_surf = None

    # Set window caption with mode if applicable
    caption = f"Audio Reactive Particles - {style}"
    if mode:
        caption += f" ({mode})"
    pygame.display.set_caption(caption)

    clock = pygame.time.Clock()
    running = True

    # Initialize audio meter first
    audio_meter = AudioMeter(cfg)

    # Instantiate visualization based on style and mode selection
    field = _make_field(style, mode, cfg)
    _last_num_particles = cfg.num_particles

    overlay = build_overlay(cfg, style, mode)
    audio_graph = AudioGraph(audio_meter, cfg)
    if cfg.use_gl:
        audio_graph.set_gl(gl)
    # Track whether overlay_surf needs a fresh fill+draw+composite.
    # In GL mode the audio graph is drawn directly to the framebuffer so
    # overlay_surf only changes when the params panel is dirty.
    _overlay_surf_dirty = True  # force composite on first frame

    try:
        audio_meter.start()
    except Exception as exc:
        print(f"Could not start audio input, continuing without it: {exc}")

    t0 = pygame.time.get_ticks() / 1000.0

    # initial clear
    if cfg.use_gl:
        ctx.clear(0.0, 0.0, 0.0)
    else:
        screen.fill(cfg.bg_color)
    pygame.display.flip()

    while running:
        clock.tick(cfg.fps)
        t = pygame.time.get_ticks() / 1000.0 - t0

        for event in pygame.event.get():
            if overlay.handle_event(event, screen):
                continue
            if audio_graph.handle_event(event, screen):
                continue
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.VIDEORESIZE:
                cfg.width = event.w
                cfg.height = event.h
                if cfg.use_gl:
                    gl.resize(event.w, event.h)
                    overlay_surf = pygame.Surface((event.w, event.h), pygame.SRCALPHA)
                    _overlay_surf_dirty = True
                else:
                    screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
                    screen.fill(cfg.bg_color)
                field = _make_field(overlay.style, overlay.mode, cfg)

        # Rebuild field when overlay style/mode selector changes
        if overlay.consume_changed():
            field = _make_field(overlay.style, overlay.mode, cfg)
            _last_num_particles = cfg.num_particles
            _overlay_surf_dirty = True

        # Rebuild field when num_particles slider changes (baked at init)
        if cfg.num_particles != _last_num_particles:
            field = _make_field(overlay.style, overlay.mode, cfg)
            _last_num_particles = cfg.num_particles

        # trails fade
        if cfg.use_gl:
            gl.fade(cfg.fade_alpha)
        else:
            fade_surface(screen, cfg.fade_alpha)

        # draw field
        audio_level = audio_meter.get_level()
        field.draw(screen, t, audio_level)

        # overlay (Tab to toggle)
        if cfg.use_gl:
            # Only redo the expensive fill+tobytes+composite when the params
            # panel actually changed.  The audio graph draws to the framebuffer
            # directly (no overlay_surf involvement) so it never forces a re-upload.
            if overlay._dirty or _overlay_surf_dirty:
                overlay_surf.fill((0, 0, 0, 0))
                overlay.draw(screen, dest=overlay_surf)
                gl.composite_surface(overlay_surf)
                _overlay_surf_dirty = False
            else:
                # Panel unchanged: re-composite the existing texture as-is.
                overlay.draw(screen, dest=overlay_surf)  # fast cache blit
                gl.composite_surface(overlay_surf)
            audio_graph.draw(screen)  # GPU path: direct GL draw, no surface
        else:
            overlay.draw(screen)
            audio_graph.draw(screen)

        pygame.display.flip()

    audio_meter.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
