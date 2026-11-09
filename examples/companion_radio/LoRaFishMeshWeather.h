#pragma once

#include <stdint.h>
#include "LoRaFishRfStats.h"

// Pet senses: "mesh weather".
//
// The pet notices when the mesh suddenly gets much busier than it has been lately, and
// gives a brief sparkle. "Busier than lately" is RELATIVE, so it works the same on a
// quiet rural mesh and on a busy city one:
//
//   the newest finished minute  >=  SPIKE_TENTHS/10 times the average of the minutes before
//   it (up to BASELINE_MINUTES of them)  AND  at least SPIKE_FLOOR packets.
//
// The counts come from RF Monitor+ (LoRaFishRfStats::Window), which keeps the packet total
// of each of the last 32 finished minutes. Purely presentational:
//
//   * RAM only: this class is 12 bytes, the minute totals are 64 bytes; never stored,
//     gone after a restart.
//   * It only READS the counts. It does not touch what is received, forwarded or
//     answered, any radio packet, the save file, food, growth, breeding or visits.
//   * It is worked out once per finished minute, so it cannot flicker with every packet.
//   * Nothing sparkles until MIN_BASELINE_MINUTES of earlier minutes exist to compare with.
//   * A sparkle fires when the mesh JUMPS, not while it stays high, and at most once every
//     COOLDOWN_MS, however noisy the mesh gets.
//
// The constants below are the only thing to tune.
//
// Written from scratch for LoRagotchi-DX; no Orion/Nova code is used here.

// --- e-ink never gets this -----------------------------------------------------------------
// E-ink panels are for still images. They get NO animation of any kind, by design, and this
// effect is not available on them: there is no option to switch it on.
//
// Compile time: a build whose DISPLAY_CLASS is an e-ink driver defines LORAFISH_EINK_BUILD as 1,
// and then the sparkle drawing, its state and its timing are not compiled in at all.
// (An e-ink driver is any class in src/helpers/ui that says isEink() { return true; }.
// test/ui/check_mesh_weather.py checks this list against those classes.)
// Run time: UITask.cpp also asks display->isEink() and returns before touching anything.
#define LORAFISH_EINK_CLASS_GxEPDDisplay 1
#define LORAFISH_EINK_CLASS_E213Display 1
#define LORAFISH_EINK_CLASS_E290Display 1
#define LORAFISH_EINK_PASTE_(a, b) a##b
#define LORAFISH_EINK_PASTE(a, b) LORAFISH_EINK_PASTE_(a, b)
#ifdef DISPLAY_CLASS
  #if LORAFISH_EINK_PASTE(LORAFISH_EINK_CLASS_, DISPLAY_CLASS)
    #define LORAFISH_EINK_BUILD 1
  #endif
#endif
#ifndef LORAFISH_EINK_BUILD
  #define LORAFISH_EINK_BUILD 0
#endif

