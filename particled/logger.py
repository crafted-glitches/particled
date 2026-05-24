"""Per-run structured logging for freeze / performance investigation.

Creates one folder per run under logs/::

    logs/YYYY-MM-DD_HH-MM-SS/
        run.log      ← human-readable event log + spike warnings

Frame timing data is **not** written to CSV.  Only spike warnings
(any phase ≥ 50 ms) appear in run.log so the file stays compact.

At startup the log captures:
  - Python / platform / kernel version
  - CPU model, core count, max frequency
  - GPU info via ``nvidia-smi``
  - Connected displays via ``xrandr``
  - Relevant environment variables (GL / NVIDIA / PRIME)
  - Rolling FPS is tracked in memory; avg is logged at shutdown.

Freeze signatures to look for in run.log:
  - ``SPIKE swap=NNNms``   → driver prerender queue or vsync stall
  - ``SPIKE field=NNNms``  → numpy / GL particle render bottleneck
  - ``SPIKE imgui=NNNms``  → Dear ImGui render overhead
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_LOGS_DIR = Path(__file__).parent.parent / "logs"

# Environment variables worth capturing for GPU/display correlation
_ENV_KEYS = [
    "__NV_PRIME_RENDER_OFFLOAD",
    "__GLX_VENDOR_LIBRARY_NAME",
    "__GL_SYNC_TO_VBLANK",
    "__GL_YIELD",
    "__GL_MaxFramesAllowed",
    "__GL_THREADED_OPTIMIZATIONS",
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_SESSION_TYPE",
    "GDK_BACKEND",
]


def _make_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _run_cmd(args: list[str], timeout: float = 3.0) -> str:
    """Run a subprocess and return stdout, or an error string on failure."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return f"(command not found: {args[0]})"
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"
    except Exception as exc:
        return f"(error: {exc})"


