#pragma once

#include <stdint.h>
#include "LoRaFishRfStats.h"

// Pet senses: "mesh weather".
//
// The pet notices how busy the mesh has been, using the packet counts RF Monitor+
// already keeps (LoRaFishRfStats::Window, the last 4 to 5 minutes). That becomes one
// small level -- quiet / normal / busy -- and a busy mesh gives the pet a brief
// sparkle. Purely presentational:
//
//   * RAM only: about 16 bytes, never saved, gone after a restart.
//   * It only READS the counts. It does not touch what is received, forwarded or
//     answered, any radio packet, the save file, food, growth, breeding or visits.
//   * The level is only worked out again when the count window rolls on to a new
//     minute, so it cannot flicker with every packet.
//   * The sparkle is bounded: it lasts SPARKLE_MS, and at most once every
//     COOLDOWN_MS, however noisy the mesh gets. A mesh that stays busy does not
//     keep the pet sparkling.
//
// Written from scratch for LoRagotchi-DX; no Orion/Nova code is used here.
namespace LoRaFishMeshWeather {

enum Level : uint8_t { Quiet, Normal, Busy };

// Packets heard in the window (about 5 minutes).
static constexpr uint32_t QUIET_MAX = 4;    // 4 or fewer: less than one a minute
static constexpr uint32_t BUSY_MIN  = 60;   // 60 or more: about 12 a minute or more

static constexpr uint32_t SPARKLE_MS  = 5000UL;     // how long one sparkle lasts
static constexpr uint32_t COOLDOWN_MS = 180000UL;   // at least this long between sparkles

inline Level levelFor(uint32_t packetsInWindow) {
  if (packetsInWindow <= QUIET_MAX) return Quiet;
  if (packetsInWindow >= BUSY_MIN) return Busy;
  return Normal;
}

inline const char* label(Level l) {
  return l == Quiet ? "quiet" : l == Busy ? "busy" : "normal";
}

class Sense {
  uint32_t mark_ = 0;          // start of the window minute the level was worked out for
  uint32_t sparkleStart_ = 0;
  uint8_t level_ = Normal;
  bool marked_ = false;
  bool sparkling_ = false;
  bool everSparkled_ = false;

  static bool within(uint32_t now, uint32_t since, uint32_t span) {   // wrap-safe
    return (int32_t)(now - since) >= 0 && (uint32_t)(now - since) < span;
  }

public:
  // Looks at the window; works out the level again only if the window has rolled on.
  void update(uint32_t now, LoRaFishRfStats::Window& window) {
    const uint32_t mark = window.rollMark(now);
    if (!marked_ || mark != mark_) {
      marked_ = true;
      mark_ = mark;
      const Level next = levelFor(window.total(now));
      const bool cooled = !everSparkled_ || !within(now, sparkleStart_, COOLDOWN_MS);
      if (next == Busy && level_ != Busy && cooled) {
        sparkling_ = true;
        everSparkled_ = true;
        sparkleStart_ = now;
      }
      level_ = next;
    }
    if (sparkling_ && !within(now, sparkleStart_, SPARKLE_MS)) sparkling_ = false;
  }

  Level level() const { return (Level)level_; }
  bool sparkling() const { return sparkling_; }
  // Which of the four twinkle frames to draw (0..3), changing every quarter second.
  uint8_t frame(uint32_t now) const { return (uint8_t)((now / 250UL) & 3); }
};

}  // namespace LoRaFishMeshWeather
