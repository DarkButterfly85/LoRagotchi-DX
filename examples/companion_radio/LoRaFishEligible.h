#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ui-new/LoRaFishText.h"

// Shared DX contact eligibility, used by the UI visit picker (ui-new/UITask.cpp) and the
// 'nova contacts' serial command (MyMesh.cpp). Include only after ContactInfo and the
// ADV_TYPE_* constants are declared. Nothing here touches the LFG1 wire format, contact
// storage or the settings files.

inline bool loRaFishDXEligible(const ContactInfo& c) {
  // A tank remains an honest MeshCore repeater advert, not a companion that
  // silently forwards. Only explicitly marked tanks join the visit picker.
  // Names are discovery hints, not authentication; the transaction still binds
  // to the selected full public key and requires the normal LFG1 handshake.
  const bool tank = c.type == ADV_TYPE_REPEATER &&
      !strncmp(c.name, "LRX1 ", 5);
  return (c.type == ADV_TYPE_CHAT || tank) && LoRaFishText::hasFish(c.name, sizeof(c.name));
}

namespace NovaContacts {

static constexpr unsigned kMaxEntries = 16;   // most contacts listed
static constexpr size_t kMaxNameBytes = 32;   // names are cut to this many bytes
static constexpr size_t kIdBytes = 6;         // short id: first 6 public-key bytes, 12 hex chars

// Appends the JSON string body (no quotes) for a contact name: truncated to kMaxNameBytes at a
// UTF-8 character boundary (also stopping at the first invalid sequence), with quotes,
// backslashes and control characters (< 0x20, 0x7F) escaped. Returns the bytes written;
// out is NUL-terminated and needs 6 * kMaxNameBytes + 1 bytes.
inline size_t escapeName(char* out, const char* name, size_t capacity) {
  char tmp[kMaxNameBytes + 1];
  size_t n = 0;
  while (n < capacity && n < kMaxNameBytes && name[n]) { tmp[n] = name[n]; ++n; }
  tmp[n] = 0;
  n = mesh::validUtf8PrefixLength(tmp, n);
  size_t o = 0;
  for (size_t i = 0; i < n; ++i) {
    const uint8_t b = (uint8_t)tmp[i];
    if (b == '"' || b == '\\') { out[o++] = '\\'; out[o++] = (char)b; }
    else if (b < 0x20 || b == 0x7F) { o += (size_t)snprintf(out + o, 7, "\\u%04x", (unsigned)b); }
    else out[o++] = (char)b;
  }
  out[o] = 0;
  return o;
}

// Streams {"contacts":[{"n":"name","id":"hex12"},...]} (one line, no newline) to sink.write(ptr,len).
// getContact(i, ContactInfo&) returns false past the end of the table (index counted the same
// way the picker counts). Only loRaFishDXEligible contacts are listed, at most kMaxEntries.
template <typename Sink, typename GetContact>
inline unsigned writeJson(Sink& sink, GetContact getContact) {
  static const char* const hex = "0123456789abcdef";
  sink.write("{\"contacts\":[", 13);
  unsigned count = 0;
  for (uint32_t i = 0; count < kMaxEntries; ++i) {
    ContactInfo c;
    if (!getContact(i, c)) break;
    if (!loRaFishDXEligible(c)) continue;
    char entry[6 * kMaxNameBytes + 1 + 40];
    size_t o = 0;
    if (count) entry[o++] = ',';
    memcpy(entry + o, "{\"n\":\"", 6); o += 6;
    o += escapeName(entry + o, c.name, sizeof(c.name));
    memcpy(entry + o, "\",\"id\":\"", 8); o += 8;
    for (size_t k = 0; k < kIdBytes; ++k) {
      entry[o++] = hex[c.id.pub_key[k] >> 4];
      entry[o++] = hex[c.id.pub_key[k] & 15];
    }
    memcpy(entry + o, "\"}", 2); o += 2;
    sink.write(entry, o);
    ++count;
  }
  sink.write("]}", 2);
  return count;
}

}  // namespace NovaContacts
