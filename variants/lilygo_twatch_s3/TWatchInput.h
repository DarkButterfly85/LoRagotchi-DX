#pragma once

#include <Arduino.h>
#include <helpers/ui/MomentaryButton.h>   // BUTTON_EVENT_* constants
#include "TWatchS3Board.h"
#include "TWatchS3Display.h"

// TWatchInput -- the T-Watch S3's side PWR key and touch screen.
//
// poll() reports one gesture at a time, using the same touch model as the
// Meck T-Watch firmware:
//   TW_PWR_CLICK        side PWR key, press < 1s (also wakes the display)
//   TW_TAP_TOP          tap in the top 90 panel pixels (the margin above a
//                       centred screen plus its header row; on the full-height
//                       aquarium, the header and the top of the tank)
//   TW_TAP_LEFT/RIGHT   tap in the left / right half below that
//   TW_SWIPE_*          finger moved at least SWIPE_PX; fires while still down
//   TW_HOLD             finger held still for HOLD_MS; fires while still down
//
// LoRaGotchi maps these to its screens in UITask.cpp (LORAFISH_WATCH_TOUCH).
// check() also offers the plain single-button events (click / long-press),
// for any build that uses UITask's generic button path instead.
//
// The PWR key is wired to the AXP2101 PWRON pin, not a GPIO, so presses are
// read from the PMU's latched IRQ status over I2C (approach ported from Meck's
// PMUButton). Holding the key 6s is a hardware power-off.
//
// Touches are ignored while the display is off, so a sleeve or wrist brushing
// the glass cannot wake the watch; press the side key to wake it.
enum TWatchGesture {
  TW_NONE = 0,
  TW_PWR_CLICK,
  TW_TAP_TOP,
  TW_TAP_LEFT,
  TW_TAP_RIGHT,
  TW_SWIPE_LEFT,
  TW_SWIPE_RIGHT,
  TW_SWIPE_UP,
  TW_SWIPE_DOWN,
  TW_HOLD,
};

class TWatchInput {
public:
  // Timing and thresholds follow Meck's watch touch handling.
  static const unsigned long PWR_POLL_MS = 30;
  static const unsigned long TOUCH_POLL_MS = 20;
  static const unsigned long LIFT_MS = 150;        // finger counts as down if seen this recently
  static const uint8_t LATCH_LIFT_POLLS = 5;       // after a swipe/hold: empty polls needed to re-arm
  static const unsigned long MIN_INTERVAL_MS = 300; // after a swipe/hold: minimum gap before re-arming
  static const unsigned long HOLD_MS = 750;
  static const int SWIPE_PX = 32;                  // panel pixels (Meck: 16 at half scale)
  static const int TOP_ZONE_PX = 90;               // margin above a centred screen + its 16-row header

private:
  TWatchS3Board& _board;
  TWatchS3Display& _display;

  unsigned long _last_pwr_poll = 0;
  bool _pwr_down = false;

  unsigned long _last_touch_poll = 0;
  unsigned long _last_seen = 0;
  bool _down = false;            // a gesture is in progress
  bool _latched = false;         // swipe/hold already reported; wait for a real lift
  uint8_t _empty_polls = 0;
  unsigned long _down_at = 0;
  unsigned long _event_at = 0;
  int _down_x = 0, _down_y = 0, _last_x = 0, _last_y = 0;

  void resetTouch() {
    _down = false;
    _latched = false;
    _empty_polls = 0;
  }

  TWatchGesture pollPwrKey() {
    if (millis() - _last_pwr_poll < PWR_POLL_MS) return TW_NONE;
    _last_pwr_poll = millis();

    XPowersAXP2101* pmu = _board.getPMU();
    if (pmu == NULL) return TW_NONE;

    pmu->getIrqStatus();   // latch the status registers into the driver
    // Apply the edges before the click, so a poll that catches press, release
    // and short-press together still leaves _pwr_down false.
    if (pmu->isPekeyNegativeIrq()) _pwr_down = true;   // PWRON is active low: press
    if (pmu->isPekeyPositiveIrq()) _pwr_down = false;  // release
    TWatchGesture g = pmu->isPekeyShortPressIrq() ? TW_PWR_CLICK : TW_NONE;
    pmu->clearIrqStatus();
    return g;
  }

  TWatchGesture pollTouch() {
    if (!_display.isOn()) {
      resetTouch();
      return TW_NONE;
    }
    unsigned long now = millis();
    if (now - _last_touch_poll < TOUCH_POLL_MS) return TW_NONE;
    _last_touch_poll = now;

    int x, y;
    bool got = _display.getTouch(&x, &y);
    if (got) {
      _last_seen = now;
      _empty_polls = 0;
    } else if (_empty_polls < 255) {
      _empty_polls++;
    }
    bool present = got || (_down && now - _last_seen < LIFT_MS);

    if (_latched) {
      // A swipe or hold was already reported for this touch. Ignore it until
      // the finger is clearly gone, so it cannot also act on the next screen.
      if (!got && _empty_polls >= LATCH_LIFT_POLLS && now - _last_seen >= LIFT_MS &&
          now - _event_at >= MIN_INTERVAL_MS) {
        _latched = false;
        _down = false;
      }
      return TW_NONE;
    }

    if (!_down) {
      if (got) {                 // finger down
        _down = true;
        _down_at = now;
        _down_x = _last_x = x;
        _down_y = _last_y = y;
      }
      return TW_NONE;
    }

    if (!present) {              // finger up with no swipe or hold: a tap
      _down = false;
      if (_down_y < TOP_ZONE_PX) return TW_TAP_TOP;
      return (_down_x < LCD_HOR_SIZE / 2) ? TW_TAP_LEFT : TW_TAP_RIGHT;
    }

    if (got) { _last_x = x; _last_y = y; }
    int dx = _last_x - _down_x;
    int dy = _last_y - _down_y;
    int dist = abs(dx) > abs(dy) ? abs(dx) : abs(dy);

    if (dist >= SWIPE_PX) {
      _latched = true;
      _event_at = now;
      _empty_polls = 0;
      if (abs(dx) > abs(dy)) return (dx < 0) ? TW_SWIPE_LEFT : TW_SWIPE_RIGHT;
      return (dy < 0) ? TW_SWIPE_UP : TW_SWIPE_DOWN;
    }
    if (now - _down_at >= HOLD_MS) {
      _latched = true;
      _event_at = now;
      _empty_polls = 0;
      return TW_HOLD;
    }
    return TW_NONE;
  }

public:
  TWatchInput(TWatchS3Board& board, TWatchS3Display& display) : _board(board), _display(display) {}

  void begin() {}

  // True while the PWR key is held or a finger is on the screen.
  bool isPressed() const { return _pwr_down || _down; }

  TWatchGesture poll() {
    TWatchGesture g = pollPwrKey();
    if (g != TW_NONE) {
      resetTouch();
      return g;
    }
    return pollTouch();
  }

  // Plain single-button view of poll(): side key or tap = click, hold = long-press.
  int check() {
    switch (poll()) {
      case TW_PWR_CLICK:
      case TW_TAP_TOP:
      case TW_TAP_LEFT:
      case TW_TAP_RIGHT:
        return BUTTON_EVENT_CLICK;
      case TW_HOLD:
        return BUTTON_EVENT_LONG_PRESS;
      default:
        return BUTTON_EVENT_NONE;
    }
  }
};
