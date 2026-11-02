"""Turn click events into success/failure labels for each pick-and-place trial.

Two plates, one piezo under each:
  ch 0 = source plate (beans start here)
  ch 1 = target plate (beans should land here)

Only "click" events count; "thud" events (a finger knocking the plate) are
dropped when the CSV is read.

A trial window comes from the teleoperation / policy log: when the hand was
told to move one bean. Rule for one trial:
  success  - exactly one click on the target plate inside the window
  dropped  - a click on the source plate after the grasp time (the bean fell back)
  double   - two or more target clicks (two beans moved, or a bounce we could not merge)
  miss     - no target click at all
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

SOURCE, TARGET = 0, 1


@dataclass
class Trial:
    trial_id: str
    t_start: float
    t_grasp: float
    t_end: float


def label_trial(trial: Trial, events) -> dict:
    tgt = [e for e in events if e["ch"] == TARGET and trial.t_start <= e["t"] <= trial.t_end]
    drop = [e for e in events if e["ch"] == SOURCE and trial.t_grasp < e["t"] <= trial.t_end]
    if drop and not tgt:
        result = "dropped"
    elif len(tgt) == 1:
        result = "success"
    elif len(tgt) >= 2:
        result = "double"
    else:
        result = "miss"
    return {"trial_id": trial.trial_id, "result": result,
            "t_land": tgt[0]["t"] if tgt else "", "n_target": len(tgt), "n_drop": len(drop)}


def read_events(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [{"ch": int(r["ch"]), "t": float(r["t"]), "peak": float(r["peak"])}
                for r in csv.DictReader(f) if r.get("kind", "click") == "click"]


def read_trials(path: str) -> list[Trial]:
    with open(path, newline="", encoding="utf-8") as f:
        return [Trial(r["trial_id"], float(r["t_start"]), float(r["t_grasp"]), float(r["t_end"]))
                for r in csv.DictReader(f)]


def main(argv=None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Label pick-and-place trials from click events.")
    ap.add_argument("events", help="events.csv from kachi_sense.logger")
    ap.add_argument("trials", help="trials.csv with trial_id,t_start,t_grasp,t_end (host seconds)")
    ap.add_argument("-o", "--out", default="labels.csv")
    a = ap.parse_args(argv)
    events = read_events(a.events)
    rows = [label_trial(t, events) for t in read_trials(a.trials)]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["trial_id"])
        w.writeheader()
        w.writerows(rows)
    ok = sum(r["result"] == "success" for r in rows)
    print(f"{len(rows)} trials, {ok} success -> {a.out}")


if __name__ == "__main__":
    main()
