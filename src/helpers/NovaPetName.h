#pragma once
// Nova dashboard link: the pet's name on its way to the dashboard.
// Pure text handling, no Arduino, no radio, no storage; host tested (test/test_nova_pet_name).
//
// The pet's own name lives in /lorafish.id (LoRaFishIdentity.h, 16 characters at most, printable ASCII
// 0x20..0x7E). It is NEVER the radio's node name. This file does three jobs:
//   prepare()   the argument of "nova petname <name>": trim, "-" clears, refuse anything that would
//               make a bad name or a bad JSON line (longer than 16, not printable ASCII, a '"' or a '\\')
//   jsonSafe()  the name as it goes into a JSON line: printable ASCII only, '"' and '\\' stripped, 16 at
//               most. Applied to every name that is printed into a line, so even a name that is already
//               stored (older file, other tool) can never break the line.
//   reply()     the one JSON line that answers "nova petname":
//                 {"nova_ok":"petname","name":"Fluffy"}   saved (name "" = cleared)
//                 {"nova_error":"petname_<why>"}          refused or failed, nothing changed
//                 {"nova_unavailable":"petname"}          this build has no pet name to set
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace NovaPetName {

static const size_t kMax = 16;   // same limit as LoRaFishIdentity::kNameMax

enum class Status { Ok, Cleared, Usage, TooLong, NonAscii, JsonChar, NoPet, SaveFailed };

// out needs kMax + 1 bytes (cap >= kMax + 1). Ok: out holds the trimmed name. Cleared: out is "".
// Any refusal leaves out "".
static inline Status prepare(const char* arg, char* out, size_t cap) {
  if (!out || cap < kMax + 1) return Status::Usage;
  out[0] = 0;
  if (!arg) return Status::Usage;
  while (*arg == ' ') arg++;
  size_t n = strlen(arg);
  while (n && arg[n - 1] == ' ') n--;
  if (n == 0) return Status::Usage;
  if (n == 1 && arg[0] == '-') return Status::Cleared;      // the dashboard sends "-" to clear
  bool jsonChar = false;
  for (size_t i = 0; i < n; i++) {
    const unsigned char c = (unsigned char)arg[i];
    if (c < 0x20 || c > 0x7E) return Status::NonAscii;
    if (c == '"' || c == '\\') jsonChar = true;
  }
  if (jsonChar) return Status::JsonChar;
  if (n > kMax) return Status::TooLong;
  memcpy(out, arg, n);
  out[n] = 0;
  return Status::Ok;
}

// Copies the printable-ASCII characters of in, leaving out '"' and '\\', at most kMax of them.
// out needs kMax + 1 bytes (cap >= kMax + 1); smaller buffers get "".
static inline void jsonSafe(const char* in, char* out, size_t cap) {
  if (!out || cap == 0) return;
  out[0] = 0;
  if (!in || cap < kMax + 1) return;
  size_t n = 0;
  for (; *in && n < kMax; ++in) {
    const unsigned char c = (unsigned char)*in;
    if (c < 0x20 || c > 0x7E || c == '"' || c == '\\') continue;
    out[n++] = (char)c;
  }
  out[n] = 0;
}

// Writes the reply line (no line ending) and returns its length; 0 (and "") if it does not fit.
// name is only used for Ok and Cleared, and is made JSON safe here.
static inline size_t reply(Status s, const char* name, char* out, size_t cap) {
  if (!out || cap == 0) return 0;
  out[0] = 0;
  int n = 0;
  switch (s) {
    case Status::Ok:
    case Status::Cleared: {
      char safe[kMax + 1];
      jsonSafe(s == Status::Ok ? name : "", safe, sizeof(safe));
      n = snprintf(out, cap, "{\"nova_ok\":\"petname\",\"name\":\"%s\"}", safe);
      break;
    }
    case Status::Usage:      n = snprintf(out, cap, "{\"nova_error\":\"petname_usage\"}"); break;
    case Status::TooLong:    n = snprintf(out, cap, "{\"nova_error\":\"petname_too_long\"}"); break;
    case Status::NonAscii:   n = snprintf(out, cap, "{\"nova_error\":\"petname_not_ascii\"}"); break;
    case Status::JsonChar:   n = snprintf(out, cap, "{\"nova_error\":\"petname_bad_char\"}"); break;
    case Status::NoPet:      n = snprintf(out, cap, "{\"nova_unavailable\":\"petname\"}"); break;
    case Status::SaveFailed: n = snprintf(out, cap, "{\"nova_error\":\"petname_save_failed\"}"); break;
  }
  if (n < 0 || (size_t)n >= cap) { out[0] = 0; return 0; }
  return (size_t)n;
}

}  // namespace NovaPetName