class RunLogger:
    """Manages the structured text log for a single run."""

    def __init__(self) -> None:
        _LOGS_DIR.mkdir(exist_ok=True)
        self.run_id = _make_run_id()

        run_dir  = _LOGS_DIR / self.run_id
        run_dir.mkdir(exist_ok=True)
        log_path = run_dir / "run.log"

        # ── text event logger ─────────────────────────────────────────────
        self._logger = logging.getLogger(f"particled.run.{self.run_id}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        ))
        self._logger.addHandler(fh)

        # Mirror WARNING+ to stderr so critical errors surface immediately
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.WARNING)
        sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        self._logger.addHandler(sh)

        # ── rolling FPS tracking ──────────────────────────────────────────
        self._recent_frame_ms: list[float] = []
        self._frame_count: int = 0

        self.info(f"=== particled run {self.run_id} ===")
        self.info(f"Log: {log_path}")
        self._log_system_info()

    # ── delegation helpers ────────────────────────────────────────────────

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str, exc_info: bool = False) -> None:
        self._logger.error(msg, exc_info=exc_info)

    # ── system info ───────────────────────────────────────────────────────

    def _log_system_info(self) -> None:
        """Capture and log system / GPU / display context at startup."""
        self.info("── system ──────────────────────────────────────────────")

        # Python + kernel
        uname = platform.uname()
        self.info(f"Python   {sys.version.split()[0]}")
        self.info(f"Kernel   {uname.system} {uname.release} {uname.machine}")
        self.info(f"Platform {platform.platform(terse=True)}")

        # CPU
        cpu_model = platform.processor() or uname.processor or "unknown"
        cpu_cores = os.cpu_count() or "?"
        self.info(f"CPU      {cpu_model}  cores={cpu_cores}")

        # RAM (Linux /proc/meminfo)
        try:
            mem_kb = 0
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_kb = int(line.split()[1])
                        break
            self.info(f"RAM      {mem_kb // 1024} MB")
        except Exception:
            pass

        # GPU via nvidia-smi
        self.info("── gpu ─────────────────────────────────────────────────")
        smi_fields = (
            "name,driver_version,memory.total,memory.free,"
            "utilization.gpu,temperature.gpu,clocks.current.graphics,"
            "clocks.max.graphics,pcie_link_width.current"
        )
        smi = _run_cmd([
            "nvidia-smi",
            f"--query-gpu={smi_fields}",
            "--format=csv,noheader,nounits",
        ])
        if smi and "(command not found" not in smi:
            labels = [
                "name", "driver", "vram_total_mb", "vram_free_mb",
                "gpu_util_%", "temp_c", "clk_mhz", "clk_max_mhz",
                "pcie_width",
            ]
            for label, val in zip(labels, smi.split(",")):
                self.info(f"  {label:<16} {val.strip()}")
        else:
            self.info(f"  nvidia-smi: {smi}")

        # Prime sync / provider status
        providers = _run_cmd(["xrandr", "--listproviders"])
        self.info(f"  xrandr providers: {providers[:120]}")

        # Displays
        self.info("── displays ────────────────────────────────────────────")
        xrandr_out = _run_cmd(["xrandr"])
        for line in xrandr_out.splitlines():
            if " connected" in line or " disconnected" in line or "current" in line:
                self.info(f"  {line}")

        # GL / NVIDIA env vars
        self.info("── env vars ────────────────────────────────────────────")
        for key in _ENV_KEYS:
            val = os.environ.get(key, "<unset>")
            self.info(f"  {key}={val}")

        self.info("────────────────────────────────────────────────────────")

    # ── structured event helpers ──────────────────────────────────────────

    def log_config(self, cfg: object, style: str, mode: str | None) -> None:
        """Log startup configuration."""
        self.info(
            f"Config: {cfg.width}x{cfg.height} fps={cfg.fps} "
            f"particles={cfg.num_particles} use_gl={cfg.use_gl} "
            f"fullscreen={cfg.fullscreen}"
        )
        self.info(f"Style: {style!r}  Mode: {mode!r}")
        self.info(
            f"Audio: sample_rate={cfg.sample_rate} channels={cfg.channels} "
            f"blocksize={cfg.blocksize} gain={cfg.audio_gain}"
        )
        self.info(
            f"Visual: fade_alpha={cfg.fade_alpha} "
            f"brightness_gamma={cfg.brightness_gamma} "
            f"bg_color={cfg.bg_color}"
        )

    def log_audio_device(self, msg: str) -> None:
        self.info(f"[audio] {msg}")

    def log_audio_calibration(self, noise: float, peak: float, auto_gain: float) -> None:
        self.info(
            f"[audio] calibrated  noise_floor={noise:.5f}  "
            f"peak_ref={peak:.5f}  auto_gain={auto_gain:.1f}"
        )

    def log_resize(self, w: int, h: int) -> None:
        self.info(f"[event] VIDEORESIZE → {w}x{h}")

    def log_style_change(self, style: str, mode: str | None) -> None:
        self.info(f"[overlay] style/mode changed → {style!r} {mode!r}")

    def log_gl_context(self, ctx: object) -> None:
        """Log OpenGL version and renderer info from a ModernGL context."""
        try:
            self.info(f"[gl] vendor='{ctx.info['GL_VENDOR']}' "
                      f"renderer='{ctx.info['GL_RENDERER']}' "
                      f"version='{ctx.info['GL_VERSION']}'")
        except Exception as exc:
            self.warning(f"[gl] could not read GL info: {exc}")

    def log_frame(
        self,
        *,
        t_s: float,
        audio_level: float,
        t_poll_ms: float,
        t_fade_ms: float,
        t_field_ms: float,
        t_imgui_ms: float,
        t_imgui_detail: dict[str, float] | None = None,
        t_agraph_ms: float,
        t_swap_ms: float,
        t_total_ms: float,
    ) -> None:
        """Track rolling FPS and emit WARNING for any phase ≥ 50 ms."""
        self._recent_frame_ms.append(t_total_ms)
        if len(self._recent_frame_ms) > 60:
            self._recent_frame_ms.pop(0)

        phases = {
            "poll":  t_poll_ms,
            "fade":  t_fade_ms,
            "field": t_field_ms,
            "imgui": t_imgui_ms,
            "agraph": t_agraph_ms,
            "swap":  t_swap_ms,
            "TOTAL": t_total_ms,
        }
        for phase, ms in phases.items():
            if ms >= 50.0:
                self.warning(
                    f"[frame {self._frame_count}] SPIKE {phase}={ms:.1f}ms  "
                    f"(t={t_s:.2f}s  audio={audio_level:.3f})"
                )
                if phase == "imgui" and t_imgui_detail:
                    detail_str = "  ".join(
                        f"{k}={v:.1f}ms"
                        for k, v in t_imgui_detail.items()
                        if v >= 1.0
                    )
                    self.warning(
                        f"[frame {self._frame_count}] SPIKE imgui breakdown: {detail_str}"
                    )

        self._frame_count += 1

        # Flush to disk every ~120 frames so data survives a hard crash
        if self._frame_count % 120 == 0:
            for h in self._logger.handlers:
                if hasattr(h, "flush"):
                    h.flush()

    def log_shutdown(self, total_frames: int, elapsed_s: float) -> None:
        avg_fps = total_frames / elapsed_s if elapsed_s > 0 else 0.0
        avg_ms  = (
            sum(self._recent_frame_ms) / len(self._recent_frame_ms)
            if self._recent_frame_ms else 0.0
        )

        # Log a final nvidia-smi snapshot for GPU temp / util at shutdown
        smi_live = _run_cmd([
            "nvidia-smi",
            "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ])
        self.info(
            f"Shutdown: {total_frames} frames in {elapsed_s:.1f}s "
            f"→ avg {avg_fps:.1f} fps  last_60f_avg={avg_ms:.1f}ms"
        )
        if smi_live and "(command not found" not in smi_live:
            parts = [p.strip() for p in smi_live.split(",")]
            if len(parts) >= 4:
                self.info(
                    f"[gpu] shutdown snapshot  temp={parts[0]}°C  "
                    f"util={parts[1]}%  vram_used={parts[2]}MB  "
                    f"vram_free={parts[3]}MB"
                )

        for h in self._logger.handlers[:]:
            h.flush()
            h.close()
