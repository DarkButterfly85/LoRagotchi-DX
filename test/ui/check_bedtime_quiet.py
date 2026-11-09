#!/usr/bin/env python3
"""Bedtime quiet: asleep pets stay silent for ordinary messages, favourites get through.

python3 test/ui/check_bedtime_quiet.py (Python 3 and g++). Extracts the real
UITask message handlers, notify() and loRaFishIsSleeping() from UITask.cpp and
runs them against mock buzzer/vibration/screen, with and without a buzzer.
No radio, no screen, no flash.
"""
from pathlib import Path
import runpy, subprocess, tempfile

root = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(root / 'test/ui/check_menu_navigation.py'))
block, source = fixture['block'], fixture['source']

assert 'LoRaFishBedtime::quiet(' in source, 'UITask must use the bedtime rule'
parts = [r'''
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include "examples/companion_radio/ui-new/LoRaFishHappiness.h"
#include "examples/companion_radio/ui-new/LoRaFishBedtime.h"
#include "src/helpers/ContactInfo.h"
static constexpr uint8_t TXT_TYPE_PLAIN = 0, TXT_TYPE_SIGNED_PLAIN = 2;

struct ChannelDetails { char name[16] = "chan"; };
enum class UIEventType { none, contactMessage, channelMessage, roomMessage, newContactMessage, ack };
static uint8_t min(uint8_t a, uint8_t b) { return a < b ? a : b; }
static uint8_t loRaFishSleepHour = 21, loRaFishWakeHour = 7, loRaFishMessageSound = 1;
static uint32_t localHour = 12;
static uint32_t loRaFishLocalEpoch() { return localHour * 3600; }
static const char* loRaFishMessageMelodies[] = {"", "a", "b", "c"};
static uint32_t loRaFishScreenTimeoutMs() { return 30000; }
struct FishState { uint32_t messages = 0, txAcks = 0; } fish;
static int reactions = 0, activity = 0;
static void reactLoRaFish(int) { ++reactions; }
struct Disp { bool on = true; bool isOn() { return on; } void turnOn() { on = true; } };
static void loRaFishRegisterDisplayActivity(Disp&) { ++activity; }
''']
parts.append(block('static bool loRaFishIsSleeping() {'))
parts.append(r'''
struct UITask {
  Disp d; Disp* _display = &d;
  uint32_t _auto_off = 0, _next_refresh = 777;
  bool connected = false; int homes = 0;
  struct { int plays = 0; void play(const char*) { ++plays; } } buzzer;
  struct { int buzzes = 0; void trigger() { ++buzzes; } } vibration;
  bool hasConnection() { return connected; }
  void gotoHomeScreen() { ++homes; }
  void notify(UIEventType);
  void handleLoRaFishMessage();
  void handleLoRaFishQuietMessage();
  void onMessageRecv(mesh::Packet*, const ContactInfo&, uint8_t, uint32_t, const char*);
  void onChannelMessageRecv(mesh::Packet*, ChannelDetails&, const char*);
};
''')
for m in ['void UITask::notify(', 'void UITask::onMessageRecv(', 'void UITask::onChannelMessageRecv(',
          'void UITask::handleLoRaFishMessage() {', 'void UITask::handleLoRaFishQuietMessage() {']:
    parts.append(block(m))
