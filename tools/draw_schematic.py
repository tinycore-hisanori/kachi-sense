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

TOP, VMID, GND = 6.0, 3.0, -1.0      # 3V3 rail, mid-rail, AGND rail (y)
X_END = 25.0


def channel(d, x0, gpio, plate, n):
    """One piezo channel hanging off the VMID bus at x0."""
    xa = x0 + 3.6                     # node A: piezo + / bias / series R
    xb = xa + 3.2                     # node B: ADC node
    # VMID bus out to the piezo minus side
    d.add(elm.Line().at((x0, VMID)).to((x0 + 0.6, VMID)))
    d.add(elm.Crystal().at((x0 + 0.6, VMID)).to((xa, VMID))
          .label(f"PZ{n}  7BB-27-4L0\n（{plate}の裏）", loc="top", ofst=0.25))
    d.add(elm.Label().at((x0 + 0.85, VMID - 0.35)).label("−"))
    d.add(elm.Label().at((xa - 0.25, VMID - 0.35)).label("＋"))
    d.add(elm.Dot().at((xa, VMID)))
    # 100k bias in parallel with the piezo, drawn below it
    d.add(elm.Line().at((x0 + 0.3, VMID)).to((x0 + 0.3, VMID - 1.6)))
    d.add(elm.Dot().at((x0 + 0.3, VMID)))
    d.add(elm.Resistor().at((x0 + 0.3, VMID - 1.6)).to((xa, VMID - 1.6))
          .label(f"R{n}a 100kΩ", loc="bottom"))
    d.add(elm.Line().at((xa, VMID - 1.6)).to((xa, VMID)))
    # 10k series to node B
    d.add(elm.Resistor().at((xa, VMID)).to((xb, VMID)).label(f"R{n}b 10kΩ", loc="top"))
    d.add(elm.Dot().at((xb, VMID)))
    # clamp to 3V3: anode at node B, cathode at 3V3
    d.add(elm.Schottky().at((xb, VMID)).to((xb, TOP)).label(f"D{n}a BAT43", loc="bottom", ofst=0.15))
    d.add(elm.Dot().at((xb, TOP)))
    # clamp to GND: anode at AGND, cathode at node B
    xc = xb + 1.6
    d.add(elm.Line().at((xb, VMID)).to((xc, VMID)))
    d.add(elm.Dot().at((xc, VMID)))
    d.add(elm.Schottky().at((xc, GND)).to((xc, VMID)).label(f"D{n}b BAT43", loc="bottom", ofst=0.15))
    d.add(elm.Dot().at((xc, GND)))
    # anti-alias capacitor
    xd = xc + 3.2
    d.add(elm.Line().at((xc, VMID)).to((xd, VMID)))
    d.add(elm.Dot().at((xd, VMID)))
    d.add(elm.Capacitor().at((xd, VMID)).to((xd, GND)).label(f"C{n} 1500pF", loc="bottom", ofst=0.15))
    d.add(elm.Dot().at((xd, GND)))
    # to the Pico pin
    d.add(elm.Line().at((xd, VMID)).to((xd + 2.5, VMID)))
    d.add(elm.Dot(open=True).at((xd + 2.5, VMID)).label(gpio, loc="right", ofst=0.15))


with schemdraw.Drawing(show=False) as d:
    # rails
    d.add(elm.Dot(open=True).at((0, TOP)).label("Pico 3V3(OUT)  36番ピン", loc="left", ofst=0.15))
    d.add(elm.Line().at((0, TOP)).to((X_END - 4.4, TOP)))
    d.add(elm.Dot(open=True).at((0, GND)).label("Pico AGND  33番ピン", loc="left", ofst=0.15))
    d.add(elm.Line().at((0, GND)).to((X_END - 4.4, GND)))

    # mid-rail divider and its capacitor
    d.add(elm.Dot().at((1.2, TOP)))
    d.add(elm.Resistor().at((1.2, TOP)).to((1.2, VMID)).label("R1\n10kΩ", loc="top", ofst=0.15))
    d.add(elm.Dot().at((1.2, VMID)))
    d.add(elm.Resistor().at((1.2, VMID)).to((1.2, GND)).label("R2\n10kΩ", loc="top", ofst=0.15))
    d.add(elm.Dot().at((1.2, GND)))
    d.add(elm.Line().at((1.2, VMID)).to((3.0, VMID)))
    d.add(elm.Dot().at((3.0, VMID)))
    d.add(elm.Capacitor().at((3.0, VMID)).to((3.0, GND)).label("C0 10μF", loc="bottom", ofst=0.15))
    d.add(elm.Dot().at((3.0, GND)))
    d.add(elm.Label().at((2.2, VMID + 0.4)).label("VMID ≈ 1.65V", halign="left"))
    d.add(elm.Line().at((3.0, VMID)).to((4.0, VMID)))
    d.add(elm.Dot().at((4.0, VMID)))

    channel(d, 4.0, "GP26 / ADC0  31番ピン  (ch0)", "取り出す皿", 1)

    d.add(elm.Label().at((0, GND - 1.3)).label(
        "ch1（置く皿）：同じ回路（PZ2・R2a・R2b・D2a・D2b・C2）をもう1組、"
        "VMID・3V3・AGND を共用して GP27 / ADC1（32番ピン）へ。", halign="left"))
    d.add(elm.Label().at((0, GND - 1.9)).label(
        "PZ の − は VMID、＋ は R*a/R*b 側。D*a はカソードが 3V3、D*b はアノードが AGND。", halign="left"))

    d.save(str(OUT / "schematic.svg"))
    d.save(str(OUT / "schematic.png"), dpi=160)

print("wrote", OUT / "schematic.svg", OUT / "schematic.png")
