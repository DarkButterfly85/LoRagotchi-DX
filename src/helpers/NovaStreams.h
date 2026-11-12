#pragma once
// Nova dashboard data streams: what the dashboard's Mesh analyzer, Best uplink, Repeaters, Speed, Battery
// and Messages-you-sent panels read from the radio. Pure logic: no Arduino, no radio, no storage, no
// serial port; MyMesh.cpp feeds it and writes what it produces, so it is tested on the host
// (test/test_nova_streams). The line shapes are the ones the dashboard decoder reads (docs/index.html of the
// Nova repo: onMeshLine, onFrame/render, renderBatt, renderDeliveries).
//
//   mesh line     {"mesh":{"nf":..,"sf":..,"bw":..,"cr":..,"rx":..,"tx":..,"ty":[16 counts],"p":[[age_ms,rssi,snr4,type,hops,len,route,tx,"id","src"],..]}}
//                 built by meshscope::Scope::line (MeshScope.h). At most one a second, and an empty one every 10 s so the
//                 page can tell the stream is alive.
//   status frame  {"nova":1,"t":ms,"bat":{mv,pct,chg,trend,hrs,hist[]},"gps":{fix[,lat,lon,sats,spd,mov,course]},
//                 "links":[{id,name,best,sc,rel,lq,snr,rssi,age,hit,n}],"best":N,"dl":{sent,rep,ok,fail,list[]},
//                 "diag":{rx,tx,snr,last_rx_s,up_s}}
//                 One line, at most one every 5 s, and only as the answer to a dashboard request. It has no "ed" key (a line
//                 with "ed":"dx-pro" is read as a hello) and every key the page reads: the page replaces its whole frame with
//                 each one, so a frame is never partial. Keys the firmware has no data for are left out (trip, cov, quiet, v, prof).
//   battery reply {"nova_ok":"battery","mv":N,"pct":N,"chg":0|1}   (the answer of the explicit battery command)
//
// What is derived, not measured (said here so nobody reads more into it than there is):
//   * links: the repeaters this radio hears are the last hop of the flood packets it receives, plus the zero-hop adverts that say
//     "repeater". Their score is an estimate from the SNR and from how recently they were heard (lq from the SNR, rel from the
//     age); the firmware has no ack-based reliability, so "n" is 0 and the page shows a dash in the Acks column.
//   * gps speed and heading are worked out from successive fixes (the location provider gives position only).
//   * deliveries: direct messages sent from the phone app, delivered when the ack comes, failed when it does not in time.
//     Channel messages are not tracked (the radio cannot tell that a repeater heard them).
//   * battery history is one sample every 150 s (what the page's chart assumes), at most 96 (4 hours).
#include <math.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "MeshScope.h"

