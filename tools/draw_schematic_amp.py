"""Draw docs/schematic_amp.svg and docs/schematic_amp.png (v2: op-amp preamp, x11).

    pip install schemdraw matplotlib
    python tools/draw_schematic_amp.py
"""

from pathlib import Path

import matplotlib
import schemdraw
import schemdraw.elements as elm

matplotlib.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "sans-serif"]
schemdraw.config(fontsize=11, lw=1.4)
OUT = Path(__file__).resolve().parents[1] / "docs"

V3_LABEL = "3V3（Pico 36番ピン）"
GND_LABEL = "Pico AGND\n（33番ピン）"


def vdd(d, x, y, label=V3_LABEL):
    d.add(elm.Vdd().at((x, y)).label(label, loc="top", ofst=0.1))


def gnd(d, x, y, label=GND_LABEL):
    d.add(elm.Ground().at((x, y)).label(label, loc="bottom", fontsize=9, ofst=0.1))


def channel(d, yc, gpio, plate, n, half, pins):
    """One complete channel: VMID divider, piezo, input clamp, x11 amp, anti-alias RC."""
    ym = yc - 4.2                     # VMID line (y)
    # VMID divider and its capacitor
    vdd(d, 1.2, ym + 2.6)
    d.add(elm.Resistor().at((1.2, ym + 2.6)).to((1.2, ym)).label(f"R{n}c\n10kΩ", loc="top", ofst=0.15))
    d.add(elm.Dot().at((1.2, ym)))
    d.add(elm.Resistor().at((1.2, ym)).to((1.2, ym - 2.6)).label(f"R{n}d\n10kΩ", loc="top", ofst=0.15))
    gnd(d, 1.2, ym - 2.6)
    d.add(elm.Line().at((1.2, ym)).to((4.0, ym)))
    d.add(elm.Dot().at((3.0, ym)))
    d.add(elm.Capacitor().at((3.0, ym)).to((3.0, ym - 2.6)).label(f"C{n}m\n10μF", loc="bottom", ofst=0.15))
    gnd(d, 3.0, ym - 2.6)
    d.add(elm.Label().at((1.4, ym + 0.4)).label(f"VMID{n} ≈ 1.65V", halign="left"))
    d.add(elm.Dot().at((4.0, ym)))
    d.add(elm.Line().at((4.0, ym)).to((4.0, yc)))

    # piezo with its 100k bias
    x0, xa = 4.0, 7.6
    d.add(elm.Line().at((x0, yc)).to((x0 + 0.6, yc)))
    d.add(elm.Crystal().at((x0 + 0.6, yc)).to((xa, yc))
          .label(f"PZ{n}  7BB-27-4L0\n（{plate}の裏）", loc="top", ofst=0.25))
    d.add(elm.Label().at((x0 + 0.85, yc - 0.35)).label("−"))
    d.add(elm.Label().at((xa - 0.25, yc - 0.35)).label("＋"))
    d.add(elm.Dot().at((xa, yc)))
    d.add(elm.Line().at((x0 + 0.3, yc)).to((x0 + 0.3, yc - 1.6)))
    d.add(elm.Dot().at((x0 + 0.3, yc)))
    d.add(elm.Resistor().at((x0 + 0.3, yc - 1.6)).to((xa, yc - 1.6)).label(f"R{n}a 100kΩ", loc="bottom"))
    d.add(elm.Line().at((xa, yc - 1.6)).to((xa, yc)))

    # 10k series + clamps at the op-amp input
    xp = xa + 3.0
    d.add(elm.Resistor().at((xa, yc)).to((xp, yc)).label(f"R{n}b 10kΩ", loc="top"))
    d.add(elm.Dot().at((xp, yc)))
    d.add(elm.Schottky().at((xp, yc)).to((xp, yc + 2.2)).label(f"D{n}a BAT43", loc="bottom", ofst=0.15))
    vdd(d, xp, yc + 2.2)
    d.add(elm.Schottky().at((xp, yc - 2.2)).to((xp, yc)).label(f"D{n}b BAT43", loc="top", ofst=0.15))
    gnd(d, xp, yc - 2.2)

    # non-inverting amp: + on top, - below
    op = d.add(elm.Opamp(leads=True).right().flip().anchor("in2").at((xp + 2.0, yc))
               .label(f"U1{half}\nMCP6002", loc="center", ofst=(0.35, 0), fontsize=10))
    d.add(elm.Line().at((xp, yc)).to(op.in2))
    d.add(elm.Label().at((op.in2[0] + 0.25, op.in2[1] + 0.3)).label(pins[0], fontsize=9, color="gray"))
    d.add(elm.Label().at((op.in1[0] + 0.25, op.in1[1] - 0.3)).label(pins[1], fontsize=9, color="gray"))
    d.add(elm.Label().at((op.out[0] - 0.25, op.out[1] + 0.3)).label(pins[2], fontsize=9, color="gray"))
    yf = yc - 2.6                     # feedback / gain node row
    xf = op.in1[0]
    d.add(elm.Line().at(op.in1).to((xf, yf)))
    d.add(elm.Dot().at((xf, yf)))
    d.add(elm.Resistor().at((xf, yf)).to((op.out[0], yf)).label(f"R{n}f 100kΩ", loc="top"))
    d.add(elm.Line().at((op.out[0], yf)).to(op.out))
    d.add(elm.Resistor().at((xf, yf)).to((xf, ym)).label(f"R{n}g\n10kΩ", loc="bottom", ofst=0.15))
    d.add(elm.Line().at((4.0, ym)).to((xf, ym)))
    d.add(elm.Dot().at((xf, ym)))

    # anti-alias RC to the ADC
    d.add(elm.Dot().at(op.out))
    yo = op.out[1]
    xo = op.out[0] + 3.0
    d.add(elm.Resistor().at(op.out).to((xo, yo)).label(f"R{n}e 10kΩ", loc="top"))
    d.add(elm.Dot().at((xo, yo)))
    d.add(elm.Capacitor().at((xo, yo)).to((xo, yo - 2.2)).label(f"C{n} 1500pF\n（1000pFでも可）", loc="bottom", ofst=0.15))
    gnd(d, xo, yo - 2.2)
    d.add(elm.Line().at((xo, yo)).to((xo + 2.0, yo)))
    d.add(elm.Dot(open=True).at((xo + 2.0, yo)).label(gpio, loc="right", ofst=0.15))