parts.append(r'''
static void reset(UITask& t, uint32_t hour, bool screenOn = true) {
  t.buzzer.plays = t.vibration.buzzes = 0; t.homes = 0; t.d.on = screenOn;
  t._auto_off = 5; t._next_refresh = 777; activity = 0; reactions = 0; fish.messages = 0;
  localHour = hour;
}
int main() {
  g_mock_millis = 100000;
  UITask t; mesh::Packet* pkt = nullptr; ChannelDetails ch;
  // The mock Identity has no constructor body, so build the contacts in raw storage.
  alignas(ContactInfo) static unsigned char plainBuf[sizeof(ContactInfo)], favBuf[sizeof(ContactInfo)];
  memset(plainBuf, 0, sizeof plainBuf); memset(favBuf, 0, sizeof favBuf);
  ContactInfo& plain = *reinterpret_cast<ContactInfo*>(plainBuf);
  ContactInfo& fav = *reinterpret_cast<ContactInfo*>(favBuf);
  fav.flags = 0x01;
  assert(!plain.isFav() && fav.isFav());
  assert(LoRaFishBedtime::quiet(true, false) && !LoRaFishBedtime::quiet(true, true) &&
         !LoRaFishBedtime::quiet(false, false) && !LoRaFishBedtime::quiet(false, true));
  assert(!loRaFishIsSleeping() == (localHour == 12));

  // Awake (noon): unchanged -- sound (if fitted), buzz, screen kept lit, pet counts it.
  reset(t, 12);
  t.onMessageRecv(pkt, plain, TXT_TYPE_PLAIN, 0, "hi");
  assert(t.vibration.buzzes == 1 && t._auto_off == 100000 + 30000 && t._next_refresh == 0 && activity == 1);
  assert(fish.messages == 1 && reactions == 1);
#ifdef PIN_BUZZER
  assert(t.buzzer.plays == 1);
#endif
  reset(t, 12); t.onChannelMessageRecv(pkt, ch, "hi");
  assert(t.vibration.buzzes == 1 && t._auto_off == 130000 && activity == 1);

  // Asleep (23:00 and 03:00, across midnight) + ordinary message: silent, no screen extension, pet still counts it.
  for (uint32_t hour : {23u, 3u, 21u, 6u}) {
    reset(t, hour);
    assert(loRaFishIsSleeping());
    t.onMessageRecv(pkt, plain, TXT_TYPE_PLAIN, 0, "hi");
    assert(t.buzzer.plays == 0 && t.vibration.buzzes == 0);
    assert(t._auto_off == 5 && t._next_refresh == 777 && activity == 0);
    assert(fish.messages == 1 && reactions == 1 && t.homes == 1);
    reset(t, hour); t.onChannelMessageRecv(pkt, ch, "hi");
    assert(t.buzzer.plays == 0 && t.vibration.buzzes == 0 && t._auto_off == 5 && activity == 0);
    // Screen already off stays off.
    reset(t, hour, false); t.onMessageRecv(pkt, plain, TXT_TYPE_PLAIN, 0, "hi");
    assert(!t.d.on && t.buzzer.plays == 0 && t.vibration.buzzes == 0);
  }

  // Asleep + favourite: everything still fires, exactly like awake.
  reset(t, 23);
  t.onMessageRecv(pkt, fav, TXT_TYPE_PLAIN, 0, "hi");
  assert(t.vibration.buzzes == 1 && t._auto_off == 130000 && t._next_refresh == 0 && activity == 1);
#ifdef PIN_BUZZER
  assert(t.buzzer.plays == 1);
#endif
  // Asleep + connected app: the phone gets the message, device stays quiet either way.
  reset(t, 23); t.connected = true; t.onMessageRecv(pkt, fav, TXT_TYPE_PLAIN, 0, "hi");
  assert(t.buzzer.plays == 0 && t.vibration.buzzes == 0); t.connected = false;
  // Non-text types are ignored as before.
  reset(t, 12); t.onMessageRecv(pkt, plain, 7, 0, "x"); assert(fish.messages == 0 && t.vibration.buzzes == 0);
  // Ack beeps are not messages and are untouched at night.
  reset(t, 23); t.notify(UIEventType::ack);
#ifdef PIN_BUZZER
  assert(t.buzzer.plays == 1);
#endif
  assert(t.vibration.buzzes == 1);
  // Sleep == Wake hour means never asleep.
  loRaFishSleepHour = loRaFishWakeHour = 7; reset(t, 23); t.onMessageRecv(pkt, plain, TXT_TYPE_PLAIN, 0, "hi");
  assert(t.vibration.buzzes == 1);
  puts("PASS bedtime quiet");
}
''')
with tempfile.TemporaryDirectory(prefix='lrx-bedtime-') as tmp:
    path = Path(tmp); cpp = path / 'bedtime.cpp'; cpp.write_text('\n'.join(parts))
    for sound in (False, True):
        exe = path / ('bedtime%d' % sound)
        args = ['g++', '-std=c++17', '-DLORAFISH_UI=1', '-DPIN_VIBRATION=1', '-I', str(root), '-I', str(root / 'src'), '-I', str(root / 'test/mocks')]
        if sound: args.append('-DPIN_BUZZER=1')
        subprocess.run(args + [str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
