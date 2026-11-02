import numpy as np

from kachi_sense.dsp import Detector
from kachi_sense.synth import plate_signal


def match(events, truth, tol=0.006):
    hit = sum(any(abs(e.t_start - t) < tol for e in events) for t in truth)
    false = sum(not any(abs(e.t_start - t) < tol for t in truth) for e in events)
    return hit, false


def test_detects_clicks_in_hum_and_noise():
    rng = np.random.default_rng(1)
    clicks = np.sort(rng.uniform(0.2, 9.8, 40))
    clicks = clicks[np.insert(np.diff(clicks) > 0.06, 0, True)]
    x = plate_signal(10.0, clicks, seed=1)
    ev = Detector().run(x)
    hit, false = match(ev, clicks)
    assert hit >= 0.95 * len(clicks)
    assert false <= 1


def test_ignores_hand_bumps():
    bumps = [0.5, 1.5, 2.5, 3.5, 4.5]
    x = plate_signal(5.0, [], bump_times=bumps, seed=2)
    assert len(Detector().run(x)) == 0


def test_hard_knocks_are_reported_as_thuds_not_clicks():
    bumps = [0.5, 1.5, 2.5, 3.5, 4.5]
    x = plate_signal(5.0, [], bump_times=bumps, seed=2, bump_amp=(1200, 2000))
    every = Detector().run(x, clicks_only=False)
    assert every and all(e.kind == "thud" for e in every)


def test_faint_clicks_still_count():
    clicks = np.arange(0.3, 9.8, 0.25)
    x = plate_signal(10.0, clicks, seed=9, click_amp=(40, 60))
    hit, false = match(Detector().run(x), clicks)
    assert hit == len(clicks) and false == 0


def test_click_right_after_bump_still_counts():
    x = plate_signal(2.0, [1.03], bump_times=[1.0], seed=3)
    ev = Detector().run(x)
    hit, _ = match(ev, [1.03])
    assert hit == 1


def test_one_bean_one_event():
    x = plate_signal(1.0, [0.5], seed=4, click_amp=(400, 400))
    assert len(Detector().run(x)) == 1