namespace NovaStreams {

static constexpr uint32_t MESH_GAP_MS = 1000;        // mesh lines: at most one a second
static constexpr uint32_t MESH_BEAT_MS = 10000;      // an empty mesh line this often, so the page knows the stream is alive
static constexpr uint32_t STATUS_GAP_MS = 5000;      // status frames that ride on the mesh request: at most one every 5 s
static constexpr uint32_t STATUS_CMD_GAP_MS = 1000;  // the explicit status command: at most one a second
static constexpr size_t MESH_CAP = 1280, STATUS_CAP = 2816, OUTBOX_CAP = 4096;

// ---- small pieces -----------------------------------------------------------------------------------------

struct Gate {                                         // "not again within gap ms of the last time", surviving the millis() wrap
  uint32_t at = 0; bool armed = false;
  bool ready(uint32_t now, uint32_t gap) const { return !armed || (uint32_t)(now - at) >= gap; }
  void mark(uint32_t now) { armed = true; at = now; }
};

struct J {                                            // bounded JSON writer: never writes past cap, ok goes false instead
  char* b; size_t cap; size_t n; bool ok;
  J(char* buf, size_t c) : b(buf), cap(c), n(0), ok(buf && c > 1) { if (ok) b[0] = 0; }
  void s(const char* t) { size_t l = strlen(t); if (!ok || n + l + 1 > cap) { ok = false; return; } memcpy(b + n, t, l + 1); n += l; }
  void f(const char* fmt, ...) {
    if (!ok) return;
    va_list ap; va_start(ap, fmt);
    int r = vsnprintf(b + n, cap - n, fmt, ap);
    va_end(ap);
    if (r < 0 || (size_t)r >= cap - n) { ok = false; return; }
    n += (size_t)r;
  }
  void esc(const char* t, size_t max) {               // a name is data, not markup: printable ASCII, no quote or backslash
    for (size_t i = 0; t && t[i] && i < max; i++) {
      char c = (t[i] >= 32 && t[i] < 127 && t[i] != '"' && t[i] != '\\') ? t[i] : '?';
      if (!ok || n + 2 > cap) { ok = false; return; }
      b[n++] = c; b[n] = 0;
    }
  }
};

// Text waiting for the serial port. Lines are written in order, at the link's pace (the caller takes a few bytes a time), so
// the radio loop never waits on the port and a line is never cut by another writer: see midLine().
struct Outbox {
  char buf[OUTBOX_CAP];
  size_t len = 0, pos = 0;
  size_t pending() const { return len - pos; }
  bool midLine() const { return pos > 0 && pos < len && buf[pos - 1] != '\n'; }   // part of a line has gone out
  char* room(size_t& cap) {                           // where the next line can be built, and how many bytes it may use
    if (pos == len) len = pos = 0;
    cap = OUTBOX_CAP - len - 1;                       // one byte stays for the line end
    return buf + len;
  }
  void commit(size_t n) { len += n; buf[len++] = '\n'; }
  bool append(const char* s) {                        // a short whole line (a command reply) behind what is waiting
    size_t cap; char* p = room(cap); size_t n = strlen(s);
    if (n > cap) return false;
    memcpy(p, s, n); commit(n); return true;
  }
  const uint8_t* data() const { return (const uint8_t*)buf + pos; }
  void consumed(size_t n) { pos += n; if (pos >= len) len = pos = 0; }
};

// ---- battery ----------------------------------------------------------------------------------------------

struct Battery {
  static constexpr int N = 96;                        // 96 samples x 150 s = 4 hours
  static constexpr uint32_t STEP_MS = 150000;
  uint16_t hist[N]; int n = 0;
  uint32_t lastAt = 0;
  uint16_t mv = 0; bool chg = false, seen = false;
  int (*pctOf)(uint16_t) = nullptr;                   // the radio's voltage-to-percent curve (LoRaFishBattery::percent); a straight 3.3-4.2 V line if unset

  void sample(uint32_t now, uint16_t mv_now, bool charging) {
    if (mv_now == 0) return;                          // no reading
    if (seen && charging != chg) n = 0;               // plugged in or out: the history starts again (the page says so too)
    chg = charging; mv = mv_now; seen = true;
    if (n == 0 || (uint32_t)(now - lastAt) >= STEP_MS) {
      if (n == N) { memmove(hist, hist + 1, (N - 1) * sizeof(hist[0])); n = N - 1; }
      hist[n++] = mv_now; lastAt = now;
    }
  }
  int pctFor(uint16_t v) const {
    if (pctOf) return pctOf(v);
    int p = ((int)v - 3300) * 100 / 900; return p < 0 ? 0 : p > 100 ? 100 : p;
  }
  int pct() const { return mv ? pctFor(mv) : -1; }
  // percent per hour over the history (needs 30 minutes of it); false when there is not enough
  bool trendPerHour(float& out) const {
    if (n < 13) return false;
    double sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (int i = 0; i < n; i++) { double x = i * 150.0 / 3600.0, y = pctFor(hist[i]); sx += x; sy += y; sxx += x * x; sxy += x * y; }
    double d = n * sxx - sx * sx; if (d <= 0) return false;
    out = (float)((n * sxy - sx * sy) / d); return true;
  }
  bool hoursLeft(float& out) const {                  // only while discharging at a clear rate
    float t; if (chg || !mv || !trendPerHour(t) || t > -0.1f) return false;
    out = (float)pct() / -t; if (out > 99.9f) out = 99.9f; return true;
  }
};

// ---- gps --------------------------------------------------------------------------------------------------

struct Gps {
  bool fix = false, moving = false;
  int32_t lat = 0, lon = 0; int sats = 0;
  float kmh = 0; int course = -1;                     // course -1 = unknown
  bool havePrev = false, haveSpeed = false; int32_t plat = 0, plon = 0; uint32_t pAt = 0;

