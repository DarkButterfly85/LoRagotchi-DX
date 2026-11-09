#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

// Power-cut-safe pet save. The pet record itself is unchanged; the file around
// it gains an 8-byte trailer ("LSV1" + CRC-32 of the record) so a damaged copy
// can be told from a good one, and a second copy is kept as a backup.
//
//   /lorafish.dat  main copy      (record + trailer)
//   /lorafish.tmp  new copy while it is being written (record + trailer)
//   /lorafish.bak  previous good main copy (record + trailer)
//
// Save: write tmp, read it back, move the old main to bak, move tmp over main.
// A power cut at any step leaves at least one complete, checksummed copy.
// Load: a complete tmp is the newest save, then main, then bak. A main file
// from older firmware (bare record, no trailer) is still accepted once.
//
// Storage is passed in (so it can be tested on a PC) and must offer:
//   bool hasRename() const;            // false: key/value store, no tmp file
//   bool write(path, data, len);       // replace whole file; true if complete
//   int  read(path, buf, cap);         // length, -1 missing, -2 unreadable/too big
//   bool exists(path); bool remove(path);
//   bool rename(from, to);             // destination replaced if present
namespace LoRaFishSafeSave {

static const size_t kTrailer = 8;
static const size_t kMaxRecord = 64;  // pet record is 32 bytes today
static const size_t kMaxBlob = kMaxRecord + kTrailer;
static const char* const kMain = "/lorafish.dat";
static const char* const kTmp = "/lorafish.tmp";
static const char* const kBak = "/lorafish.bak";

enum Source { None, Main, Legacy, Tmp, Bak };

inline uint32_t crc32(const uint8_t* data, size_t len) {
  uint32_t crc = 0xFFFFFFFFUL;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (int b = 0; b < 8; ++b) crc = (crc >> 1) ^ (0xEDB88320UL & (0UL - (crc & 1UL)));
  }
  return ~crc;
}

// out must hold len + kTrailer. Returns the sealed length.
inline size_t seal(const uint8_t* rec, size_t len, uint8_t* out) {
  memcpy(out, rec, len);
  memcpy(out + len, "LSV1", 4);
  const uint32_t crc = crc32(rec, len);
  for (int i = 0; i < 4; ++i) out[len + 4 + i] = (uint8_t)(crc >> (8 * i));
  return len + kTrailer;
}

// True when blob is record + a correct trailer; the record length is returned.
inline bool unseal(const uint8_t* blob, size_t len, size_t* recLen) {
  if (len <= kTrailer || len > kMaxBlob) return false;
  const size_t n = len - kTrailer;
  if (memcmp(blob + n, "LSV1", 4) != 0) return false;
  uint32_t stored = 0;
  for (int i = 0; i < 4; ++i) stored |= (uint32_t)blob[n + 4 + i] << (8 * i);
  if (stored != crc32(blob, n)) return false;
  *recLen = n;
  return true;
}

template <class S>
inline bool readSealed(S& s, const char* path, uint8_t* blob, size_t* blobLen, size_t* recLen) {
  const int n = s.read(path, blob, kMaxBlob);
  if (n <= 0) return false;
  *blobLen = (size_t)n;
  return unseal(blob, (size_t)n, recLen);
}

// valid(record, length) decides whether a record is a genuine pet (magic, size).
// rec must hold kMaxRecord bytes.
template <class S, class V>
inline Source load(S& s, V valid, uint8_t* rec, size_t* recLen) {
  uint8_t blob[kMaxBlob];
  size_t blobLen = 0, n = 0;
  if (s.hasRename() && readSealed(s, kTmp, blob, &blobLen, &n) && valid(blob, n)) {
    memcpy(rec, blob, n); *recLen = n; return Tmp;
  }
  const int raw = s.read(kMain, blob, kMaxBlob);
  if (raw > 0) {
    if (unseal(blob, (size_t)raw, &n)) {
      if (valid(blob, n)) { memcpy(rec, blob, n); *recLen = n; return Main; }
    } else if (valid(blob, (size_t)raw)) {
      memcpy(rec, blob, (size_t)raw); *recLen = (size_t)raw; return Legacy;  // older firmware
    }
  }
  if (readSealed(s, kBak, blob, &blobLen, &n) && valid(blob, n)) {
    memcpy(rec, blob, n); *recLen = n; return Bak;
  }
  return None;
}

// Write path, then read it back and compare.
template <class S>
inline bool writeVerified(S& s, const char* path, const uint8_t* blob, size_t len) {
  if (!s.write(path, blob, len)) return false;
  uint8_t check[kMaxBlob];
  return s.read(path, check, kMaxBlob) == (int)len && memcmp(check, blob, len) == 0;
}

// Returns true only when the new copy is in place as the main file.
template <class S>
inline bool commit(S& s, const uint8_t* rec, size_t len) {
  if (len == 0 || len > kMaxRecord) return false;
  uint8_t blob[kMaxBlob];
  const size_t blobLen = seal(rec, len, blob);

  uint8_t oldBlob[kMaxBlob];
  size_t oldBlobLen = 0, oldRec = 0;
  const bool oldGood = readSealed(s, kMain, oldBlob, &oldBlobLen, &oldRec);

  if (s.hasRename()) {
    if (!writeVerified(s, kTmp, blob, blobLen)) { s.remove(kTmp); return false; }
    // Only a main that passes its checksum may replace the backup.
    if (oldGood && !s.rename(kMain, kBak)) return false;
    return s.rename(kTmp, kMain);
  }
  // Key/value store: each write is already all-or-nothing, so no tmp copy.
  if (oldGood && !writeVerified(s, kBak, oldBlob, oldBlobLen)) return false;
  return writeVerified(s, kMain, blob, blobLen);
}

}  // namespace LoRaFishSafeSave
