#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

// Battery readout for colour screens: a real Li-ion discharge curve instead of
// a straight line, and a runtime estimate from the recent discharge rate.
// Monochrome and e-ink screens do not use this; they keep legacyPercent().
//
// The curve is a typical single-cell 4.2 V Li-ion/LiPo under light load. It is
// not calibrated to any particular cell, so treat the numbers as honest
// estimates, not a fuel gauge.
namespace LoRaFishBattery {

struct Point { uint16_t mv; uint16_t tenths; };  // tenths of a percent

// Strictly increasing in voltage and in charge.
static const Point kCurve[] = {
  {3300, 0},   {3450, 20},  {3610, 50},  {3690, 100}, {3710, 150}, {3730, 200},
  {3750, 250}, {3770, 300}, {3790, 350}, {3800, 400}, {3820, 450}, {3840, 500},
  {3850, 550}, {3870, 600}, {3910, 650}, {3950, 700}, {3980, 750}, {4020, 800},
  {4080, 850}, {4110, 900}, {4150, 950}, {4200, 1000},
};
static const size_t kCurveLen = sizeof(kCurve) / sizeof(kCurve[0]);

// Charge in tenths of a percent (0..1000), linearly interpolated between points.
inline uint16_t tenthsPercent(uint16_t mv) {
  if (mv <= kCurve[0].mv) return 0;
  if (mv >= kCurve[kCurveLen - 1].mv) return 1000;
  size_t i = 1;
  while (mv > kCurve[i].mv) ++i;
  const Point& lo = kCurve[i - 1];
  const Point& hi = kCurve[i];
  const uint32_t span = (uint32_t)(hi.mv - lo.mv);
  const uint32_t part = (uint32_t)(mv - lo.mv) * (uint32_t)(hi.tenths - lo.tenths);
  return (uint16_t)(lo.tenths + (part + span / 2) / span);
}

inline int percent(uint16_t mv) { return (tenthsPercent(mv) + 5) / 10; }

// The original straight line from 3.3 V to 4.2 V, used by monochrome/e-ink.
inline int legacyPercent(uint16_t mv) {
  int p = ((int)mv - 3300) * 100 / 900;
  return p < 0 ? 0 : (p > 100 ? 100 : p);
}

// Keeps about an hour of readings, one every five minutes, and turns the
// recent drop into a time-left estimate.
static const uint8_t kSamples = 12;
static const uint32_t kIntervalMs = 5UL * 60UL * 1000UL;
static const uint32_t kMinSpanMs = 20UL * 60UL * 1000UL;
static const int32_t kMaxMinutes = 99 * 60;

struct Tracker {
  uint32_t t[kSamples];
  uint16_t p[kSamples];  // tenths of a percent
  uint8_t n;
  bool charging;
  Tracker() : n(0), charging(false) {}

  void reset() { n = 0; }

  bool due(uint32_t nowMs) const {
    return n == 0 || (uint32_t)(nowMs - t[n - 1]) >= kIntervalMs;
  }

  // Charging (or a battery reading that jumps up) throws the history away: the
  // curve only describes discharge.
  void sample(uint32_t nowMs, uint16_t mv, bool externalPower) {
    charging = externalPower;
    if (externalPower || mv == 0) { reset(); return; }
    if (!due(nowMs)) return;
    const uint16_t now = tenthsPercent(mv);
    if (n && now > p[n - 1] + 20) reset();  // up by more than 2%: it was charged
    if (n == kSamples) {
      for (uint8_t i = 1; i < kSamples; ++i) { t[i - 1] = t[i]; p[i - 1] = p[i]; }
      --n;
    }
    t[n] = nowMs;
    p[n] = now;
    ++n;
  }

  // Minutes of runtime left at the recent rate; -1 when it cannot be told yet
  // (charging, under 20 minutes of history, or no measurable drain). Capped at 99 h.
  int32_t minutesLeft() const {
    if (charging || n < 4) return -1;
    const uint32_t span = (uint32_t)(t[n - 1] - t[0]);
    if (span < kMinSpanMs) return -1;
    // Average the first and last few readings so one noisy reading does not swing it.
    const uint8_t k = n / 4 ? n / 4 : 1;
    uint32_t headT = 0, tailT = 0, headP = 0, tailP = 0;
    for (uint8_t i = 0; i < k; ++i) {
      headT += (uint32_t)(t[i] - t[0]);          headP += p[i];
      tailT += (uint32_t)(t[n - 1 - i] - t[0]);  tailP += p[n - 1 - i];
    }
    headT /= k; tailT /= k; headP /= k; tailP /= k;
    if (tailT <= headT || headP <= tailP) return -1;
    const uint32_t dropTenths = headP - tailP;
    const uint32_t dtMin = (tailT - headT) / 60000UL;
    if (dtMin == 0) return -1;
    const uint64_t minutes = (uint64_t)tailP * dtMin / dropTenths;
    return minutes > (uint64_t)kMaxMinutes ? kMaxMinutes : (int32_t)minutes;
  }
};

// Short text for the estimate: "~5.5h", "~40m", ">99h", "CHG" while charging, "--" if unknown.
inline void formatLeft(const Tracker& tracker, char* out, size_t cap) {
  if (cap == 0) return;
  const int32_t m = tracker.minutesLeft();
  if (tracker.charging) snprintf(out, cap, "CHG");
  else if (m < 0) snprintf(out, cap, "--");
  else if (m >= kMaxMinutes) snprintf(out, cap, ">99h");
  else if (m < 60) snprintf(out, cap, "~%ldm", (long)m);
  else if (m < 600) snprintf(out, cap, "~%ld.%ldh", (long)(m / 60), (long)((m % 60) / 6));
  else snprintf(out, cap, "~%ldh", (long)((m + 30) / 60));
}

}  // namespace LoRaFishBattery
