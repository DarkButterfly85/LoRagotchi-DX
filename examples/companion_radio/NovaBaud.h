#pragma once
// LORAGOTCHI NOVA serial link speed: the list of speeds, the saved choice, the "nova baud" reply.
// Pure C++ (no Arduino calls) so it is host tested (test/test_nova_baud, test/ui/check_nova_baud_setting.py).
//
// The owner picks the speed on the radio (Options > Display > Serial speed) or over the link ("nova baud 460800").
// Only the speeds in kRates are accepted. The default is kDefault (115200), the speed every build has always
// used, so nothing changes until a speed is chosen. The choice is saved and used from the NEXT START-UP (see
// "when it applies" below); the dashboard opens the port at the same speed.
//
// ---- the list ------------------------------------------------------------------------------------------
//   115200 (default), 230400, 460800, 921600. Short on purpose (four numbers, 16 bytes of flash). All four are
//   standard rates of the ESP32 UART driver (any rate the APB clock divides, up to 5 Mbaud), of the USB-serial
//   chips on those boards (CP210x, CH340, FTDI take 1 Mbaud or more) and of browser Web Serial.
//
// ---- which boards ---------------------------------------------------------------------------------------
//   Only where Serial is a real UART: ESP32 builds without ARDUINO_USB_CDC_ON_BOOT (Heltec V2/V3, T-Beam ...). UITask.cpp
//   offers the setting only in builds that carry the Nova link (LORAGOTCHI_NOVA_LINK), so a build with the phone protocol
//   on USB never changes its speed.
//   Boards with native USB (T-Deck, Cardputer, T-Watch, nRF52, RP2040 ...) carry the link over USB-CDC, which
//   has no baud rate: the number is ignored by the port. There the Serial speed row is hidden, "nova baud"
//   answers {"nova_unavailable":"baud"} and hello does not list "baud", because a setting that cannot change
//   anything would be a lie. kApplies says which case a build is in (override with -D NOVA_BAUD_APPLIES=0/1).
//
// ---- storage --------------------------------------------------------------------------------------------
//   /lorafish.bd  main copy   (record + SafeSave trailer)      /lorafish.bdt  new copy while writing
//   /lorafish.bdb previous good main copy
// Same wrapper as /lorafish.id (LoRaFishSafeSave: tmp, read back, backup, rename). /lorafish.dat (the pet),
// /lorafish.cfg (settings) and /lorafish.id are NOT touched and keep their format byte for byte. Missing or
// damaged file: the default speed. Record, 9 bytes little-endian, then the 8 byte trailer = 17 bytes on flash:
//    0  4  magic "NBD1"
//    4  1  version (1)
//    5  4  rate (uint32), one of kRates
//
// ---- when it applies ------------------------------------------------------------------------------------
//   After a restart: UITask begin() reads the file once the flash is up (the port itself is opened at 115200 in
//   main.cpp before that) and then moves the port to the saved speed once (apply()). Choosing a speed never
//   changes the port under a running dashboard session; the reply is sent at the old speed, so the dashboard
//   can read it, and the new speed is used from the next start-up. Unlisted values never reach the port.
//
// ---- the reply ------------------------------------------------------------------------------------------
//   nova baud <rate>   {"nova_ok":"baud","rate":N}        saved (N is the rate, one of kRates)
//                      {"nova_error":"baud_unsupported"}  not a number, or not in the list: nothing changed
//                      {"nova_error":"baud_save_failed"}  listed, but the file could not be written
//                      {"nova_unavailable":"baud"}        this build has no speed to set (native USB)
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ui-new/LoRaFishSafeSave.h"

#ifndef NOVA_BAUD_APPLIES
#if defined(ESP32) && !(defined(ARDUINO_USB_CDC_ON_BOOT) && ARDUINO_USB_CDC_ON_BOOT)
#define NOVA_BAUD_APPLIES 1
#else
#define NOVA_BAUD_APPLIES 0
#endif
#endif