  void update(uint32_t now, bool valid, int32_t lat_e6, int32_t lon_e6, int sat_count) {
    if (!valid) { fix = moving = havePrev = haveSpeed = false; kmh = 0; course = -1; return; }
    fix = true; lat = lat_e6; lon = lon_e6; sats = sat_count;
    if (!havePrev) { plat = lat_e6; plon = lon_e6; pAt = now; havePrev = true; return; }
    const uint32_t dt = now - pAt;
    if (dt < 2000) return;                            // work speed out over 2 s or more, so a fix's own jitter does not show
    const float dy = (float)(lat_e6 - plat) * 0.111195f;                                         // metres
    const float dx = (float)(lon_e6 - plon) * 0.111195f * cosf((float)lat_e6 * 1e-6f * 0.0174533f);
    const float dist = sqrtf(dx * dx + dy * dy);
    float v = dist < 2.0f ? 0.0f : dist / ((float)dt / 1000.0f) * 3.6f;                         // under 2 m is noise
    kmh = haveSpeed ? 0.5f * kmh + 0.5f * v : v; haveSpeed = true;
    moving = kmh >= 3.0f;
    if (moving && dist >= 5.0f) { int c = (int)(atan2f(dx, dy) * 57.29578f + 360.5f); course = c % 360; }
    if (!moving) course = -1;
    plat = lat_e6; plon = lon_e6; pAt = now;
  }
};

// ---- repeaters this radio hears ---------------------------------------------------------------------------

struct Links {
  static constexpr int N = 12, SHOWN = 8;
  static constexpr uint32_t FORGET_MS = 30UL * 60UL * 1000UL;
  static constexpr int BEST_MIN = 40;                 // a repeater counts as an uplink from this score
  struct E { uint8_t key[3]; uint8_t len; int16_t rssi; float snr; uint32_t last_ms, hits, tryAt; char name[24]; bool used, named; };
  E e[N];
  Links() { memset(e, 0, sizeof(e)); }

  void heard(uint32_t now, const uint8_t* key, uint8_t len, float rssi, float snr) {
    if (!key || len < 1 || len > 3) return;
    int at = -1; bool known = false;
    for (int i = 0; i < N; i++) {
      if (!e[i].used) { if (at < 0) at = i; continue; }
      if (e[i].len == len && memcmp(e[i].key, key, len) == 0) { at = i; known = true; break; }
    }
    if (at < 0) { uint32_t worst = 0; for (int i = 0; i < N; i++) { uint32_t a = now - e[i].last_ms; if (a >= worst) { worst = a; at = i; } } }   // full: replace the stalest
    E& r = e[at];
    if (!known) { memset(&r, 0, sizeof(r)); r.used = true; r.len = len; memcpy(r.key, key, len); r.snr = snr; }
    else r.snr = 0.7f * r.snr + 0.3f * snr;
    r.rssi = (int16_t)(rssi < -32000 ? -32000 : rssi > 32000 ? 32000 : rssi);
    r.last_ms = now; r.hits++;
  }
  // from what the radio hands us (rx): the last hop of a flood packet, or an advert from a repeater heard direct
  void onRx(uint32_t now, float rssi, float snr, uint8_t type, uint8_t route, uint8_t hops, uint8_t hash_size,
            const uint8_t* path, const uint8_t* payload, int payload_len) {
    if (route & 2) return;                            // a direct-routed packet's path is the way still to go, not the way it came
    const uint8_t n = hash_size > 3 ? 3 : hash_size;
    if (hops > 0 && path && n >= 1) { heard(now, path + (hops - 1) * hash_size, n, rssi, snr); return; }
    if (hops == 0 && type == 4 && payload && payload_len >= 101 && (payload[100] & 0x0F) == 2 && n >= 1)   // advert whose type says repeater
      heard(now, payload, n, rssi, snr);
  }

