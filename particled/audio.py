"""Audio input processing and monitoring."""

import collections
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

    def __init__(self, cfg: Config, _run_log=None):
        """Initialize the audio meter with configuration.

        Sets up the audio processing system with thread-safe level tracking.
        Does not start audio input immediately; call start() to begin monitoring.

        Args:
            cfg: Configuration object containing audio parameters including
                sample_rate, channels, blocksize, and audio_gain.
            _run_log: Optional RunLogger instance for structured logging.

        """
        self.cfg = cfg
        self._log = _run_log
        self.level = 0.0
        self._lock = threading.Lock()
        self._stream = None
        # Set by _calibrate(); used in _callback for noise subtraction & scaling.
        self._noise_floor: float = 0.0
        self._auto_gain: float = cfg.audio_gain
        # Rolling history of smoothed levels for the audio graph (audio-thread rate).
        self._level_history: collections.deque = collections.deque(maxlen=240)
        # Per-band rolling histories for the multi-band graph
        self._bass_history:   collections.deque = collections.deque(maxlen=240)
        self._mid_history:    collections.deque = collections.deque(maxlen=240)
        self._treble_history: collections.deque = collections.deque(maxlen=240)
        # Per-band RMS levels (smoothed, updated in _callback via FFT)
        self._bass_level: float = 0.0
        self._mid_level: float = 0.0
        self._treble_level: float = 0.0
        # FFT bin slices per band — set in start() once samplerate is known
        self._bass_slice: slice = slice(0, 1)
        self._mid_slice: slice = slice(0, 1)
        self._treble_slice: slice = slice(0, 1)
        # Analysis window (Hanning) — set in start(); reduces spectral leakage
        # so bass energy doesn’t bleed into mid/treble bins.
        self._fft_window: np.ndarray | None = None

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
        gain_factor = self._auto_gain * (self.cfg.audio_gain / 50.0)
        above_noise = max(0.0, rms - self._noise_floor)
        value = min(above_noise * gain_factor, 1.5)

        # FFT band levels — collapse to mono then compute per-band RMS.
        # Parseval: band_rms = sqrt(2 * sum(|X[k]|²)) / N
        # (×2 for single-sided spectrum; DC bin is excluded from all slices)
        mono = samples[:, 0] if samples.ndim == 2 else samples
        N = len(mono)
        win = self._fft_window
        windowed = mono * win[:N] if (win is not None and len(win) >= N) else mono
        fft_mag = np.abs(np.fft.rfft(windowed))

        def _brms(s: slice) -> float:
            v = fft_mag[s]
            return float(np.sqrt(2.0 * np.dot(v, v))) / N

        bass_v   = min(_brms(self._bass_slice)   * gain_factor, 1.5)
        mid_v    = min(_brms(self._mid_slice)    * gain_factor, 1.5)
        treble_v = min(_brms(self._treble_slice) * gain_factor, 1.5)

        with self._lock:
            self.level = 0.85 * self.level + 0.15 * value
            # Bass smoothed slowly (more inertia), treble faster (transients)
            self._bass_level   = 0.80 * self._bass_level   + 0.20 * bass_v
            self._mid_level    = 0.85 * self._mid_level    + 0.15 * mid_v
            self._treble_level = 0.88 * self._treble_level + 0.12 * treble_v
            self._level_history.append(self.level)
            self._bass_history.append(self._bass_level)
            self._mid_history.append(self._mid_level)
            self._treble_history.append(self._treble_level)

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
        msg = (
            f"Audio: calibrated  noise_floor={noise:.5f}  "
            f"peak_ref={peak:.5f}  auto_gain={self._auto_gain:.1f}"
        )
        print(msg)
        if self._log is not None:
            self._log.log_audio_calibration(noise, peak, self._auto_gain)

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

        # Compute FFT band slices now that samplerate is known.
        # rfft output has blocksize//2+1 bins; bin k → frequency k*sr/blocksize.
        n_fft  = self.cfg.blocksize
        n_bins = n_fft // 2 + 1
        bass_hi   = min(int(250  * n_fft / samplerate) + 1, n_bins)
        mid_hi    = min(int(2000 * n_fft / samplerate) + 1, n_bins)
        treble_hi = min(int(8000 * n_fft / samplerate) + 1, n_bins)
        self._bass_slice   = slice(1, bass_hi)         # ~20–250 Hz  (skip DC bin 0)
        self._mid_slice    = slice(bass_hi, mid_hi)    # ~250–2000 Hz
        self._treble_slice = slice(mid_hi, treble_hi)  # ~2000–8000 Hz

        # Precompute Hanning analysis window sized to the callback block.
        self._fft_window = np.hanning(n_fft).astype("f4")

        if device is not None:
            dev_name = sd.query_devices(device)['name']
            msg = f"using device [{device}] {dev_name} @ {samplerate} Hz"
            print(f"Audio: {msg}")
            if self._log is not None:
                self._log.log_audio_device(msg)

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

    def get_band_levels(self) -> tuple[float, float, float]:
        """Return the current smoothed (bass, mid, treble) RMS levels (thread-safe).

        Returns:
            Tuple of (bass, mid, treble) levels, each in range 0.0–1.5.
            Bass covers ~20–250 Hz, mid ~250–2000 Hz, treble ~2000–8000 Hz.
        """
        with self._lock:
            return (
                float(self._bass_level),
                float(self._mid_level),
                float(self._treble_level),
            )

    def get_history(self) -> list[float]:
        """Return a snapshot of the rolling level history (thread-safe).

        Returns:
            List of smoothed RMS levels (oldest first), up to 240 entries.
            Each entry was recorded at approximately the audio callback rate
            (~43 Hz for blocksize=1024 at 44100 Hz sample rate).
        """
        with self._lock:
            return list(self._level_history)

    def get_band_histories(self) -> tuple[list[float], list[float], list[float]]:
        """Return rolling history snapshots for bass, mid, and treble (thread-safe).

        Returns:
            Tuple of (bass_history, mid_history, treble_history), each a list
            of smoothed levels (oldest first), up to 240 entries.
        """
        with self._lock:
            return (
                list(self._bass_history),
                list(self._mid_history),
                list(self._treble_history),
            )
