"""Audio Reactive Particle Visualizer.

A real-time particle visualization that reacts to microphone input,
featuring multiple visualization styles.
"""

import os

# Disable pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from particled.audio import AudioMeter
from particled.cli import (
    configure_interactively,
    get_visualization_style,
    prompt_for_interactive_config,
)
from particled.config import Config
from particled.visuals import (
    ParticleCloudGravitas,
    ParticleCloudImpact,
    PenroseTriangle,
    TorusKnotField,
    fade_surface,
)


def main():
    """Run the audio reactive particle visualizer."""
    # Select visualization style first
    style = get_visualization_style()

    # Ask if user wants interactive configuration
    use_interactive = prompt_for_interactive_config()
    if use_interactive:
        cfg, mode = configure_interactively(style)
    else:
        cfg = Config()
        mode = "Gravitas" if style == "Particle Cloud" else None

    pygame.init()
    flags = pygame.SRCALPHA | pygame.RESIZABLE
    if cfg.fullscreen:
        flags |= pygame.FULLSCREEN

    screen = pygame.display.set_mode((cfg.width, cfg.height), flags)

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
    if style == "Torus Knot":
        field = TorusKnotField(cfg)
    elif style == "Penrose":
        field = PenroseTriangle(cfg)
    elif mode == "Impact":
        field = ParticleCloudImpact(cfg)
    else:  # Gravitas (default)
        field = ParticleCloudGravitas(cfg)

    try:
        audio_meter.start()
    except Exception as exc:
        print(f"Could not start audio input, continuing without it: {exc}")

    t0 = pygame.time.get_ticks() / 1000.0

    # initial clear
    screen.fill(cfg.bg_color)
    pygame.display.flip()

    while running:
        clock.tick(cfg.fps)
        t = pygame.time.get_ticks() / 1000.0 - t0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.VIDEORESIZE:
                cfg.width = event.w
                cfg.height = event.h
                screen = pygame.display.set_mode((cfg.width, cfg.height), flags)
                screen.fill(cfg.bg_color)
                # Rebuild visualization to apply new dimensions (keeps Penrose centered)
                if style == "Torus Knot":
                    field = TorusKnotField(cfg)
                elif style == "Penrose":
                    field = PenroseTriangle(cfg)
                elif mode == "Impact":
                    field = ParticleCloudImpact(cfg)
                else:
                    field = ParticleCloudGravitas(cfg)

        # trails fade
        fade_surface(screen, cfg.fade_alpha)

        # draw field
        audio_level = audio_meter.get_level()
        field.draw(screen, t, audio_level)

        pygame.display.flip()

    audio_meter.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
