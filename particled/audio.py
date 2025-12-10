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

    def _callback(self, indata, frames, time_, status):
        """Process incoming audio data from the microphone stream.

        This callback runs in a separate thread managed by sounddevice. It computes
        the RMS (Root Mean Square) level of the incoming audio, applies gain
        amplification, and smooths the result using exponential moving average.

        The smoothing formula: new_level = 0.85 * old_level + 0.15 * (rms * gain)
        This creates a natural response that follows audio changes without jitter.

        Args:
            indata: Input audio data array from the microphone.
            frames: Number of audio frames in this callback.
            time_: Time information structure (unused).
            status: Status flags indicating stream health (logged if present).

        Note:
            This method is called automatically by sounddevice and should not
            be invoked directly.

        """
        if status:
            # could log overruns here if you want
            pass

        # RMS of the incoming audio block
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2)) + 1e-8
        # Normalise and smooth a bit
        value = min(rms * self.cfg.audio_gain, 1.5)
        with self._lock:
            self.level = 0.85 * self.level + 0.15 * value

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

        self._stream = sd.InputStream(
            callback=self._callback,
            channels=self.cfg.channels,
            samplerate=self.cfg.sample_rate,
            blocksize=self.cfg.blocksize,
        )
        self._stream.start()

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
