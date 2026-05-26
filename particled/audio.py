"""Audio input processing and monitoring."""

import collections
import threading

import numpy as np
import sounddevice as sd

from particled.config import Config


class AudioMeter:
    """Real-time audio input processor for microphone-based reactivity."""

    def __init__(self, cfg: Config, _run_log=None):
        """Initialize the audio meter with configuration."""
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
        self._bass_history: collections.deque = collections.deque(maxlen=240)
        self._mid_history: collections.deque = collections.deque(maxlen=240)
        self._treble_history: collections.deque = collections.deque(maxlen=240)

        # Legacy 3-band levels for graph + compatibility.
        self._bass_level: float = 0.0
        self._mid_level: float = 0.0
        self._treble_level: float = 0.0
        self._bass_slice: slice = slice(0, 1)
        self._mid_slice: slice = slice(0, 1)
        self._treble_slice: slice = slice(0, 1)

        # Expanded multiband analysis (log-spaced).
        self._n_bands: int = max(3, int(cfg.audio_band_count))
        self._multiband_levels = np.zeros(self._n_bands, dtype=np.float32)
        self._multiband_histories: list[collections.deque] = [
            collections.deque(maxlen=240) for _ in range(self._n_bands)
        ]
        self._band_bounds: list[tuple[int, int]] = []
        self._analysis_lo_hz: float = cfg.audio_analysis_min_hz
        self._analysis_hi_hz: float = cfg.audio_analysis_max_hz

        # Transient + timbre features.
        self._transient_level: float = 0.0
        self._spectral_centroid_norm: float = 0.0
        self._prev_fft_mag: np.ndarray | None = None
        self._fft_freqs: np.ndarray | None = None

        # Analysis window (Hanning) - set in start().
        self._fft_window: np.ndarray | None = None

    def _callback(self, indata, frames, time_, status):
        """Process incoming audio data from the microphone stream."""
        if status:
            pass

        # AC-couple: subtract the block mean to remove hardware DC offset.
        samples = indata.astype(np.float32)
        samples -= samples.mean()
        rms = float(np.sqrt(np.mean(samples ** 2)))
        gain_factor = self._auto_gain * (self.cfg.audio_gain / 50.0)
        above_noise = max(0.0, rms - self._noise_floor)
        value = min(above_noise * gain_factor, 1.5)

        mono = samples[:, 0] if samples.ndim == 2 else samples
        N = len(mono)
        win = self._fft_window
        windowed = mono * win[:N] if (win is not None and len(win) >= N) else mono
        fft_mag = np.abs(np.fft.rfft(windowed))
        power = fft_mag * fft_mag

        def _brms(s: slice) -> float:
            v = fft_mag[s]
            if len(v) == 0:
                return 0.0
            return float(np.sqrt(2.0 * np.dot(v, v))) / N

        bass_v = min(_brms(self._bass_slice) * gain_factor, 1.5)
        mid_v = min(_brms(self._mid_slice) * gain_factor, 1.5)
        treble_v = min(_brms(self._treble_slice) * gain_factor, 1.5)

        # Build cumulative sum so any band energy can be read in O(1).
        csum = np.concatenate(([0.0], np.cumsum(power)))
        raw_bands = np.zeros(self._n_bands, dtype=np.float32)
        for i, (lo, hi) in enumerate(self._band_bounds):
            e = csum[hi] - csum[lo]
            raw_bands[i] = min(float(np.sqrt(2.0 * max(e, 0.0))) / N * gain_factor, 1.5)

        # Lower bands move heavier; upper bands react faster.
        # Keep this conservative to preserve graceful motion.
        alpha = np.linspace(0.08, 0.20, self._n_bands, dtype=np.float32)

        # Soft-knee compression keeps details from many bands while limiting
        # abrupt spikes that make particle motion feel jumpy.
        raw_bands = np.tanh(raw_bands * 1.1)

        # Positive spectral flux = transient/onset signal.
        if self._prev_fft_mag is None:
            flux = 0.0
        else:
            diff = fft_mag - self._prev_fft_mag
            pos = diff[diff > 0.0]
            prev_sum = float(self._prev_fft_mag.sum())
            flux = float(pos.sum()) / max(prev_sum, 1e-6)
        self._prev_fft_mag = fft_mag

        transient_raw = min(flux * self.cfg.audio_transient_sensitivity * 2.5, 1.0)

        # Spectral centroid (normalised) tracks timbral brightness.
        centroid_norm = 0.0
        if self._fft_freqs is not None:
            p_sum = float(power.sum())
            if p_sum > 1e-9:
                centroid_hz = float(np.dot(self._fft_freqs, power) / p_sum)
                span = max(self._analysis_hi_hz - self._analysis_lo_hz, 1.0)
                centroid_norm = np.clip(
                    (centroid_hz - self._analysis_lo_hz) / span,
                    0.0,
                    1.0,
                )

        with self._lock:
            self.level = 0.88 * self.level + 0.12 * value
            self._bass_level = 0.86 * self._bass_level + 0.14 * bass_v
            self._mid_level = 0.88 * self._mid_level + 0.12 * mid_v
            self._treble_level = 0.90 * self._treble_level + 0.10 * treble_v

            self._multiband_levels = (1.0 - alpha) * self._multiband_levels + alpha * raw_bands
            for i, h in enumerate(self._multiband_histories):
                h.append(float(self._multiband_levels[i]))

            self._transient_level = 0.82 * self._transient_level + 0.18 * transient_raw
            self._spectral_centroid_norm = (
                0.94 * self._spectral_centroid_norm + 0.06 * centroid_norm
            )

            self._level_history.append(self.level)
            self._bass_history.append(self._bass_level)
            self._mid_history.append(self._mid_level)
            self._treble_history.append(self._treble_level)

    def _calibrate(self, device: int | None, samplerate: int) -> None:
        """Sample ~0.5 s of audio to measure noise floor and auto-gain."""
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
            return

        if not samples:
            return

        noise = float(np.percentile(samples, 20))
        peak = float(np.percentile(samples, 90))

        self._noise_floor = noise
        reference = max(peak - noise, noise * 2, 1e-5)
        self._auto_gain = min(1.0 / reference, 500.0)
        msg = (
            f"Audio: calibrated  noise_floor={noise:.5f}  "
            f"peak_ref={peak:.5f}  auto_gain={self._auto_gain:.1f}"
        )
        print(msg)
        if self._log is not None:
            self._log.log_audio_calibration(noise, peak, self._auto_gain)

    def start(self):
        """Start the audio input stream and begin monitoring."""
        if self._stream is not None:
            return

        device, samplerate = self._choose_device()

        n_fft = self.cfg.blocksize
        n_bins = n_fft // 2 + 1
        self._fft_freqs = np.fft.rfftfreq(n_fft, d=1.0 / samplerate).astype(np.float32)

        # Legacy 3-band slices for existing graph and fallback mapping.
        bass_hi = min(int(250 * n_fft / samplerate) + 1, n_bins)
        mid_hi = min(int(2000 * n_fft / samplerate) + 1, n_bins)
        treble_hi = min(int(8000 * n_fft / samplerate) + 1, n_bins)
        self._bass_slice = slice(1, bass_hi)
        self._mid_slice = slice(bass_hi, mid_hi)
        self._treble_slice = slice(mid_hi, treble_hi)

        nyq = 0.5 * float(samplerate)
        lo_hz = float(np.clip(self.cfg.audio_analysis_min_hz, 20.0, nyq * 0.8))
        hi_hz = float(np.clip(self.cfg.audio_analysis_max_hz, lo_hz + 50.0, nyq * 0.98))
        self._analysis_lo_hz = lo_hz
        self._analysis_hi_hz = hi_hz

        edges = np.geomspace(lo_hz, hi_hz, self._n_bands + 1)
        freqs = self._fft_freqs if self._fft_freqs is not None else np.zeros(1)
        bounds: list[tuple[int, int]] = []
        for i in range(self._n_bands):
            lo = int(np.searchsorted(freqs, edges[i], side="left"))
            hi = int(np.searchsorted(freqs, edges[i + 1], side="right"))
            lo = max(1, min(lo, n_bins - 1))
            hi = max(lo + 1, min(hi, n_bins))
            bounds.append((lo, hi))
        self._band_bounds = bounds

        self._fft_window = np.hanning(n_fft).astype("f4")

        if device is not None:
            dev_name = sd.query_devices(device)["name"]
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
        """Pick the best available input device and its preferred sample rate."""
        try:
            devices = sd.query_devices()

            for d in devices:
                if d["max_input_channels"] > 0 and d["name"].startswith("alsa_input."):
                    return d["index"], int(d["default_samplerate"])

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

        return None, 44100

    def stop(self):
        """Stop the audio input stream and release resources."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_level(self) -> float:
        """Retrieve the current smoothed audio level in a thread-safe manner."""
        with self._lock:
            return float(self.level)

    def get_band_levels(self) -> tuple[float, float, float]:
        """Return the current smoothed (bass, mid, treble) levels."""
        with self._lock:
            return (
                float(self._bass_level),
                float(self._mid_level),
                float(self._treble_level),
            )

    def get_multiband_levels(self) -> tuple[float, ...]:
        """Return log-spaced multiband levels as a tuple."""
        with self._lock:
            return tuple(float(v) for v in self._multiband_levels)

    def get_features(self) -> dict:
        """Return a compact audio feature payload for visualization mapping."""
        with self._lock:
            return {
                "bands": tuple(float(v) for v in self._multiband_levels),
                "transient": float(self._transient_level),
                "centroid": float(self._spectral_centroid_norm),
            }

    def get_history(self) -> list[float]:
        """Return a snapshot of the rolling level history (thread-safe)."""
        with self._lock:
            return list(self._level_history)

    def get_band_histories(self) -> tuple[list[float], list[float], list[float]]:
        """Return rolling history snapshots for bass, mid, and treble."""
        with self._lock:
            return (
                list(self._bass_history),
                list(self._mid_history),
                list(self._treble_history),
            )
