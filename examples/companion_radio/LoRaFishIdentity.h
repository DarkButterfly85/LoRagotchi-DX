#pragma once
// LoRaFish static pet identity: the pet's name, species and colour genes in a file of their own.
//
//   /lorafish.id    main copy      (record + SafeSave trailer)
//   /lorafish.idt   new copy while it is being written
//   /lorafish.idb   previous good main copy
//
// It is written through LoRaFishSafeSave (tmp, read back, backup, rename), so the only checksum is the
// one SafeSave adds. The pet record (/lorafish.dat, LoRaFishState, magic LFM2, 32 bytes), the settings
// file (/lorafish.cfg), the radio LFG1 text, the egg records (LEG1/EGJ1) and the species IDs are NOT
// touched by anything in this file. If /lorafish.id is missing or damaged, nothing changes: the pet
// keeps the species and colours it already has, and shows no name of its own.
//
// Record, 27 bytes (little-endian), then the 8-byte SafeSave trailer = 35 bytes on flash:
//    0  4  magic "LFI1"
//    4  1  version (1)
//    5 17  name: ASCII 0x20..0x7E, NUL terminated, at most 16 characters, unused bytes 0
//   22  2  species id (uint16), the same IDs as LoRaFishSpecies (permanent protocol identities)
//   24  1  body gene     (LoRaFishColour::valid)
//   25  1  accent gene   (the scales; LoRaFishColour::valid)
//   26  1  eyes gene     (LoRaFishColour::valid)
//
// The file is created the first time a name is set or the species/colours change from what the pet had
// when the radio started. Storage is the same duck-typed store LoRaFishSafeSave takes (testable on a PC).

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "LoRaFishColour.h"
#include "LoRaFishSpecies.h"
#include "ui-new/LoRaFishSafeSave.h"