namespace NovaBaud {

static const uint32_t kRates[] = { 115200, 230400, 460800, 921600 };
static const uint8_t kCount = sizeof(kRates) / sizeof(kRates[0]);
static const uint32_t kDefault = 115200;
static const bool kApplies = NOVA_BAUD_APPLIES != 0;

// Position of rate in kRates, or -1 when it is not a listed speed.
inline int indexOf(uint32_t rate) {
  for (uint8_t i = 0; i < kCount; ++i) if (kRates[i] == rate) return i;
  return -1;
}
inline bool listed(uint32_t rate) { return indexOf(rate) >= 0; }

enum class Status { Ok, Unsupported, SaveFailed, Unavailable };

// The text after "nova baud": spaces around are fine; digits only (no sign, no decimal point, no suffix),
// at most 9 of them, no leading zero; and the number must be in the list. Anything else: Unsupported, *rate untouched.
inline Status parse(const char* arg, uint32_t* rate) {
  if (!arg) return Status::Unsupported;
  while (*arg == ' ') arg++;
  size_t n = 0;
  while (arg[n] >= '0' && arg[n] <= '9') n++;
  if (n == 0 || n > 9 || arg[0] == '0') return Status::Unsupported;   // no leading zero: "0115200" is a typo, not 115200
  const char* end = arg + n;
  while (*end == ' ') end++;
  if (*end) return Status::Unsupported;
  uint32_t v = 0;
  for (size_t i = 0; i < n; ++i) v = v * 10u + (uint32_t)(arg[i] - '0');
  if (!listed(v)) return Status::Unsupported;
  if (rate) *rate = v;
  return Status::Ok;
}

// One JSON line, no line ending. rate is only used for Ok. Returns the length (0 and "" when it cannot fit).
inline size_t reply(Status st, uint32_t rate, char* out, size_t cap) {
  if (!out || cap == 0) return 0;
  out[0] = 0;
  int n = 0;
  switch (st) {
    case Status::Ok:          n = snprintf(out, cap, "{\"nova_ok\":\"baud\",\"rate\":%lu}", (unsigned long)rate); break;
    case Status::Unsupported: n = snprintf(out, cap, "{\"nova_error\":\"baud_unsupported\"}"); break;
    case Status::SaveFailed:  n = snprintf(out, cap, "{\"nova_error\":\"baud_save_failed\"}"); break;
    case Status::Unavailable: n = snprintf(out, cap, "{\"nova_unavailable\":\"baud\"}"); break;
  }
  if (n < 0 || (size_t)n >= cap) { out[0] = 0; return 0; }
  return (size_t)n;
}

// ---- the saved choice ----------------------------------------------------------------------------------
static const size_t kRecord = 9;
static const size_t kSealed = kRecord + LoRaFishSafeSave::kTrailer;   // 17 bytes on flash per copy
static const uint8_t kVersion = 1;
static const char* const kMain = "/lorafish.bd";
static const char* const kTmp = "/lorafish.bdt";
static const char* const kBak = "/lorafish.bdb";

inline bool encode(uint32_t rate, uint8_t* out /* kRecord bytes */) {
  if (!listed(rate)) return false;
  memcpy(out, "NBD1", 4);
  out[4] = kVersion;
  for (int i = 0; i < 4; ++i) out[5 + i] = (uint8_t)(rate >> (8 * i));
  return true;
}

inline bool recordValid(const uint8_t* rec, size_t len) {
  if (len != kRecord || memcmp(rec, "NBD1", 4) != 0 || rec[4] != kVersion) return false;
  uint32_t rate = 0;
  for (int i = 0; i < 4; ++i) rate |= (uint32_t)rec[5 + i] << (8 * i);
  return listed(rate);
}

inline uint32_t decode(const uint8_t* rec, size_t len) {
  if (!recordValid(rec, len)) return kDefault;
  uint32_t rate = 0;
  for (int i = 0; i < 4; ++i) rate |= (uint32_t)rec[5 + i] << (8 * i);
  return rate;
}

inline LoRaFishSafeSave::Paths paths() {
  return LoRaFishSafeSave::Paths{kMain, kTmp, kBak, false};     // never existed without the trailer
}

// The saved rate, or kDefault when there is no usable file (missing, damaged, unlisted rate).
template <class S>
inline uint32_t load(S& s) {
  uint8_t rec[LoRaFishSafeSave::kMaxRecord];
  size_t len = 0;
  if (LoRaFishSafeSave::load(s, recordValid, rec, &len, paths()) == LoRaFishSafeSave::None) return kDefault;
  return decode(rec, len);
}

// true only when the new copy is in place as /lorafish.bd. An unlisted rate writes nothing.
template <class S>
inline bool commit(S& s, uint32_t rate) {
  uint8_t rec[kRecord];
  if (!encode(rate, rec)) return false;
  return LoRaFishSafeSave::commit(s, rec, kRecord, paths());
}

// ---- links to the rest of the firmware ------------------------------------------------------------------
// The speed the port really runs at (a start-up fact, not the saved choice): the Nova pet sender paces its
// output by it (NovaPetLink::sendChunk). kDefault until apply() moves the port.
inline uint32_t& activeRate() { static uint32_t r = kDefault; return r; }

// Moves the port once, at start-up, to the saved rate. P is the Arduino HardwareSerial (flush(),
// updateBaudRate()); a mock on the host. Returns true when the port was moved. Unlisted rates, the speed
// already in use, and builds where the port has no baud rate do nothing.
template <class P>
inline bool apply(P& port, uint32_t rate) {
  if (!kApplies || !listed(rate) || rate == activeRate()) return false;
  port.flush();
  port.updateBaudRate(rate);
  activeRate() = rate;
  return true;
}

// What the menu (ui-new/LoRaFishMenu.h users) needs, kept here so the UI code references nothing but NovaBaud::
// and the host fixtures that cut menu functions out of UITask.cpp need no extra variables:
//   shown()   the Serial speed row is offered (a UART build, set once at start-up)
//   choice()  the saved speed (kDefault until the file has been read)
inline bool& shown() { static bool v = false; return v; }
inline uint32_t& choice() { static uint32_t v = kDefault; return v; }

// MyMesh.cpp cannot see the UI's storage. The UI registers one function that saves a listed rate; with none
// registered (native USB, no pet UI) the command says it is unavailable and hello does not list "baud".
typedef Status (*Setter)(uint32_t rate);
inline Setter& setterSlot() { static Setter f = 0; return f; }

// "nova baud <arg>" end to end: parse, then save through the registered setter. The caller prints reply().
inline Status request(const char* arg, uint32_t* rate) {
  Setter f = setterSlot();
  if (!f) return Status::Unavailable;
  const Status p = parse(arg, rate);
  if (p != Status::Ok) return p;
  return f(*rate);
}

}  // namespace NovaBaud