  static int clamp100(int v) { return v < 0 ? 0 : v > 100 ? 100 : v; }
  static int lq(const E& r) { return clamp100((int)((r.snr + 15.0f) * 5.0f + 0.5f)); }
  static int rel(const E& r, uint32_t now) {          // freshness: 100 under a minute, 0 from ten minutes
    uint32_t s = (now - r.last_ms) / 1000u;
    return s <= 60 ? 100 : s >= 600 ? 0 : (int)(100 - (s - 60) * 100 / 540);
  }
  static int score(const E& r, uint32_t now) { return (7 * lq(r) + 3 * rel(r, now) + 5) / 10; }   // mostly the SNR, some of how recently it was heard
  bool live(const E& r, uint32_t now) const { return r.used && (now - r.last_ms) < FORGET_MS; }

  int count(uint32_t now) const { int c = 0; for (int i = 0; i < N; i++) if (live(e[i], now)) c++; return c; }
  bool hasBest(uint32_t now) const { for (int i = 0; i < N; i++) if (live(e[i], now) && score(e[i], now) >= BEST_MIN) return true; return false; }
  // best first; returns how many indices were written (at most max)
  int ranked(uint32_t now, int* order, int max) const {
    int c = 0;
    for (int i = 0; i < N; i++) if (live(e[i], now)) order[c++] = i;
    for (int a = 0; a < c; a++) for (int b = a + 1; b < c; b++)
      if (score(e[order[b]], now) > score(e[order[a]], now)) { int t = order[a]; order[a] = order[b]; order[b] = t; }
    return c < max ? c : max;
  }
  // one repeater whose name was not looked up yet (and not tried in the last 30 s); -1 if none
  int nextUnnamed(uint32_t now) const {
    for (int i = 0; i < N; i++) if (live(e[i], now) && !e[i].named && (e[i].tryAt == 0 || now - e[i].tryAt >= 30000u)) return i;
    return -1;
  }
  void triedName(int i, uint32_t now) { e[i].tryAt = now ? now : 1; }
  void setName(int i, const char* name) { strncpy(e[i].name, name, sizeof(e[i].name) - 1); e[i].name[sizeof(e[i].name) - 1] = 0; e[i].named = true; }
};

// ---- messages sent from the phone app --------------------------------------------------------------------

struct Deliveries {
  static constexpr int N = 8, SHOWN = 6;
  static constexpr uint32_t GRACE_MS = 3000;          // an ack this much after the estimated time still counts as in time
  enum St : uint8_t { Sent, Delivered, Failed };
  struct D { char who[24]; uint32_t ack, sent_ms, rtt, timeout_ms; uint8_t st, flood, link, used; };
  D d[N]; uint32_t head = 0;                          // head = messages ever recorded
  uint32_t sent = 0, ok = 0, fail = 0;
  Deliveries() { memset(d, 0, sizeof(d)); }

  void onSent(uint32_t now, const char* who, uint32_t ack, uint32_t timeout_ms, bool flood, bool link_ok) {
    D& r = d[head % N]; head++; sent++;
    memset(&r, 0, sizeof(r));
    strncpy(r.who, who ? who : "", sizeof(r.who) - 1);
    r.ack = ack; r.sent_ms = now; r.timeout_ms = timeout_ms; r.st = Sent; r.flood = flood ? 1 : 0; r.link = link_ok ? 1 : 0; r.used = 1;
  }
  bool onAck(uint32_t now, uint32_t ack) {            // true when it was one of ours
    const uint32_t have = head < (uint32_t)N ? head : (uint32_t)N;
    for (uint32_t k = 0; k < have; k++) {
      D& r = d[(head - 1 - k) % N];
      if (!r.used || r.ack != ack || r.st == Delivered) continue;
      if (r.st == Failed && fail) fail--;             // it came after all, late
      r.st = Delivered; r.rtt = now - r.sent_ms; ok++; return true;
    }
    return false;
  }
  void tick(uint32_t now) {
    for (int i = 0; i < N; i++) {
      D& r = d[i];
      if (r.used && r.st == Sent && (uint32_t)(now - r.sent_ms) > r.timeout_ms + GRACE_MS) { r.st = Failed; fail++; }
    }
  }
};

// ---- everything together ----------------------------------------------------------------------------------

struct Hub {
  meshscope::Scope scope;
  Links links;
  Deliveries dl;
  Battery bat;
  Gps gps;
  Outbox out;
  // radio state, kept up to date by MyMesh (cheap reads, about once a second)
  int nf = 0, sf = 0, cr = 0; float bw = 0;
  bool haveRx = false; float lastSnr = 0; uint32_t lastRxMs = 0;
  // pacing
  Gate meshGate, statusGate;
  uint32_t meshBeatAt = 0; bool meshBeatArmed = false;
  bool contactsDue = false;                            // a contacts request that arrived while a line was half written

