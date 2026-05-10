"""Audio Reactive Particle Visualizer.

A real-time particle visualization that reacts to microphone input,
featuring multiple visualization styles.
"""

import argparse
import os

# Disable pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

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
    else:
        screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
        gl = None

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
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.VIDEORESIZE:
                cfg.width = event.w
                cfg.height = event.h
                if cfg.use_gl:
                    gl.resize(event.w, event.h)
                else:
                    screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
                    screen.fill(cfg.bg_color)
                field = _make_field(overlay.style, overlay.mode, cfg)

        # Rebuild field when overlay style/mode selector changes
        if overlay.consume_changed():
            field = _make_field(overlay.style, overlay.mode, cfg)
            _last_num_particles = cfg.num_particles

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
        overlay.draw(screen)

        pygame.display.flip()

    audio_meter.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
