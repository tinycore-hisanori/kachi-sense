"""Draw docs/schematic.svg and docs/schematic.png.

    pip install schemdraw matplotlib
    python tools/draw_schematic.py
"""

from pathlib import Path

import matplotlib
import schemdraw
import schemdraw.elements as elm

matplotlib.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "sans-serif"]
schemdraw.config(fontsize=11, lw=1.4)
OUT = Path(__file__).resolve().parents[1] / "docs"

V3_LABEL = "3V3"


def vdd(d, x, y):
    d.add(elm.Vdd().at((x, y)).label(V3_LABEL, loc="top", ofst=0.1))


def gnd(d, x, y):
    d.add(elm.Ground().at((x, y)))


def channel(d, yc, gpio, plate, n):
    """One complete, independent channel: its own VMID divider plus the piezo front end."""
    ym = yc - 3.0                     # VMID node (y), below the signal line
    # VMID divider and its capacitor
    vdd(d, 1.2, ym + 2.6)
    d.add(elm.Resistor().at((1.2, ym + 2.6)).to((1.2, ym)).label(f"R{n}c\n10kΩ", loc="top", ofst=0.15))
    d.add(elm.Dot().at((1.2, ym)))
    d.add(elm.Resistor().at((1.2, ym)).to((1.2, ym - 2.6)).label(f"R{n}d\n10kΩ", loc="top", ofst=0.15))
    gnd(d, 1.2, ym - 2.6)
    d.add(elm.Line().at((1.2, ym)).to((4.0, ym)))
    d.add(elm.Dot().at((2.6, ym)))
    d.add(elm.Capacitor().at((2.6, ym)).to((2.6, ym - 2.6)).label(f"C{n}m\n10μF", loc="bottom", ofst=0.15))
    gnd(d, 2.6, ym - 2.6)
    d.add(elm.Label().at((1.4, ym + 0.4)).label(f"VMID{n} ≈ 1.65V", halign="left"))
    d.add(elm.Line().at((4.0, ym)).to((4.0, yc)))

    x0 = 4.0
    xa = x0 + 3.6                     # node A: piezo + / bias / series R
    xb = xa + 3.2                     # node B: ADC node
    d.add(elm.Line().at((x0, yc)).to((x0 + 0.6, yc)))
    d.add(elm.Crystal().at((x0 + 0.6, yc)).to((xa, yc))
          .label(f"PZ{n}  7BB-27-4L0\n（{plate}の裏）", loc="top", ofst=0.25))
    d.add(elm.Label().at((x0 + 0.85, yc - 0.35)).label("−"))
    d.add(elm.Label().at((xa - 0.25, yc - 0.35)).label("＋"))
    d.add(elm.Dot().at((xa, yc)))
    # 100k bias in parallel with the piezo, drawn below it
    d.add(elm.Line().at((x0 + 0.3, yc)).to((x0 + 0.3, yc - 1.6)))
    d.add(elm.Dot().at((x0 + 0.3, yc)))
    d.add(elm.Resistor().at((x0 + 0.3, yc - 1.6)).to((xa, yc - 1.6))
          .label(f"R{n}a 100kΩ", loc="bottom"))
    d.add(elm.Line().at((xa, yc - 1.6)).to((xa, yc)))
    # 10k series to node B
    d.add(elm.Resistor().at((xa, yc)).to((xb, yc)).label(f"R{n}b 10kΩ", loc="top"))
    d.add(elm.Dot().at((xb, yc)))
    # clamp to 3V3: anode at node B, cathode at 3V3
    d.add(elm.Schottky().at((xb, yc)).to((xb, yc + 2.2)).label(f"D{n}a BAT43", loc="bottom", ofst=0.15))
    vdd(d, xb, yc + 2.2)
    # clamp to GND: anode at AGND, cathode at node B
    xc = xb + 1.8
    d.add(elm.Line().at((xb, yc)).to((xc, yc)))
    d.add(elm.Dot().at((xc, yc)))
    d.add(elm.Schottky().at((xc, yc - 2.2)).to((xc, yc)).label(f"D{n}b BAT43", loc="bottom", ofst=0.15))
    gnd(d, xc, yc - 2.2)
    # anti-alias capacitor
    xd = xc + 3.2
    d.add(elm.Line().at((xc, yc)).to((xd, yc)))
    d.add(elm.Dot().at((xd, yc)))
    d.add(elm.Capacitor().at((xd, yc)).to((xd, yc - 2.2))
          .label(f"C{n} 1500pF\n（1000pFでも可）", loc="bottom", ofst=0.15))
    gnd(d, xd, yc - 2.2)
    # to the Pico pin
    d.add(elm.Line().at((xd, yc)).to((xd + 2.5, yc)))
    d.add(elm.Dot(open=True).at((xd + 2.5, yc)).label(gpio, loc="right", ofst=0.15))


Y0, Y1 = 6.0, -6.0                    # ch0 / ch1 signal lines (y)

with schemdraw.Drawing(show=False) as d:
    d.add(elm.Label().at((0, Y0 + 3.4)).label("ch0（取り出す皿）", halign="left", fontsize=13))
    channel(d, Y0, "GP26 / ADC0  31番ピン  (ch0)", "取り出す皿", 1)
    d.add(elm.Line().at((0, Y0 - 6.9)).to((24.5, Y0 - 6.9)).linestyle(":").color("gray"))
    d.add(elm.Label().at((0, Y1 + 3.4)).label("ch1（置く皿）　※ch0 とまったく同じ回路", halign="left", fontsize=13))
    channel(d, Y1, "GP27 / ADC1  32番ピン  (ch1)", "置く皿", 2)

    yn = Y1 - 7.2
    d.add(elm.Label().at((0, yn)).label(
        "3V3 = Pico 36番ピン 3V3(OUT)　／　⏚ = Pico 33番ピン AGND"
        "（Raspberry Pi Pico・Pico 2 W 共通）", halign="left"))
    d.add(elm.Label().at((0, yn - 0.6)).label(
        "PZ の − は VMID、＋ は R*a/R*b 側。D*a はカソードが 3V3、D*b はアノードが AGND。"
        "2チャンネルは完全に独立（VMID も別々）。", halign="left"))

    d.save(str(OUT / "schematic.svg"))
    d.save(str(OUT / "schematic.png"), dpi=160)

print("wrote", OUT / "schematic.svg", OUT / "schematic.png")
