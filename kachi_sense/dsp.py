"""Click detector: the reference implementation.

The firmware (firmware/kachi_sense_pico/detector.h) runs the same algorithm
sample by sample on the RP2040. Keep the two in step: tests/test_dsp.py
exercises this version, and the constants below are the ones the firmware uses.

Signal chain per channel:
  raw ADC -> remove slow DC (EMA, 0.5 s)
          -> high band: 2nd-order Butterworth high-pass at 1.5 kHz
             -> peak-hold envelope (instant attack, ~5 ms release)
             -> adaptive noise floor (slow EMA, frozen during an event)
             -> trigger when envelope > max(floor * K_ON, MIN_ABS)
             -> event ends when envelope < floor * K_OFF for HOLD_MS, or MAX_MS passes
             -> refractory period so one bean gives one event
          -> low band: two 1st-order low-passes at 400 Hz, peak tracked during the event
  An event is a "click" (a bean landing) when its high-band peak is at least
  CLICK_RATIO times its low-band peak; otherwise it is a "thud" (a finger or
  the hand knocking the plate), which has its energy down low.

Bounce mask (a decaying peak-hold on accepted clicks):
  A bean bounces a few times after landing, 70-430 ms apart, each bounce at
  0.14-0.54 of the landing peak (measured on the v2 x11 board). After a click
  with peak P at time t0, a later click-like event at time t only counts as a
  new bean when its peak exceeds MASK_K * P * exp(-(t - t0) / MASK_TAU_S);
  otherwise it is a "bounce". Bounces do not move the mask.

Clipping: an event is marked clipped when the raw ADC touched CLIP_LO / CLIP_HI
  (the op-amp hit a rail). Logged only for now; the ratio of a clipped event
  reads low because the flattened tops add low-band energy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

FS = 20_000          # samples per second, per channel
HPF_HZ = 1500.0      # bean clicks ring at 2-6 kHz; hum and thuds sit far below
LPF_HZ = 400.0       # low band used to recognise thuds
ENV_RELEASE_MS = 5.0
FLOOR_TC_S = 0.5
DC_TC_S = 0.5
K_ON = 6.0
K_OFF = 2.5
MIN_ABS = 12.0       # ADC counts; ignore anything smaller even in silence
HOLD_MS = 4.0
MAX_MS = 60.0
REFRACTORY_MS = 40.0
CLICK_RATIO = 2.0    # measured on synthetic data: clicks >= 3.5, thuds <= 1.3
WARMUP_MS = 50.0
MASK_K = 0.7         # a new bean must beat 0.7 x the last landing peak ...
MASK_TAU_S = 1.0     # ... decaying with this time constant
CLIP_LO = 8.0        # raw ADC counts treated as the op-amp rails
CLIP_HI = 4087.0


@dataclass
class Event:
    ch: int
    t_start: float      # seconds from the start of the stream
    dur_ms: float
    peak: float         # peak of the high band, ADC counts
    energy: float       # sum of squares of the high band over the event
    lf_peak: float      # peak of the low band over the event
    bounce: bool = False   # click-like, but under the bounce mask of the last click
    clipped: bool = False  # the raw ADC hit a rail during the event

    @property
    def ratio(self) -> float:
        return self.peak / (self.lf_peak + 1.0)

    @property
    def is_click_like(self) -> bool:
        return self.ratio >= CLICK_RATIO

    @property
    def kind(self) -> str:
        if not self.is_click_like:
            return "thud"
        return "bounce" if self.bounce else "click"

    def as_dict(self) -> dict:
        return {"ch": self.ch, "t": round(self.t_start, 6), "kind": self.kind,
                "dur_ms": round(self.dur_ms, 2), "peak": round(self.peak, 1),
                "energy": round(self.energy, 1), "ratio": round(self.ratio, 2),
                "clipped": self.clipped}


class BounceMask:
    """Decaying peak-hold over accepted clicks. Same rule as ks::BounceMask in detector.h."""

    def __init__(self, fs: int = FS, k: float = MASK_K, tau_s: float = MASK_TAU_S) -> None:
        self.fs, self.k, self.tau_n = fs, k, tau_s * fs
        self.peak = 0.0
        self.n = 0
        self.armed = False

    def level(self, n: int) -> float:
        if not self.armed:
            return 0.0
        return self.k * self.peak * math.exp(-(n - self.n) / self.tau_n)

    def judge(self, n: int, peak: float) -> bool:
        """Feed a click-like event starting at sample n. Returns True if it is a bounce."""
        if peak < self.level(n):
            return True
        self.peak, self.n, self.armed = peak, n, True
        return False


class Detector:
    def __init__(self, ch: int = 0, fs: int = FS, k_on: float = K_ON,
                 k_off: float = K_OFF, min_abs: float = MIN_ABS) -> None:
        self.ch, self.fs, self.k_on, self.k_off, self.min_abs = ch, fs, k_on, k_off, min_abs
        # RBJ cookbook high-pass, Q = 1/sqrt(2)
        w0 = 2 * math.pi * HPF_HZ / fs
        al = math.sin(w0) / math.sqrt(2)
        c = math.cos(w0)
        a0 = 1 + al
        self.b0, self.b1, self.b2 = (1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0
        self.a1, self.a2 = -2 * c / a0, (1 - al) / a0
        self.lp_a = 1 - math.exp(-2 * math.pi * LPF_HZ / fs)
        self.dc_a = 1.0 / (fs * DC_TC_S)
        self.rel = math.exp(-1.0 / (fs * ENV_RELEASE_MS / 1000.0))
        self.floor_a = 1.0 / (fs * FLOOR_TC_S)
        self.hold = int(fs * HOLD_MS / 1000.0)
        self.max_len = int(fs * MAX_MS / 1000.0)
        self.refr = int(fs * REFRACTORY_MS / 1000.0)
        self.warmup = int(fs * WARMUP_MS / 1000.0)

        self.n = 0
        self.dc = None
        self.z1 = self.z2 = 0.0
        self.lp1 = self.lp2 = 0.0
        self.env = 0.0
        self.floor = 0.0
        self.in_event = False
        self.ev_start = 0
        self.ev_peak = self.ev_energy = self.ev_lf = 0.0
        self.below = 0
        self.quiet_until = 0
        self.ev_clip = False
        self.mask = BounceMask(fs)

    def push(self, x: float) -> Event | None:
        """Feed one raw ADC sample. Returns an Event when one finishes."""
        n = self.n
        self.n += 1
        if self.dc is None:
            self.dc = x
        self.dc += (x - self.dc) * self.dc_a
        v = x - self.dc

        y = self.b0 * v + self.z1                  # high band, transposed direct form II
        self.z1 = self.b1 * v - self.a1 * y + self.z2
        self.z2 = self.b2 * v - self.a2 * y
        self.lp1 += (v - self.lp1) * self.lp_a     # low band
        self.lp2 += (self.lp1 - self.lp2) * self.lp_a

        a = abs(y)
        self.env = a if a > self.env else self.env * self.rel

        if n < self.warmup:                        # let the filters settle, learn the floor
            self.floor += (self.env - self.floor) * 0.02
            return None

        if not self.in_event:
            on = max(self.floor * self.k_on, self.min_abs)
            if self.env > on and n >= self.quiet_until:
                self.in_event = True
                self.ev_start, self.below = n, 0
                self.ev_peak = self.ev_energy = self.ev_lf = 0.0
                self.ev_clip = False
            else:
                self.floor += (self.env - self.floor) * self.floor_a
                return None

        self.ev_peak = max(self.ev_peak, a)
        self.ev_energy += y * y
        self.ev_lf = max(self.ev_lf, abs(self.lp2))
        if x <= CLIP_LO or x >= CLIP_HI:
            self.ev_clip = True
        off = max(self.floor * self.k_off, self.min_abs * 0.5)
        self.below = self.below + 1 if self.env < off else 0
        length = n - self.ev_start + 1
        if self.below >= self.hold or length >= self.max_len:
            self.in_event = False
            self.quiet_until = n + self.refr
            ev = Event(self.ch, self.ev_start / self.fs, length * 1000.0 / self.fs,
                       self.ev_peak, self.ev_energy, self.ev_lf, clipped=self.ev_clip)
            if ev.is_click_like:
                ev.bounce = self.mask.judge(self.ev_start, self.ev_peak)
            return ev
        return None

    def run(self, samples, clicks_only: bool = True) -> list[Event]:
        out = []
        for x in samples:
            ev = self.push(float(x))
            if ev and (ev.kind == "click" or not clicks_only):
                out.append(ev)
        return out
