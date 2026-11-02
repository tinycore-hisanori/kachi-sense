"""Run the detector on a synthetic 20-trial session and print what it finds.

    python tools/demo.py

Writes demo_events.csv, demo_trials.csv and demo_labels.csv next to you.
"""

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kachi_sense.dsp import Detector  # noqa: E402
from kachi_sense.label import Trial, label_trial  # noqa: E402
from kachi_sense.synth import plate_signal  # noqa: E402

rng = np.random.default_rng(7)
trials, src_clicks, tgt_clicks, bumps = [], [], [], []
truth = []
t = 0.5
for i in range(20):
    start, grasp, end = t, t + 0.8, t + 2.2
    outcome = rng.choice(["success", "dropped", "miss"], p=[0.7, 0.2, 0.1])
    bumps.append(start + 0.3)                      # finger touches the source plate
    if outcome == "success":
        tgt_clicks.append(grasp + rng.uniform(0.6, 1.2))
    elif outcome == "dropped":
        src_clicks.append(grasp + rng.uniform(0.1, 0.5))
    trials.append(Trial(f"trial{i:02d}", start, grasp, end))
    truth.append(outcome)
    t = end + 0.3

dur = t + 0.5
events = []
for ch, clicks, b in [(0, src_clicks, bumps), (1, tgt_clicks, [])]:
    x = plate_signal(dur, clicks, bump_times=b, seed=10 + ch)
    events += [e.as_dict() for e in Detector(ch=ch).run(x)]
events.sort(key=lambda e: e["t"])

rows = [label_trial(tr, events) for tr in trials]
agree = sum(r["result"] == want for r, want in zip(rows, truth))

with open("demo_events.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["ch", "t", "kind", "dur_ms", "peak", "energy", "ratio"])
    w.writeheader()
    w.writerows(events)
with open("demo_trials.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["trial_id", "t_start", "t_grasp", "t_end"])
    w.writerows([[tr.trial_id, tr.t_start, tr.t_grasp, tr.t_end] for tr in trials])
with open("demo_labels.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["truth"])
    w.writeheader()
    w.writerows([{**r, "truth": want} for r, want in zip(rows, truth)])

for r, want in zip(rows, truth):
    mark = "ok " if r["result"] == want else "NG "
    print(f"{mark}{r['trial_id']}  label={r['result']:<8} truth={want}")
print(f"\nauto labels agree with truth: {agree}/{len(rows)}")
