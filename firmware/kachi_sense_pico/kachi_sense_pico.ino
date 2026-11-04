// kachi-sense firmware for Raspberry Pi Pico / Pico W (RP2040) and Pico 2 / Pico 2 W (RP2350),
// Arduino-Pico core (Earle Philhower). The same sketch builds for all four boards.
//
// Two piezo discs, one under each plate:
//   GP26 / A0 = ch 0 = source plate (beans start here)
//   GP27 / A1 = ch 1 = target plate (beans should land here)
// Each channel is sampled at 20 kHz (the timer runs at 40 kHz and alternates).
// Detected events go out over USB serial as one JSON object per line:
//   {"ch":1,"t_us":1234567,"kind":"click","dur_ms":13.1,"peak":212.0,"energy":15320.5,"ratio":8.4}
// The on-board LED (LED_BUILTIN) blinks on every click on the target plate. On the W boards the
// LED hangs off the wireless chip; the core routes LED_BUILTIN there for us.
//
// Serial commands: "t" toggles printing thuds, "T" turns it on, "Q" turns it off,
// "s" prints a status line, "v" prints the version / chip line. The web demo (docs/demo/) sends "T" when it connects.

#include <Arduino.h>
#include "pico/time.h"
#include "hardware/adc.h"
#include "detector.h"

static constexpr uint32_t RING = 4096;          // samples, both channels interleaved
static volatile uint16_t ring_[RING];
static volatile uint32_t head_ = 0;              // written by the timer
static volatile uint32_t tail_ = 0;              // advanced by loop(), read by the timer
static volatile uint32_t overruns_ = 0;
static volatile uint8_t next_ch_ = 0;

static repeating_timer_t timer_;
static ks::Detector det0(0), det1(1);
static uint32_t n_ch_[2] = {0, 0};               // samples processed per channel
static uint32_t t0_us_ = 0;
static bool print_thuds_ = false;
static uint32_t led_off_ms_ = 0;
static uint32_t clicks_[2] = {0, 0};

#define KS_VERSION "0.1.1"
#if defined(PICO_RP2350)
#define KS_CHIP "RP2350"
#else
#define KS_CHIP "RP2040"
#endif

static void print_version() {
  Serial.printf("# kachi-sense %s on %s, %lu MHz, 2 ch x %d Hz\n", KS_VERSION, KS_CHIP,
                (unsigned long)(rp2040.f_cpu() / 1000000), (int)ks::FS);
}

static bool on_tick(repeating_timer_t*) {
  const uint16_t v = adc_read();                 // channel selected on the previous tick
  const uint8_t ch = next_ch_;
  next_ch_ ^= 1;
  adc_select_input(next_ch_);                    // settles before the next tick (25 us)
  const uint32_t h = head_;
  if (h - tail_ >= RING) { overruns_++; return true; }
  ring_[h % RING] = (uint16_t)(v | (ch << 15));
  head_ = h + 1;
  return true;
}

static void emit(const ks::Event& e) {
  const bool click = e.is_click();
  if (click) clicks_[e.ch]++;
  if (!click && !print_thuds_) return;
  const uint32_t t_us = t0_us_ + (uint32_t)(e.start_n * (1e6f / ks::FS));
  Serial.printf("{\"ch\":%u,\"t_us\":%lu,\"kind\":\"%s\",\"dur_ms\":%.1f,\"peak\":%.1f,\"energy\":%.1f,\"ratio\":%.2f}\n",
                e.ch, (unsigned long)t_us, click ? "click" : "thud", e.dur_ms, e.peak, e.energy, e.ratio());
  if (click && e.ch == 1) { digitalWrite(LED_BUILTIN, HIGH); led_off_ms_ = millis() + 80; }
}

void setup() {
  Serial.begin(115200);
  // Give the PC up to 2 s to open the port so the version line is not lost; runs fine without a PC.
  for (const uint32_t t = millis(); !Serial && millis() - t < 2000;) delay(10);
  print_version();
  pinMode(LED_BUILTIN, OUTPUT);
  adc_init();
  adc_gpio_init(26);
  adc_gpio_init(27);
  adc_select_input(0);
  t0_us_ = time_us_32();
  // negative interval = fixed period between starts, 25 us -> 40 kHz total
  add_repeating_timer_us(-25, on_tick, nullptr, &timer_);
}

void loop() {
  while (tail_ != head_) {
    const uint16_t raw = ring_[tail_ % RING];
    tail_++;
    const uint8_t ch = raw >> 15;
    const float x = (float)(raw & 0x0FFF);
    ks::Event e;
    if ((ch == 0 ? det0 : det1).push(x, &e)) emit(e);
    n_ch_[ch]++;
  }
  if (led_off_ms_ && millis() > led_off_ms_) { digitalWrite(LED_BUILTIN, LOW); led_off_ms_ = 0; }
  if (Serial.available()) {
    const int c = Serial.read();
    if (c == 't') print_thuds_ = !print_thuds_;
    if (c == 'T') print_thuds_ = true;
    if (c == 'Q') print_thuds_ = false;
    if (c == 'v') print_version();
    if (c == 's') {
      Serial.printf("# samples ch0=%lu ch1=%lu overruns=%lu clicks src=%lu tgt=%lu thuds=%s\n",
                    (unsigned long)n_ch_[0], (unsigned long)n_ch_[1], (unsigned long)overruns_,
                    (unsigned long)clicks_[0], (unsigned long)clicks_[1], print_thuds_ ? "on" : "off");
    }
  }
}
