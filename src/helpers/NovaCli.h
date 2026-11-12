#pragma once
// Nova dashboard serial link: pure text parsing and JSON line formatting.
// No Arduino, no radio, no storage; so it can be tested on the host (test/test_nova_cli).
//
//   nova hello           one JSON line saying which dashboard features this firmware really has
//   nova contacts        parsed here, answered by the caller (one JSON line streamed from LoRaFishEligible.h); reply() builds nothing
//   nova mesh            parsed here, answered by the caller (examples/companion_radio/MyMesh.cpp queues the mesh line and, at
//                        most every 5 s, the status frame from helpers/NovaStreams.h); reply() builds nothing
//   nova status          the status frame on demand (parsed here, answered by the caller); reply() builds nothing
//   nova battery         {"nova_ok":"battery","mv":N,"pct":N,"chg":0|1} (built by NovaStreams.h, answered by the caller); reply() builds nothing
//   nova pet             {"nova_unavailable":"pet"}   (so the dashboard does not wait for nothing)
//   nova petname <name>  {"nova_unavailable":"petname"}  only as the answer of a build with no pet name to set; a build
//                        that has one answers through helpers/NovaPetName.h ({"nova_ok":"petname","name":...})
//   nova baud <rate>     only answered by a build that registered a speed setter (examples/companion_radio/NovaBaud.h
//                        builds the reply: {"nova_ok":"baud","rate":N} or {"nova_error":"baud_unsupported"}); here it is
//                        {"nova_unavailable":"baud"}. Hello lists "baud":1 in caps only for a build that really has it.
//   nova <anything else> {"nova_error":"unknown_command"}
// A line that does not start with the word "nova" is not ours: parse() says NotNova and the caller
// leaves it alone. Replies never start with "nova status" or "nova profile" (the dashboard reads
// those as "no pet support") and never repeat what the sender typed.
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace NovaCli {

enum class Cmd { NotNova, Hello, Contacts, Mesh, Pet, PetName, Baud, Status, Battery, Unknown };

struct Parsed {
  Cmd cmd;
  const char* arg;   // text after the sub-command (petname, baud), points into the parsed line
};

// What this firmware can really do. Set a flag to 1 only when the feature exists (petname: only when the
// handler really saves the name, i.e. a pet screen has registered its setter).
struct Caps {
  int pet = 0, mesh = 0, contacts = 0, petname = 0, keys = 0, clean = 0, feed = 0, guess = 0, ping = 0, sendpet = 0;
  // mesh = 1 means this build feeds helpers/NovaStreams.h from the radio's rx/tx hooks and answers "nova mesh" with the mesh lines and the status frames.
  int baud = 0;   // "nova baud" saves a speed (NovaBaud.h). Listed as "baud":1 only when 1; absent otherwise, so a build without it says exactly what it always said
};

static inline Parsed parse(const char* line) {
  Parsed p = { Cmd::NotNova, "" };
  if (!line) return p;
  while (*line == ' ') line++;
  if (strncmp(line, "nova", 4) != 0 || (line[4] != 0 && line[4] != ' ')) return p;   // "novae" is not ours
  const char* w = line + 4;
  while (*w == ' ') w++;
  size_t n = 0;
  while (w[n] && w[n] != ' ') n++;
  const char* rest = w + n;
  while (*rest == ' ') rest++;
  p.cmd = Cmd::Unknown;
  if (n == 5 && strncmp(w, "hello", 5) == 0) p.cmd = Cmd::Hello;
  else if (n == 8 && strncmp(w, "contacts", 8) == 0) p.cmd = Cmd::Contacts;
  else if (n == 4 && strncmp(w, "mesh", 4) == 0) p.cmd = Cmd::Mesh;
  else if (n == 3 && strncmp(w, "pet", 3) == 0) p.cmd = Cmd::Pet;
  else if (n == 7 && strncmp(w, "petname", 7) == 0) { p.cmd = Cmd::PetName; p.arg = rest; }
  else if (n == 4 && strncmp(w, "baud", 4) == 0) { p.cmd = Cmd::Baud; p.arg = rest; }
  else if (n == 6 && strncmp(w, "status", 6) == 0) p.cmd = Cmd::Status;
  else if (n == 7 && strncmp(w, "battery", 7) == 0) p.cmd = Cmd::Battery;
  return p;
}

// Edition name for the "ed" field: lower case, only [a-z0-9_-]; "dx" if nothing is left.
static inline void editionId(const char* edition, char* out, size_t cap) {
  size_t n = 0;
  for (; edition && *edition && n + 1 < cap; ++edition) {
    char c = *edition;
    if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
    if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_') out[n++] = c;
  }
  if (n == 0 && cap > 2) { out[n++] = 'd'; out[n++] = 'x'; }
  if (cap) out[n < cap ? n : cap - 1] = 0;
}

// Writes the reply line (no line ending) to out and returns its length. Returns 0 for a line that is
// not a nova command. The result is always NUL-terminated when cap > 0; a reply that does not fit is cut
// to an empty string rather than half a JSON line.
static inline size_t reply(const Parsed& p, const char* edition, const Caps& c, char* out, size_t cap) {
  if (!out || cap == 0) return 0;
  out[0] = 0;
  int n = 0;
  switch (p.cmd) {
    case Cmd::NotNova: return 0;
    case Cmd::Hello: {
      char ed[24];
      editionId(edition, ed, sizeof(ed));
      n = snprintf(out, cap,
        "{\"ed\":\"%s\",\"nova\":{\"v\":1,\"caps\":{\"pet\":%d,\"mesh\":%d,\"contacts\":%d,\"petname\":%d,"
        "\"keys\":%d,\"clean\":%d,\"feed\":%d,\"guess\":%d,\"ping\":%d,\"sendpet\":%d%s}},"
        "\"lg\":{\"hello\":1,\"pet\":%d,\"mesh\":%d}}",
        ed, c.pet ? 1 : 0, c.mesh ? 1 : 0, c.contacts ? 1 : 0, c.petname ? 1 : 0, c.keys ? 1 : 0,
        c.clean ? 1 : 0, c.feed ? 1 : 0, c.guess ? 1 : 0, c.ping ? 1 : 0, c.sendpet ? 1 : 0,
        c.baud ? ",\"baud\":1" : "",
        c.pet ? 1 : 0, c.mesh ? 1 : 0);
      break;
    }
    case Cmd::Contacts: return 0;   // streamed by the caller (NovaContacts::writeJson, LoRaFishEligible.h): no line built here
    case Cmd::Status:  return 0;    // answered by the caller (NovaStreams.h status frame): no line built here
    case Cmd::Battery: return 0;    // answered by the caller (NovaStreams.h batteryReply): no line built here
    case Cmd::Mesh:    n = snprintf(out, cap, "{\"nova_unavailable\":\"mesh\"}"); break;   // a build without the stream (the caller answers it where there is one)
    case Cmd::Pet:     n = snprintf(out, cap, "{\"nova_unavailable\":\"pet\"}"); break;
    case Cmd::PetName: n = snprintf(out, cap, "{\"nova_unavailable\":\"petname\"}"); break;
    case Cmd::Baud:    n = snprintf(out, cap, "{\"nova_unavailable\":\"baud\"}"); break;
    case Cmd::Unknown: n = snprintf(out, cap, "{\"nova_error\":\"unknown_command\"}"); break;
  }
  if (n < 0 || (size_t)n >= cap) { out[0] = 0; return 0; }
  return (size_t)n;
}

}  // namespace NovaCli
