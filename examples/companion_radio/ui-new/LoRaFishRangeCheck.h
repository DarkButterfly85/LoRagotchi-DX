#pragma once

#include <stdint.h>

// Range Check: "can my pet reach anyone from here?"
//
// One press sends MeshCore's own zero-hop "node discover" control packet (the
// same packet the stock Discovery page sends; no new packet type, no format
// change). Repeaters that hear it answer with a short reply, and every reply
// is matched to the probe by its random tag. This header is the decision only:
// no radio, no display, no settings, no flash. Nothing here is saved.
//
// Each reply is graded from how well it was heard (RSSI, dBm) and how well the
// repeater heard us (SNR, dB; the reply carries it). A reply is only as good as
// the weaker of those, and the verdict is the best reply heard in the window:
//   GOOD  RSSI >= -100 dBm and SNR >= 4 dB    (solid link)
//   OK    RSSI >= -112 dBm and SNR >= -3 dB   (works, little margin)
//   WEAK  anything heard that is worse        (at the edge)
//   NONE  nothing answered within the window
// The same thresholds are used for every spreading factor. They are a guide for
// the owner, not a link budget.
namespace LoRaFishRangeCheck {

enum class Verdict : uint8_t { None, Weak, Ok, Good };
enum class State : uint8_t { Idle, Listening, Done };

static constexpr uint32_t WINDOW_MS = 10000;    // how long to listen after the probe
static constexpr uint32_t COOLDOWN_MS = 20000;  // probe-to-probe minimum (airtime courtesy)

// Quarter-dB inputs are what the radio reports (SNR x 4); RSSI is whole dBm.
inline Verdict grade(int rssiDbm, int snrInQuarterDb, int snrOutQuarterDb) {
  const int snr4 = snrInQuarterDb < snrOutQuarterDb ? snrInQuarterDb : snrOutQuarterDb;
  if (rssiDbm >= -100 && snr4 >= 4 * 4) return Verdict::Good;
  if (rssiDbm >= -112 && snr4 >= -3 * 4) return Verdict::Ok;
  return Verdict::Weak;
}

class Session {
  bool started = false;
  uint32_t sentAt = 0, tag = 0;
  uint8_t heard = 0;
  Verdict best = Verdict::None;
  int bestRssi = 0, bestSnr4 = 0;   // of the best reply, for the screen

  // Wrap-safe; a clock a hair behind the send time (a frame started just before) counts as zero.
  uint32_t elapsed(uint32_t now) const { int32_t d = (int32_t)(now - sentAt); return d < 0 ? 0 : (uint32_t)d; }

public:
  // False while the last probe is still too recent (no new probe may be sent).
  bool canStart(uint32_t now) const { return !started || elapsed(now) >= COOLDOWN_MS; }
  uint32_t waitSeconds(uint32_t now) const {
    if (canStart(now)) return 0;
    return (COOLDOWN_MS - elapsed(now) + 999) / 1000;
  }
  // Call when the probe has actually been handed to the radio.
  void start(uint32_t now, uint32_t newTag) {
    started = true; sentAt = now; tag = newTag;
    heard = 0; best = Verdict::None; bestRssi = 0; bestSnr4 = 0;
  }
  State state(uint32_t now) const {
    if (!started) return State::Idle;
    return elapsed(now) < WINDOW_MS ? State::Listening : State::Done;
  }
  uint32_t secondsLeft(uint32_t now) const {
    if (state(now) != State::Listening) return 0;
    return (WINDOW_MS - elapsed(now) + 999) / 1000;
  }
  // A reply carrying a tag. Counted only for the live probe and inside its window.
  bool onReply(uint32_t now, uint32_t replyTag, int rssiDbm, int snrInQuarterDb, int snrOutQuarterDb) {
    if (!started || replyTag != tag || elapsed(now) >= WINDOW_MS) return false;
    if (heard < 255) ++heard;
    const Verdict v = grade(rssiDbm, snrInQuarterDb, snrOutQuarterDb);
    if (heard == 1 || v > best) {
      best = v;
      bestRssi = rssiDbm;
      bestSnr4 = snrInQuarterDb < snrOutQuarterDb ? snrInQuarterDb : snrOutQuarterDb;
    }
    return true;
  }
  uint8_t replies() const { return heard; }
  // Valid once state() == Done; while listening it is the best so far.
  Verdict verdict() const { return best; }
  int bestRssiDbm() const { return bestRssi; }
  int bestSnrQuarterDb() const { return bestSnr4; }
};

inline const char* word(Verdict v) {
  switch (v) {
    case Verdict::Good: return "GOOD";
    case Verdict::Ok: return "OK";
    case Verdict::Weak: return "WEAK";
    default: return "NONE";
  }
}

}  // namespace LoRaFishRangeCheck
