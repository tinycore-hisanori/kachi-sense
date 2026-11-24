"""Bounce mask: a bean's bounces must not count as new beans, a second bean must."""

import json
from pathlib import Path

import numpy as np

from kachi_sense.dsp import FS, BounceMask, Detector
from kachi_sense.synth import ADC_MID, bean_click

DATA = Path(__file__).parent / "data" / "bench_2026-11-24.json"


def replay(events):
    masks = {0: BounceMask(), 1: BounceMask()}
    return ["bounce" if masks[ch].judge(round(t * FS), peak) else "click" for ch, t, peak, _ in events]


def test_real_bench_logs():
    for s in json.loads(DATA.read_text())["sessions"]:
        assert replay(s["events"]) == [e[3] for e in s["events"]], s["name"]


def test_second_bean_soon_after_still_counts():
    m = BounceMask()
    assert m.judge(0, 1000.0) is False
    assert m.judge(round(0.2 * FS), 300.0) is True     # bounce: 0.3 x the landing
    assert m.judge(round(0.25 * FS), 900.0) is False   # a second bean of similar size
    assert m.judge(round(0.4 * FS), 250.0) is True     # its bounce


def _signal(parts, seconds=2.0, seed=0):
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    x = ADC_MID + rng.normal(0, 2.5, n)
    for ts, amp in parts:
        s = bean_click(rng, amp)
        i = int(ts * FS)
        x[i:i + len(s)] += s
    return np.clip(np.round(x), 0, 4095)


def test_detector_labels_bounces():
    x = _signal([(0.3, 1200), (0.45, 400), (0.6, 250), (0.75, 120), (1.6, 900)])
    kinds = [e.kind for e in Detector().run(x, clicks_only=False)]
    assert kinds == ["click", "bounce", "bounce", "bounce", "click"]


def test_clipping_is_flagged():
    x = _signal([(0.3, 2500), (1.2, 300)])
    ev = Detector().run(x, clicks_only=False)
    assert [e.clipped for e in ev] == [True, False]
