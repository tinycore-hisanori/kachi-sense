// Click detector, C++ port of kachi_sense/dsp.py. Keep the two in step.
#pragma once
#include <math.h>
#include <stdint.h>

namespace ks {

constexpr float FS = 20000.0f;
constexpr float HPF_HZ = 1500.0f;
constexpr float LPF_HZ = 400.0f;
constexpr float ENV_RELEASE_MS = 5.0f;
constexpr float FLOOR_TC_S = 0.5f;
constexpr float DC_TC_S = 0.5f;
constexpr float K_ON = 6.0f;
constexpr float K_OFF = 2.5f;
constexpr float MIN_ABS = 12.0f;
constexpr float HOLD_MS = 4.0f;
constexpr float MAX_MS = 60.0f;
constexpr float REFRACTORY_MS = 40.0f;
constexpr float CLICK_RATIO = 2.0f;
constexpr float WARMUP_MS = 50.0f;

struct Event {
  uint8_t ch;
  uint32_t start_n;  // sample index when the event began
  float dur_ms, peak, energy, lf_peak;
  float ratio() const { return peak / (lf_peak + 1.0f); }
  bool is_click() const { return ratio() >= CLICK_RATIO; }
};

class Detector {
 public:
  explicit Detector(uint8_t ch) : ch_(ch) {
    const float w0 = 2.0f * (float)M_PI * HPF_HZ / FS;
    const float al = sinf(w0) / sqrtf(2.0f);
    const float c = cosf(w0);
    const float a0 = 1.0f + al;
    b0_ = (1.0f + c) / 2.0f / a0;
    b1_ = -(1.0f + c) / a0;
    b2_ = b0_;
    a1_ = -2.0f * c / a0;
    a2_ = (1.0f - al) / a0;
    lp_a_ = 1.0f - expf(-2.0f * (float)M_PI * LPF_HZ / FS);
    dc_a_ = 1.0f / (FS * DC_TC_S);
    rel_ = expf(-1.0f / (FS * ENV_RELEASE_MS / 1000.0f));
    floor_a_ = 1.0f / (FS * FLOOR_TC_S);
    hold_ = (uint32_t)(FS * HOLD_MS / 1000.0f);
    max_len_ = (uint32_t)(FS * MAX_MS / 1000.0f);
    refr_ = (uint32_t)(FS * REFRACTORY_MS / 1000.0f);
    warmup_ = (uint32_t)(FS * WARMUP_MS / 1000.0f);
  }

  // Feed one raw ADC sample (0..4095). Returns true and fills *out when an event ends.
  bool push(float x, Event* out) {
    const uint32_t n = n_++;
    if (!primed_) { dc_ = x; primed_ = true; }
    dc_ += (x - dc_) * dc_a_;
    const float v = x - dc_;

    const float y = b0_ * v + z1_;            // high band
    z1_ = b1_ * v - a1_ * y + z2_;
    z2_ = b2_ * v - a2_ * y;
    lp1_ += (v - lp1_) * lp_a_;               // low band
    lp2_ += (lp1_ - lp2_) * lp_a_;

    const float a = fabsf(y);
    env_ = a > env_ ? a : env_ * rel_;

    if (n < warmup_) { floor_ += (env_ - floor_) * 0.02f; return false; }

    if (!in_event_) {
      const float on = fmaxf(floor_ * K_ON, MIN_ABS);
      if (env_ > on && n >= quiet_until_) {
        in_event_ = true;
        ev_start_ = n; below_ = 0;
        ev_peak_ = ev_energy_ = ev_lf_ = 0.0f;
      } else {
        floor_ += (env_ - floor_) * floor_a_;
        return false;
      }
    }

    ev_peak_ = fmaxf(ev_peak_, a);
    ev_energy_ += y * y;
    ev_lf_ = fmaxf(ev_lf_, fabsf(lp2_));
    const float off = fmaxf(floor_ * K_OFF, MIN_ABS * 0.5f);
    below_ = env_ < off ? below_ + 1 : 0;
    const uint32_t len = n - ev_start_ + 1;
    if (below_ >= hold_ || len >= max_len_) {
      in_event_ = false;
      quiet_until_ = n + refr_;
      out->ch = ch_;
      out->start_n = ev_start_;
      out->dur_ms = len * 1000.0f / FS;
      out->peak = ev_peak_;
      out->energy = ev_energy_;
      out->lf_peak = ev_lf_;
      return true;
    }
    return false;
  }

  float noise_floor() const { return floor_; }  // envelope floor, ADC counts
  float dc() const { return dc_; }              // input DC level, ADC counts (VMID ~ 2048)

 private:
  uint8_t ch_;
  float b0_, b1_, b2_, a1_, a2_, lp_a_, dc_a_, rel_, floor_a_;
  uint32_t hold_, max_len_, refr_, warmup_;
  uint32_t n_ = 0, ev_start_ = 0, below_ = 0, quiet_until_ = 0;
  bool primed_ = false, in_event_ = false;
  float dc_ = 0, z1_ = 0, z2_ = 0, lp1_ = 0, lp2_ = 0, env_ = 0, floor_ = 0;
  float ev_peak_ = 0, ev_energy_ = 0, ev_lf_ = 0;
};

}  // namespace ks