namespace LoRaFishMeshWeather {

// --- the rule ---------------------------------------------------------------
static constexpr uint32_t SPIKE_TENTHS         = 25;  // 25 = "2.5 times the usual"
static constexpr uint32_t SPIKE_FLOOR          = 8;   // ... and at least this many packets in the minute
static constexpr uint8_t  BASELINE_MINUTES     = 30;  // "usual" = average of up to this many earlier minutes
static constexpr uint8_t  MIN_BASELINE_MINUTES = 10;  // no sparkle until this many earlier minutes exist
static_assert(BASELINE_MINUTES < LoRaFishRfStats::HISTORY, "history must hold the baseline plus the newest minute");
static_assert(MIN_BASELINE_MINUTES <= BASELINE_MINUTES, "cannot need more than the baseline holds");

// --- how it looks -----------------------------------------------------------
static constexpr uint32_t SPARKLE_MS  = 5000UL;     // colour screens: how long the three yellow twinkles last
static constexpr uint32_t COOLDOWN_MS = 180000UL;   // at least this long between sparkles

// Monochrome (1-bit OLED / LCD): one small plus in a corner of the tank, then a single dot, then gone.
static constexpr uint32_t MONO_PLUS_MS = 1000UL;    // the 3x3 plus (5 pixels)
static constexpr uint32_t MONO_DOT_MS  = 300UL;     // fade step: just the centre pixel; after this, nothing

// Where the mono sparkle may go (centre of the plus). Both spots are inside the tank, under the
// header line (y 15) and above the floor line (y h-15), clear of the centred text rows.
static constexpr int MONO_EDGE   = 5;    // distance of the centre from the left / right screen edge
static constexpr int MONO_ROW_Y  = 20;   // distance of the centre from the top
// A generous box round the pet (its position is the middle of the sprite; sprites stay within ~20 px).
static constexpr int PET_HALF_W  = 26;
static constexpr int PET_ABOVE   = 20;
static constexpr int PET_BELOW   = 18;
static constexpr int SPOT_MARGIN = 3;    // clear space kept between the plus (3x3) and the pet box

// Picks the corner for the mono sparkle that keeps clear of the pet. Returns false (draw nothing)
// when the pet is near both corners.
inline bool monoSpot(int w, int petX, int petY, int& cx, int& cy) {
  const int xs[2] = {MONO_EDGE, w - 1 - MONO_EDGE};
  for (uint8_t i = 0; i < 2; ++i) {
    const int x0 = xs[i] - 1 - SPOT_MARGIN, x1 = xs[i] + 1 + SPOT_MARGIN;           // plus + margin
    const int y0 = MONO_ROW_Y - 1 - SPOT_MARGIN, y1 = MONO_ROW_Y + 1 + SPOT_MARGIN;
    const bool hit = x0 <= petX + PET_HALF_W && x1 >= petX - PET_HALF_W &&
                     y0 <= petY + PET_BELOW && y1 >= petY - PET_ABOVE;
    if (!hit) { cx = xs[i]; cy = MONO_ROW_Y; return true; }
  }
  return false;
}

// The rule on its own: was the newest minute a jump compared with the 'minutesBefore' minutes before it
// (whose packets add up to 'sumBefore')?
inline bool isSpike(uint32_t newest, uint32_t sumBefore, uint32_t minutesBefore) {
  if (minutesBefore < MIN_BASELINE_MINUTES) return false;       // not enough history yet
  if (newest < SPIKE_FLOOR) return false;                       // too small to matter, whatever the ratio
  return newest * minutesBefore * 10UL >= sumBefore * SPIKE_TENTHS;
}

class Sense {
  uint32_t seen_ = 0;           // how many finished minutes have been looked at
  uint32_t sparkleStart_ = 0;
  bool sparkling_ = false;
  bool everSparkled_ = false;
  bool wasSpike_ = false;       // the minute before was already a jump

  static bool within(uint32_t now, uint32_t since, uint32_t span) {   // wrap-safe
    return (int32_t)(now - since) >= 0 && (uint32_t)(now - since) < span;
  }

public:
  // Looks at the window; works the rule out again only when a new minute has finished.
  void update(uint32_t now, LoRaFishRfStats::Window& window) {
    const uint32_t done = window.finishedMinutes(now);
    if (done != seen_) {
      const bool consecutive = (done - seen_) == 1;   // otherwise minutes were skipped
      seen_ = done;
      const uint32_t have = done < LoRaFishRfStats::HISTORY ? done : LoRaFishRfStats::HISTORY;
      uint32_t n = have - 1;                          // minutes before the newest one
      if (n > BASELINE_MINUTES) n = BASELINE_MINUTES;
      uint32_t sum = 0;
      for (uint32_t k = 1; k <= n; ++k) sum += window.minuteAgo((uint8_t)k);
      const bool spike = isSpike(window.minuteAgo(0), sum, n);
      const bool cooled = !everSparkled_ || !within(now, sparkleStart_, COOLDOWN_MS);
      if (spike && !(consecutive && wasSpike_) && cooled) {
        sparkling_ = true;
        everSparkled_ = true;
        sparkleStart_ = now;
      }
      wasSpike_ = spike;
    }
    if (sparkling_ && !within(now, sparkleStart_, SPARKLE_MS)) sparkling_ = false;
  }

  // Colour screens: true for SPARKLE_MS after a jump.
  bool sparkling() const { return sparkling_; }
  // Which of the four twinkle frames to draw (0..3), changing every quarter second.
  uint8_t frame(uint32_t now) const { return (uint8_t)((now / 250UL) & 3); }
  // Mono screens: 0 = draw nothing, 1 = the 3x3 plus, 2 = just the centre pixel.
  uint8_t monoStep(uint32_t now) const {
    if (!sparkling_) return 0;
    const uint32_t age = now - sparkleStart_;
    if ((int32_t)age < 0) return 0;
    if (age < MONO_PLUS_MS) return 1;
    if (age < MONO_PLUS_MS + MONO_DOT_MS) return 2;
    return 0;
  }
};

}  // namespace LoRaFishMeshWeather