  void onRx(uint32_t now, float rssi, float snr, uint8_t type, uint8_t route, uint8_t hops, uint8_t hash_size, const uint8_t* path,
            const uint8_t* payload, int payload_len, int total_len) {
    scope.onRx(now, rssi, snr, type, route, hops, hash_size, path, payload, payload_len, total_len);
    links.onRx(now, rssi, snr, type, route, hops, hash_size, path, payload, payload_len);
    haveRx = true; lastSnr = snr; lastRxMs = now;
  }
  void onTx(uint32_t now, uint8_t type, uint8_t route, int total_len) { scope.onTx(now, type, route, total_len); }
  void tick(uint32_t now) { dl.tick(now); }

  // The dashboard asked for the mesh stream. Queues the mesh line when there is something to say (new packets, or the
  // 10 s beat). Never more than one a second, nothing at all unless asked.
  bool askMesh(uint32_t now) {
    if (!meshGate.ready(now, MESH_GAP_MS)) return false;
    const bool beat = !meshBeatArmed || (uint32_t)(now - meshBeatAt) >= MESH_BEAT_MS;
    size_t cap; char* p = out.room(cap); if (cap > MESH_CAP) cap = MESH_CAP;
    size_t n = scope.line(now, p, cap, nf, sf, bw, cr, beat);
    if (!n) return false;
    out.commit(n); meshGate.mark(now);
    if (beat) { meshBeatArmed = true; meshBeatAt = now; }
    return true;
  }
  // The dashboard asked for the status frame (gap = the least time between two frames).
  bool askStatus(uint32_t now, uint32_t gap) {
    if (!statusGate.ready(now, gap)) return false;
    size_t cap; char* p = out.room(cap); if (cap > STATUS_CAP) cap = STATUS_CAP;
    size_t n = statusLine(now, p, cap);
    if (!n) return false;
    out.commit(n); statusGate.mark(now);
    return true;
  }

  size_t batteryReply(char* o, size_t cap) const {    // {"nova_ok":"battery",...} or an error; one line, no line end
    if (!o || cap == 0) return 0;
    int n = bat.mv ? snprintf(o, cap, "{\"nova_ok\":\"battery\",\"mv\":%u,\"pct\":%d,\"chg\":%d}", (unsigned)bat.mv, bat.pct(), bat.chg ? 1 : 0)
                   : snprintf(o, cap, "{\"nova_error\":\"battery_no_reading\"}");
    if (n < 0 || (size_t)n >= cap) { o[0] = 0; return 0; }
    return (size_t)n;
  }

