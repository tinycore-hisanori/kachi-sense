// Host build of the firmware detector, for tests/test_parity.py.
// stdin: "ch value" per line. stdout: one line per event.
#include <cstdio>
#include "../firmware/kachi_sense_pico/detector.h"
int main() {
  ks::Detector d[2] = {ks::Detector(0), ks::Detector(1)};
  unsigned ch; float v; ks::Event e;
  while (std::scanf("%u %f", &ch, &v) == 2)
    if (d[ch].push(v, &e))
      std::printf("%u %lu %s %.3f\n", e.ch, (unsigned long)e.start_n, e.is_click() ? "click" : "thud", e.peak);
  return 0;
}