namespace LoRaFishIdentity {

static const size_t kNameMax = 16;                    // characters, not counting the NUL
static const size_t kRecord = 27;
static const size_t kSealed = kRecord + LoRaFishSafeSave::kTrailer;   // 35 bytes on flash per copy
static const uint8_t kVersion = 1;
static const char* const kMain = "/lorafish.id";
static const char* const kTmp = "/lorafish.idt";
static const char* const kBak = "/lorafish.idb";

struct Identity {
  char name[kNameMax + 1];     // "" = no name of its own
  uint16_t species;
  uint8_t body, accent, eyes;
};

inline bool same(const Identity& a, const Identity& b) {
  return strcmp(a.name, b.name) == 0 && a.species == b.species &&
         a.body == b.body && a.accent == b.accent && a.eyes == b.eyes;
}

enum NameResult : uint8_t { NameOk, NameTooLong, NameBadChar, NameNoPet, NameSaveFailed };

// A name is up to 16 characters of plain printable ASCII (space to ~). Empty is allowed (it clears the name).
inline NameResult checkName(const char* name) {
  if (!name) return NameOk;
  size_t n = 0;
  for (; name[n]; ++n) {
    if (n >= kNameMax) return NameTooLong;
    const unsigned char c = (unsigned char)name[n];
    if (c < 0x20 || c > 0x7E) return NameBadChar;
  }
  return NameOk;
}

inline bool genesValid(const Identity& id) {
  return LoRaFishColour::valid(id.body) && LoRaFishColour::valid(id.accent) && LoRaFishColour::valid(id.eyes);
}

// The record is only written for a complete, valid identity. Returns false (writes nothing) otherwise.
inline bool encode(const Identity& id, uint8_t* out /* kRecord bytes */) {
  if (checkName(id.name) != NameOk || !LoRaFishSpecies::known(id.species) || !genesValid(id)) return false;
  memset(out, 0, kRecord);
  memcpy(out, "LFI1", 4);
  out[4] = kVersion;
  memcpy(out + 5, id.name, strlen(id.name));          // out[5 + len] stays 0: the NUL
  out[22] = (uint8_t)id.species; out[23] = (uint8_t)(id.species >> 8);
  out[24] = id.body; out[25] = id.accent; out[26] = id.eyes;
  return true;
}

// True only for a record that is the right size, has the right magic and version, a known species and
// valid genes. A bad name does NOT make it invalid (see decode): the species and colours are still good.
inline bool recordValid(const uint8_t* rec, size_t len) {
  if (len != kRecord || memcmp(rec, "LFI1", 4) != 0 || rec[4] != kVersion) return false;
  const uint16_t species = (uint16_t)(rec[22] | (rec[23] << 8));
  return LoRaFishSpecies::known(species) && LoRaFishColour::valid(rec[24]) &&
         LoRaFishColour::valid(rec[25]) && LoRaFishColour::valid(rec[26]);
}

// Fills id from a valid record. A name that is not NUL terminated inside its 17 bytes, or has a byte
// outside 0x20..0x7E, or has non-zero bytes after the NUL, is treated as no name at all.
inline bool decode(const uint8_t* rec, size_t len, Identity& id) {
  if (!recordValid(rec, len)) return false;
  id.name[0] = 0;
  size_t n = 0;
  while (n <= kNameMax && rec[5 + n]) ++n;
  bool ok = n <= kNameMax;
  for (size_t i = 0; ok && i < n; ++i) ok = rec[5 + i] >= 0x20 && rec[5 + i] <= 0x7E;
  for (size_t i = n + 1; ok && i <= kNameMax; ++i) ok = rec[5 + i] == 0;
  if (ok) { memcpy(id.name, rec + 5, n); id.name[n] = 0; }
  id.species = (uint16_t)(rec[22] | (rec[23] << 8));
  id.body = rec[24]; id.accent = rec[25]; id.eyes = rec[26];
  return true;
}

inline LoRaFishSafeSave::Paths paths() {
  return LoRaFishSafeSave::Paths{kMain, kTmp, kBak, false};     // never existed without the trailer
}

// Reads /lorafish.id (or its tmp / backup copy). On success id is filled and the source says which copy;
// when nothing usable is found id is left exactly as the caller set it (the defaults) and None is returned.
template <class S>
inline LoRaFishSafeSave::Source load(S& s, Identity& id) {
  uint8_t rec[LoRaFishSafeSave::kMaxRecord];
  size_t len = 0;
  const LoRaFishSafeSave::Source src = LoRaFishSafeSave::load(s, recordValid, rec, &len, paths());
  if (src == LoRaFishSafeSave::None) return src;
  Identity got = id;
  if (!decode(rec, len, got)) return LoRaFishSafeSave::None;
  id = got;
  return src;
}

// true only when the new copy is in place as /lorafish.id.
template <class S>
inline bool commit(S& s, const Identity& id) {
  uint8_t rec[kRecord];
  if (!encode(id, rec)) return false;
  return LoRaFishSafeSave::commit(s, rec, kRecord, paths());
}

// "nova petname": the live species and colours plus a new name, saved as /lorafish.id and nothing else.
// *saved is filled only on NameOk.
template <class S>
inline NameResult saveWithName(S& s, const Identity& live, const char* name, Identity* saved) {
  const NameResult c = checkName(name);
  if (c != NameOk) return c;
  Identity next = live;
  strncpy(next.name, name ? name : "", kNameMax);
  next.name[kNameMax] = 0;
  if (!commit(s, next)) return NameSaveFailed;
  if (saved) *saved = next;
  return NameOk;
}

// The serial command (MyMesh.cpp) cannot see the UI's variables. The UI registers one function that
// applies a name; with none registered (no pet screen in this build) the command says so.
typedef NameResult (*NameSetter)(const char* name);
inline NameSetter& setterSlot() { static NameSetter f = 0; return f; }
inline NameResult requestName(const char* name) {
  const NameResult c = checkName(name);
  if (c != NameOk) return c;
  NameSetter f = setterSlot();
  return f ? f(name ? name : "") : NameNoPet;
}

}  // namespace LoRaFishIdentity
