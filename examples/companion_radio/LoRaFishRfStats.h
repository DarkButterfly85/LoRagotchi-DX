#pragma once

#include <stdint.h>
#include <string.h>

// RF Monitor+: what kinds of packets the pet hears, and how far they travelled.
//
// Fed from the radio's existing "packet received" hook (MyMesh::logRxRaw), which
// already sees every received frame. This only READS the frame header: it never
// changes what is received, forwarded or answered, and nothing here is saved --
// the counts live in RAM and are gone after a restart.
//
// The last five minutes are kept as five one-minute buckets, so a count is
// "heard during the last 4 to 5 minutes" and old minutes fall off by themselves.
// Hops are counted from the path of flood-routed packets (how many repeaters
// passed them on); direct-routed packets are counted by type but have no
// "travelled so far" number, so they are left out of the hop average.
namespace LoRaFishRfStats {

static constexpr uint8_t BUCKETS = 5;
static constexpr uint32_t BUCKET_MS = 60000UL;
// Also kept: the total packets of each of the last HISTORY finished minutes (small whole
// numbers, 64 bytes, RAM only). Pet senses compares the newest minute with the ones before it.
static constexpr uint8_t HISTORY = 32;

// What the screen shows. Payload types are MeshCore's own (Packet.h).
enum Group : uint8_t { Adv, Dm, Chan, Ack, Req, Other, GroupCount };

inline const char* label(uint8_t g) {
  static const char* const names[GroupCount] = {"ADV", "DM", "CHAN", "ACK", "REQ", "OTHER"};
  return g < GroupCount ? names[g] : "?";
}

inline Group groupOf(uint8_t payloadType) {
  switch (payloadType) {
    case 0x04: return Adv;            // ADVERT
    case 0x02: return Dm;             // TXT_MSG (direct message)
    case 0x05: case 0x06: return Chan; // GRP_TXT / GRP_DATA (channel)
    case 0x03: case 0x0A: return Ack;  // ACK / MULTIPART
    case 0x00: case 0x01: case 0x07: case 0x08: return Req;  // REQ / RESPONSE / ANON_REQ / PATH
    default: return Other;            // TRACE, CONTROL, raw, future types
  }
}

struct Frame {
  bool ok = false;
  uint8_t group = Other;
  bool flood = false;   // flood-routed: hops is the number of repeaters it passed through
  uint8_t hops = 0;
};

// Reads the first bytes of a raw LoRa frame: header, optional 4 transport bytes, path length.
inline Frame parse(const uint8_t* raw, int len) {
  Frame f;
  if (!raw || len < 3) return f;
  const uint8_t header = raw[0];
  const uint8_t route = header & 0x03;            // 0 transport flood, 1 flood, 2 direct, 3 transport direct
  int i = 1;
  if (route == 0 || route == 3) i += 4;           // transport codes
  if (i >= len) return f;
  const uint8_t pathLen = raw[i];
  const uint8_t count = pathLen & 63;
  const uint8_t hashSize = (pathLen >> 6) + 1;
  if (hashSize > 3 || i + 1 + count * hashSize >= len) return f;   // needs a payload byte after the path
  f.ok = true;
  f.group = groupOf((header >> 2) & 0x0F);
  f.flood = (route == 0 || route == 1);
  f.hops = count;
  return f;
}

class Window {
  uint16_t seen[BUCKETS][GroupCount];
  uint16_t floods[BUCKETS][GroupCount];   // how many of those were flood-routed
  uint16_t hopSum[BUCKETS][GroupCount];
  uint8_t head = 0;
  uint32_t headStart = 0;
  bool started = false;
  uint16_t minutes[HISTORY];   // packets heard in each finished minute, oldest overwritten first
  uint8_t minutesNext = 0;
  uint32_t finished = 0;       // how many minutes have been finished since start-up