Y0, Y1 = 8.0, -6.5

with schemdraw.Drawing(show=False) as d:
    d.add(elm.Label().at((0, Y0 + 4.0)).label("ch0（取り出す皿）　VMID からの振れを 11 倍に増幅（1 + R1f/R1g）", halign="left", fontsize=13))
    channel(d, Y0, "GP26 / ADC0  31番ピン  (ch0)", "取り出す皿", 1, "A", ("3 +", "2 −", "1"))
    d.add(elm.Line().at((0, Y0 - 9.0)).to((31, Y0 - 9.0)).linestyle(":").color("gray"))
    d.add(elm.Label().at((0, Y1 + 4.0)).label("ch1（置く皿）　※ch0 とまったく同じ回路。オペアンプは同じ MCP6002 のもう片方（B）", halign="left", fontsize=13))
    channel(d, Y1, "GP27 / ADC1  32番ピン  (ch1)", "置く皿", 2, "B", ("5 +", "6 −", "7"))

    yn = Y1 - 9.2
    notes = [
        "3V3 はすべて Pico の 36番ピン 3V3(OUT) から取る。GND（⏚）はすべて Pico の 33番ピン AGND につなぐ。（Raspberry Pi Pico・Pico 2 W 共通）",
        "MCP6002 の電源は 8番ピン＝3V3、4番ピン＝AGND（1個で2チャンネル分）。8番と4番のすぐそばに 0.1μF のパスコンを入れる。",
        "R*g を VMID に戻しているので、出力の中心も VMID（≈1.65V、ずれはオフセット×11 で最大 ±50mV 程度）。振れだけ 11 倍。もっと欲しければ R*f を 220kΩ で 23 倍。",
        "PZ の − は VMID、＋ は R*a/R*b 側。D*a はカソードが 3V3、D*b はアノードが AGND（オペアンプ入力の保護）。",
    ]
    for i, t in enumerate(notes):
        d.add(elm.Label().at((0, yn - 0.6 * i)).label(t, halign="left"))

    d.save(str(OUT / "schematic_amp.svg"))
    d.save(str(OUT / "schematic_amp.png"), dpi=150)

print("wrote", OUT / "schematic_amp.svg", OUT / "schematic_amp.png")