  // The whole status frame, one line, no line end. 0 if it does not fit in cap.
  size_t statusLine(uint32_t now, char* o, size_t cap) const {
    J j(o, cap);
    j.f("{\"nova\":1,\"t\":%lu", (unsigned long)now);

    // battery
    float tr = 0, hl = 0; const bool hasTr = bat.trendPerHour(tr), hasHl = bat.hoursLeft(hl);
    j.f(",\"bat\":{\"mv\":%u,\"pct\":%d,\"chg\":%d,\"trend\":", (unsigned)bat.mv, bat.pct(), bat.chg ? 1 : 0);
    if (hasTr) j.f("%.1f", (double)tr); else j.s("null");
    j.s(",\"hrs\":"); if (hasHl) j.f("%.1f", (double)hl); else j.s("null");
    j.s(",\"hist\":[");
    for (int i = 0; i < bat.n; i++) j.f("%s%u", i ? "," : "", (unsigned)bat.hist[i]);
    j.s("]}");

    // gps
    j.f(",\"gps\":{\"fix\":%d", gps.fix ? 1 : 0);
    if (gps.fix) {
      j.f(",\"lat\":%.6f,\"lon\":%.6f,\"sats\":%d,\"spd\":%d,\"mov\":%d,\"course\":", (double)gps.lat / 1e6, (double)gps.lon / 1e6, gps.sats,
          (int)(gps.kmh + 0.5f), gps.moving ? 1 : 0);
      if (gps.course >= 0) j.f("%d", gps.course); else j.s("null");
    }
    j.s("}");

    // repeaters, best first
    int order[Links::N];
    const int nrank = links.ranked(now, order, Links::SHOWN);
    int bestKey = -1;
    j.s(",\"links\":[");
    for (int k = 0; k < nrank; k++) {
      const Links::E& u = links.e[order[k]];
      const int sc = Links::score(u, now);
      const bool best = (k == 0 && sc >= Links::BEST_MIN);
      if (best) bestKey = u.key[0];
      char id[8];
      if (u.len >= 3) snprintf(id, sizeof(id), "%02X%02X%02X", u.key[0], u.key[1], u.key[2]);
      else if (u.len == 2) snprintf(id, sizeof(id), "%02X%02X", u.key[0], u.key[1]);
      else snprintf(id, sizeof(id), "%02X", u.key[0]);
      j.f("%s{\"id\":\"%s\",\"name\":\"", k ? "," : "", id);
      j.esc(u.name, sizeof(u.name) - 1);
      j.f("\",\"best\":%d,\"sc\":%d,\"rel\":%d,\"lq\":%d,\"snr\":%.1f,\"rssi\":%d,\"age\":%lu,\"hit\":%lu,\"n\":0}", best ? 1 : 0, sc,
          Links::rel(u, now), Links::lq(u), (double)u.snr, (int)u.rssi, (unsigned long)((now - u.last_ms) / 1000u), (unsigned long)u.hits);
    }
    j.s("]");
    j.f(",\"best\":%d", bestKey);                     // the page finds the best one by the "best" flag in the list; this is the original key too

    // messages sent
    j.f(",\"dl\":{\"sent\":%lu,\"rep\":0,\"ok\":%lu,\"fail\":%lu,\"list\":[", (unsigned long)dl.sent, (unsigned long)dl.ok, (unsigned long)dl.fail);
    const uint32_t have = dl.head < (uint32_t)Deliveries::N ? dl.head : (uint32_t)Deliveries::N;
    for (uint32_t k = 0; k < have && k < (uint32_t)Deliveries::SHOWN; k++) {
      const Deliveries::D& r = dl.d[(dl.head - 1 - k) % Deliveries::N];
      j.f("%s{\"who\":\"", k ? "," : ""); j.esc(r.who, sizeof(r.who) - 1);
      j.f("\",\"st\":\"%s\",\"via\":-1,\"rtt\":%lu,\"age\":%lu,\"flood\":%d,\"link\":%d,\"chan\":0}",
          r.st == Deliveries::Delivered ? "delivered" : r.st == Deliveries::Failed ? "failed" : "sent", (unsigned long)r.rtt,
          (unsigned long)((now - r.sent_ms) / 1000u), r.flood ? 1 : 0, r.link ? 1 : 0);
    }
    j.s("]}");

    // diagnostics
    j.f(",\"diag\":{\"rx\":%lu,\"tx\":%lu,\"snr\":", (unsigned long)scope.rx, (unsigned long)scope.tx);
    if (haveRx) j.f("%.1f", (double)lastSnr); else j.s("null");
    j.f(",\"last_rx_s\":%lu,\"up_s\":%lu}}", haveRx ? (unsigned long)((now - lastRxMs) / 1000u) : 0ul, (unsigned long)(now / 1000u));
    return j.ok ? j.n : 0;
  }
};

inline Hub& hub() { static Hub h; return h; }

}  // namespace NovaStreams
