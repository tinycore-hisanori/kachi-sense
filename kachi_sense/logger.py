"""Read click events from the Pico over USB serial and write them to CSV.

The firmware prints one JSON object per line, e.g.
  {"ch":1,"t_us":1234567,"kind":"click","dur_ms":13.1,"peak":212.0,"energy":15320.5,"ratio":8.4}
The logger converts the board clock to host time (time.time()) so events line
up with the teleoperation log, which is stamped on the host.
"""

from __future__ import annotations

import csv
import json
import sys
import time


def run(port: str, out: str, baud: int = 115200) -> None:
    import serial  # pyserial

    offset = None
    with serial.Serial(port, baud, timeout=1) as ser, open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["ch", "t", "kind", "dur_ms", "peak", "energy", "ratio"])
        print(f"logging {port} -> {out}  (Ctrl+C to stop)", file=sys.stderr)
        while True:
            line = ser.readline().decode("utf-8", "replace").strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            board = ev["t_us"] / 1e6
            if offset is None:
                offset = time.time() - board
            t = board + offset
            w.writerow([ev["ch"], f"{t:.6f}", ev["kind"], ev["dur_ms"], ev["peak"], ev["energy"], ev["ratio"]])
            f.flush()
            plate = "TARGET" if ev["ch"] == 1 else "SOURCE"
            print(f"{plate}  {ev['kind']:<5} peak={ev['peak']:.0f} ratio={ev['ratio']:.1f}", file=sys.stderr)


def main(argv=None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Log kachi-sense click events to CSV.")
    ap.add_argument("port", help="serial port, e.g. COM5 or /dev/ttyACM0")
    ap.add_argument("-o", "--out", default="events.csv")
    a = ap.parse_args(argv)
    try:
        run(a.port, a.out)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
