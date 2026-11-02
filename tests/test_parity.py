"""The firmware detector (C++) must find the same events as the Python reference."""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from kachi_sense.dsp import FS, Detector
from kachi_sense.synth import plate_signal

HERE = Path(__file__).parent


@pytest.mark.skipif(shutil.which("g++") is None, reason="needs g++")
def test_cpp_matches_python(tmp_path):
    exe = tmp_path / "parity"
    subprocess.run(["g++", "-O2", "-std=c++17", str(HERE / "parity_main.cpp"), "-o", str(exe)], check=True)
    x = plate_signal(4.0, [0.4, 1.1, 2.03, 3.3], bump_times=[1.0, 2.0, 2.9], seed=11,
                     bump_amp=(800, 1500))
    feed = "".join(f"0 {int(v)}\n" for v in x)
    out = subprocess.run([str(exe)], input=feed, capture_output=True, text=True, check=True).stdout
    cpp = [(int(n), k) for _, n, k, _ in (line.split() for line in out.splitlines())]
    py = [(round(e.t_start * FS), e.kind) for e in Detector().run(x, clicks_only=False)]
    assert cpp == py
    assert sum(k == "click" for _, k in py) == 4
