import math
import random
import sys
from dataclasses import dataclass

import numpy as np
import pygame
import sounddevice as sd


WIDTH, HEIGHT = 800, 800
BACKGROUND_COLOR = (0, 0, 0)

# Particle / audio settings
POINT_SPACING = 5  # grid spacing (higher = fewer particles)
BASE_RADIUS_RANGE = (1.2, 2.0)
RADIUS_BOOST_RANGE = (0.5, 1.5)
MAX_JITTER_PIXELS = 4.0
AUDIO_GAIN = 40.0  # scale factor mic loudness -> visual intensity
AUDIO_NOISE_FLOOR = 0.02  # ignore tiny background noise

audio_level = 0.0  # updated from audio callback


def audio_callback(indata, frames, time, status):
    """
    sounddevice callback: compute RMS loudness from mic input.
    """
    global audio_level
    if status:
        print(status, file=sys.stderr)
    if frames > 0:
        volume = float(np.linalg.norm(indata)) / frames
        # exponential smoothing so it feels continuous
        audio_level = 0.9 * audio_level + 0.1 * volume


def start_audio_stream():
    try:
        stream = sd.InputStream(
            channels=1,
            callback=audio_callback,
        )
        stream.start()
        return stream
    except Exception as e:
        print("Could not start audio input stream, running silently:", e)
        return None


def rotate_point(x, y, angle_rad):
    ca = math.cos(angle_rad)
    sa = math.sin(angle_rad)
    return x * ca - y * sa, x * sa + y * ca


def point_in_polygon(x, y, polygon):
    """
    Ray-casting point-in-polygon test.
    """
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-9) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


@dataclass
class Particle:
    base_x: float
    base_y: float
    side_index: int
    phase: float
    speed: float
    direction: float
    base_radius: float
    radius_boost: float


def build_penrose_polygons():
    """
    Build three '7'-shaped polygons that form a proper Penrose tribar.
    Coordinates adapted from a compact SVG Penrose path.
    """
    base_points = [
        (-53.0, -378.0),
        (53.0, -378.0),
        (354.0, 143.0),
        (-140.0, 143.0),
        (-87.0, 50.0),
        (191.0, 50.0),
    ]

    # Rotate this bar 0, 120, 240 degrees around the origin
    rotated_polys = []
    for angle_deg in (0.0, 120.0, 240.0):
        angle_rad = math.radians(angle_deg)
        poly = [rotate_point(x, y, angle_rad) for (x, y) in base_points]
        rotated_polys.append(poly)

    # Global bounding box
    xs = [x for poly in rotated_polys for (x, _) in poly]
    ys = [y for poly in rotated_polys for (_, y) in poly]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    width = max_x - min_x
    height = max_y - min_y

    # Uniform scale to fit window
    scale = 0.8 * min(WIDTH / width, HEIGHT / height)

    screen_polys = []
    for poly in rotated_polys:
        transformed = []
        for x, y in poly:
            sx = (x - cx) * scale + WIDTH / 2.0
            sy = (y - cy) * scale + HEIGHT / 2.0
            transformed.append((sx, sy))
        screen_polys.append(transformed)

    return screen_polys


def build_particles(polygons):
    particles = []

    for side_index, poly in enumerate(polygons):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        y = min_y
        while y <= max_y:
            x = min_x
            while x <= max_x:
                if point_in_polygon(x, y, poly):
                    phase = random.uniform(0.0, 2.0 * math.pi)
                    speed = random.uniform(0.4, 1.2)
                    direction = random.uniform(0.0, 2.0 * math.pi)
                    base_radius = random.uniform(*BASE_RADIUS_RANGE)
                    radius_boost = random.uniform(*RADIUS_BOOST_RANGE)
                    particles.append(
                        Particle(
                            base_x=x,
                            base_y=y,
                            side_index=side_index,
                            phase=phase,
                            speed=speed,
                            direction=direction,
                            base_radius=base_radius,
                            radius_boost=radius_boost,
                        )
                    )
                x += POINT_SPACING
            y += POINT_SPACING

    return particles


def main():
    pygame.init()
    pygame.display.set_caption("Penrose Particle Triangle (Mic Reactive)")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    polygons = build_penrose_polygons()
    particles = build_particles(polygons)

    audio_stream = start_audio_stream()

    running = True
    t = 0.0

    # Constant grey per bar for a 3-D feel, but no flicker
    side_brightness = [235, 190, 150]

    while running:
        dt = clock.tick(60) / 1000.0
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # Map audio_level -> [0, 1] with a small noise threshold
        raw = audio_level * AUDIO_GAIN
        raw = max(0.0, raw - AUDIO_NOISE_FLOOR)
        intensity = max(0.0, min(raw * 1.5, 1.0))  # clamp 0..1

        screen.fill(BACKGROUND_COLOR)

        for p in particles:
            # Always moving a bit; audio scales amplitude
            motion_amp = 0.25 + 1.75 * intensity  # 0.25 when silent, up to 2.0
            j = math.sin(p.phase + t * p.speed) * motion_amp

            dx = math.cos(p.direction) * j * MAX_JITTER_PIXELS
            dy = math.sin(p.direction) * j * MAX_JITTER_PIXELS

            px = int(p.base_x + dx)
            py = int(p.base_y + dy)

            # Radius pulses with sound, but never goes to 0 (no disappearing)
            radius = max(
                1,
                int(p.base_radius * (1.0 + p.radius_boost * intensity)),
            )

            val = side_brightness[p.side_index]
            color = (val, val, val)  # pure grayscale, no brightness modulation

            pygame.draw.circle(screen, color, (px, py), radius)

        pygame.display.flip()

    if audio_stream is not None:
        audio_stream.stop()
        audio_stream.close()
    pygame.quit()


if __name__ == "__main__":
    main()