  void clear(uint8_t b) {
    memset(seen[b], 0, sizeof(seen[b]));
    memset(floods[b], 0, sizeof(floods[b]));
    memset(hopSum[b], 0, sizeof(hopSum[b]));
  }
  static uint16_t add(uint16_t a, uint16_t b) { return (uint32_t)a + b > 65535u ? 65535u : a + b; }

  uint16_t bucketTotal(uint8_t b) const {
    uint16_t n = 0;
    for (uint8_t g = 0; g < GroupCount; ++g) n = add(n, seen[b][g]);
    return n;
  }
  void finishMinute(uint16_t n) {
    minutes[minutesNext] = n;
    minutesNext = (minutesNext + 1) % HISTORY;
    ++finished;
  }

public:
  Window() {
    for (uint8_t b = 0; b < BUCKETS; ++b) clear(b);
    memset(minutes, 0, sizeof(minutes));
  }

  // Rolls the minutes forward to 'now' (millis; wrap-safe). Called before every read or write.
  void advance(uint32_t now) {
    if (!started) { started = true; headStart = now; return; }
    if ((int32_t)(now - headStart) < 0) return;              // a reader a hair behind the radio: nothing to roll
    uint32_t behind = (uint32_t)(now - headStart);
    if (behind >= (uint32_t)BUCKETS * BUCKET_MS) {          // a long quiet spell: everything expired
      uint32_t missed = behind / BUCKET_MS - 1;             // whole minutes after the current one: nothing was heard in them
      finishMinute(bucketTotal(head));
      if (missed > HISTORY) missed = HISTORY;               // older ones would be pushed out of the history anyway
      while (missed--) finishMinute(0);
      for (uint8_t b = 0; b < BUCKETS; ++b) clear(b);
      head = 0; headStart = now;
      return;
    }
    while (behind >= BUCKET_MS) {
      finishMinute(bucketTotal(head));
      head = (head + 1) % BUCKETS; clear(head);
      headStart += BUCKET_MS; behind -= BUCKET_MS;
    }
  }

  // Start of the minute the window is currently on. It changes exactly when the window rolls,
  // so a reader can tell "same minute as last time" without keeping its own clock.
  uint32_t rollMark(uint32_t now) { advance(now); return headStart; }

  // How many minutes have been finished so far (rolls the window to 'now' first).
  uint32_t finishedMinutes(uint32_t now) { advance(now); return finished; }
  // Packets heard in a finished minute: 0 = the newest finished minute, 1 = the one before ...
  // Only meaningful for ago < min(finishedMinutes, HISTORY).
  uint16_t minuteAgo(uint8_t ago) const { return minutes[(minutesNext + 2u * HISTORY - 1u - ago) % HISTORY]; }

  void record(uint32_t now, const Frame& f) {
    if (!f.ok) return;
    advance(now);
    seen[head][f.group] = add(seen[head][f.group], 1);
    if (f.flood) {
      floods[head][f.group] = add(floods[head][f.group], 1);
      hopSum[head][f.group] = add(hopSum[head][f.group], f.hops);
    }
  }
  void record(uint32_t now, const uint8_t* raw, int len) { record(now, parse(raw, len)); }

  uint32_t count(uint32_t now, uint8_t group) {
    advance(now);
    if (group >= GroupCount) return 0;
    uint32_t n = 0;
    for (uint8_t b = 0; b < BUCKETS; ++b) n += seen[b][group];
    return n;
  }
  uint32_t total(uint32_t now) {
    uint32_t n = 0;
    for (uint8_t g = 0; g < GroupCount; ++g) n += count(now, g);
    return n;
  }
  // Average hops of the flood-routed packets of a type, in tenths; -1 when there were none.
  int averageHopsTenths(uint32_t now, uint8_t group) {
    advance(now);
    if (group >= GroupCount) return -1;
    uint32_t n = 0, sum = 0;
    for (uint8_t b = 0; b < BUCKETS; ++b) { n += floods[b][group]; sum += hopSum[b][group]; }
    if (!n) return -1;
    return (int)((sum * 10 + n / 2) / n);
  }
};

}  // namespace LoRaFishRfStats
