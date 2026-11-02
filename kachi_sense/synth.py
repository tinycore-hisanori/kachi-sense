"""Synthetic plate signals, so the detector can be tuned and tested with no hardware.

A bean landing on a hard plate rings at a few kHz and dies in a couple of ms.
The things we must not count are slower: motor hum from the hand and the
low thud when a finger bumps the plate.
"""

from __future__ import annotations

import numpy as np

from .dsp import FS

ADC_MID = 2048.0


def bean_click(rng: np.random.Generator, amp: float) -> np.ndarray:
    f = rng.uniform(2500, 6000)
    tau = rng.uniform(0.0008, 0.0025)
    t = np.arange(int(FS * 0.008)) / FS
    return amp * np.exp(-t / tau) * np.sin(2 * np.pi * f * t + rng.uniform(0, np.pi))


def hand_bump(rng: np.random.Generator, amp: float) -> np.ndarray:
    f = rng.uniform(60, 180)
    t = np.arange(int(FS * 0.06)) / FS
    return amp * np.exp(-t / 0.02) * np.sin(2 * np.pi * f * t)


def plate_signal(seconds: float, click_times, bump_times=(), seed: int = 0,
                 click_amp=(60, 400), bump_amp=(150, 600), noise=2.5, hum=6.0):
    """Return raw ADC counts (float) for one plate."""
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    t = np.arange(n) / FS
    x = ADC_MID + rng.normal(0, noise, n)
    x += hum * np.sin(2 * np.pi * 100 * t) + hum * 0.5 * np.sin(2 * np.pi * 150 * t + 1)
    for ts in click_times:
        s = bean_click(rng, rng.uniform(*click_amp))
        i = int(ts * FS)
        x[i:i + len(s)] += s[: max(0, n - i)]
    for ts in bump_times:
        s = hand_bump(rng, rng.uniform(*bump_amp))
        i = int(ts * FS)
        x[i:i + len(s)] += s[: max(0, n - i)]
    return np.clip(np.round(x), 0, 4095)
