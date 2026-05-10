"""Audio input processing and monitoring."""

import threading

import numpy as np
import sounddevice as sd

from particled.config import Config


class AudioMeter:
    """Real-time audio input processor for microphone-based reactivity.

    This class manages background audio input from the system's default microphone,
    computing smoothed RMS (Root Mean Square) levels that drive visual reactivity.
    Audio processing runs in a separate thread to avoid blocking the main
    visualization loop.

    The audio meter uses exponential smoothing to create natural-feeling audio
    response without rapid flickering. Thread-safe access to the current audio
    level is provided via a lock mechanism.

    Attributes:
        cfg: Configuration object containing audio settings.
        level: Current smoothed RMS audio level (0.0-1.0+).

    Thread Safety:
        The `level` attribute is protected by `_lock` for thread-safe reads/writes
        between the audio callback thread and the main visualization thread.

    Example:
        >>> config = Config(audio_gain=50.0, sample_rate=44100)
        >>> meter = AudioMeter(config)
        >>> meter.start()
        >>> try:
        ...     while running:
        ...         audio_level = meter.get_level()
        ...         # Use audio_level for visualization
        ... finally:
        ...     meter.stop()

    """

    def __init__(self, cfg: Config):
        """Initialize the audio meter with configuration.

        Sets up the audio processing system with thread-safe level tracking.
        Does not start audio input immediately; call start() to begin monitoring.

        Args:
            cfg: Configuration object containing audio parameters including
                sample_rate, channels, blocksize, and audio_gain.

        """
        self.cfg = cfg
        self.level = 0.0
        self._lock = threading.Lock()
        self._stream = None
        # Set by _calibrate(); used in _callback for noise subtraction & scaling.
        self._noise_floor: float = 0.0
        self._auto_gain: float = cfg.audio_gain

    def _callback(self, indata, frames, time_, status):
        """Process incoming audio data from the microphone stream."""
        if status:
            pass

        # AC-couple: subtract the block mean to remove hardware DC offset.
        # Without this, a DC-biased mic (common on ALSA/PipeWire) produces an
        # RMS of ~0.6 even in silence, drowning out the actual audio signal.
        samples = indata.astype(np.float32)
        samples -= samples.mean()
        rms = float(np.sqrt(np.mean(samples ** 2)))
        # Subtract ambient noise floor, then scale by auto_gain (calibrated so
        # that a "loud" reference sound maps to ~1.0) and the user gain knob
        # (audio_gain=50 is the neutral reference, matching original default).
        above_noise = max(0.0, rms - self._noise_floor)
        value = min(above_noise * self._auto_gain * (self.cfg.audio_gain / 50.0), 1.5)
        with self._lock:
            self.level = 0.85 * self.level + 0.15 * value

    def _calibrate(self, device: int | None, samplerate: int) -> None:
        """Sample ~0.5 s of audio to measure the ambient noise floor and set
        ``_auto_gain`` so that typical loud sounds map to roughly 1.0."""
        samples: list[float] = []
        done = threading.Event()

        def probe(indata, frames, t, status):
            s = indata.astype(np.float32)
            s -= s.mean()
            rms = float(np.sqrt(np.mean(s ** 2)))
            samples.append(rms)
            if len(samples) >= 22:
                done.set()

        try:
            with sd.InputStream(
                device=device,
                callback=probe,
                channels=self.cfg.channels,
                samplerate=samplerate,
                blocksize=self.cfg.blocksize,
            ):
                done.wait(timeout=1.0)
        except Exception:
            return  # calibration failed; keep defaults

        if not samples:
            return

        noise = float(np.percentile(samples, 20))   # low percentile = noise floor
        peak = float(np.percentile(samples, 90))    # typical-loud reference

        self._noise_floor = noise
        reference = max(peak - noise, noise * 2, 1e-5)
        # auto_gain maps (above-noise loud sound) → 1.0
        self._auto_gain = min(1.0 / reference, 500.0)
        print(
            f"Audio: calibrated  noise_floor={noise:.5f}  "
            f"peak_ref={peak:.5f}  auto_gain={self._auto_gain:.1f}"
        )

    def start(self):
        """Start the audio input stream and begin monitoring.

        Opens an input stream on the default audio device using the configuration
        parameters (sample rate, channels, blocksize). The stream runs continuously
        in the background, calling the _callback method for each audio buffer.

        Raises:
            sounddevice.PortAudioError: If the audio device cannot be opened.
            OSError: If no audio input devices are available.

        Note:
            Call stop() before exiting to properly close the audio stream.
            Failing to do so may leave audio resources locked.

        """
        if self._stream is not None:
            return

        device, samplerate = self._choose_device()
        if device is not None:
            print(f"Audio: using device [{device}] {sd.query_devices(device)['name']} @ {samplerate} Hz")

        self._calibrate(device, samplerate)

        self._stream = sd.InputStream(
            device=device,
            callback=self._callback,
            channels=self.cfg.channels,
            samplerate=samplerate,
            blocksize=self.cfg.blocksize,
        )
        self._stream.start()

    @staticmethod
    def _choose_device() -> tuple[int | None, int]:
        """Pick the best available input device and its preferred sample rate.

        On PipeWire systems the generic 'default' / 'pipewire' ALSA devices
        often return silent data even when audio is present.  The named
        ``alsa_input.*`` entries exposed by PipeWire work reliably.

        Priority:
          1. PipeWire ALSA input  (``alsa_input.*``)
          2. Any non-monitor hardware input that isn't a virtual proxy
          3. sounddevice default (``None``)

        Returns:
            Tuple of (device_index_or_None, sample_rate).
        """
        try:
            devices = sd.query_devices()

            # Priority 1: PipeWire-managed hardware input
            for d in devices:
                if d["max_input_channels"] > 0 and d["name"].startswith("alsa_input."):
                    return d["index"], int(d["default_samplerate"])

            # Priority 2: non-virtual, non-monitor hardware input
            skip = {"default", "sysdefault", "pipewire", "pulse", "dmix", "dsnoop"}
            for d in devices:
                name_lower = d["name"].lower()
                if (
                    d["max_input_channels"] > 0
                    and "monitor" not in name_lower
                    and not any(s in name_lower for s in skip)
                ):
                    return d["index"], int(d["default_samplerate"])
        except Exception:
            pass

        return None, 44100  # fall back to sounddevice default

    def stop(self):
        """Stop the audio input stream and release resources.

        Closes the audio stream and frees the associated audio device resources.
        This method is idempotent; calling it multiple times is safe.

        Should be called before application exit to ensure clean shutdown.

        """
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_level(self) -> float:
        """Retrieve the current smoothed audio level in a thread-safe manner.

        Returns the most recent RMS level computed by the audio callback thread,
        multiplied by the configured gain factor. The value is protected by a
        lock to ensure thread-safe access from the main visualization loop.

        Returns:
            Current smoothed RMS audio level, typically in range 0.0-2.0 but
            can exceed this range with very loud input or high gain settings.
            A value of 0.0 indicates silence, while 1.0 represents moderate
            audio input at default gain.

        Thread Safety:
            This method is safe to call from any thread, including the main
            visualization loop while audio processing runs in the background.

        """
        with self._lock:
            return float(self.level)
