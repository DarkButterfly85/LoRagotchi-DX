#pragma once

#include <stdint.h>

// Stable identities keep return targets correct when optional rows appear/disappear.
enum class LoRaFishOption : uint8_t {
  Advert, Guess, Breed, Reset, Display, Sound, Schedule, RF, GNSS, ReturnGuest, Count
};

class LoRaFishOptions {
public:
  static bool available(LoRaFishOption option, bool sound, bool breed, bool guest=false) {
    return option < LoRaFishOption::Count &&
        (option != LoRaFishOption::Sound || sound) &&
        (option != LoRaFishOption::Breed || breed) &&
        (option != LoRaFishOption::ReturnGuest || guest);
  }
  static uint8_t count(bool sound, bool breed, bool guest=false) { return 7 + sound + breed + guest; }
  static LoRaFishOption at(uint8_t row, bool sound, bool breed, bool guest=false) {
    for (uint8_t i = 0; i < static_cast<uint8_t>(LoRaFishOption::Count); ++i) {
      const auto option = static_cast<LoRaFishOption>(i);
      if (available(option, sound, breed, guest) && row-- == 0) return option;
    }
    return LoRaFishOption::Advert;
  }
  static uint8_t index(LoRaFishOption option, bool sound, bool breed, bool guest=false) {
    for (uint8_t row = 0; row < count(sound, breed, guest); ++row) {
      if (at(row, sound, breed, guest) == option) return row;
    }
    return 0;
  }
};

// Tester firmware gate. Normal builds leave LORAGOTCHI_TESTER_FIRMWARE undefined and the Options menu hides the pet
// design rows (pet colours, species). Pet setup still offers the colour choice; stored values are never touched.
#if defined(LORAGOTCHI_TESTER_FIRMWARE)
constexpr bool kLoRaFishTesterFirmware = true;
#else
constexpr bool kLoRaFishTesterFirmware = false;
#endif

// Stable identities for the Display list. The menu index is the position among the rows that are available, so
// hidden rows never leave a gap and up/down navigation (a modulo over count()) cannot land on them.
enum class LoRaFishDisplayRow : uint8_t {
  Timeout, Brightness, Theme, Colour, Rendering, Species, Orientation, DisplayUpdate, DimSlow, Count
};

struct LoRaFishDisplayRows {
  bool colourDisplay = false;   // true: the Colour row is the pet colours; false: it is the mono screen colour
  bool speciesEdition = false;
  bool orientation = false;
  bool partial = false;
  bool dimSlow = false;
  bool tester = kLoRaFishTesterFirmware;
  bool available(LoRaFishDisplayRow row) const {
    switch (row) {
      case LoRaFishDisplayRow::Colour: return !colourDisplay || tester;  // pet colours: tester only
      case LoRaFishDisplayRow::Species: return speciesEdition && tester;
      case LoRaFishDisplayRow::Orientation: return orientation;
      case LoRaFishDisplayRow::DisplayUpdate: return partial;
      case LoRaFishDisplayRow::DimSlow: return dimSlow;
      case LoRaFishDisplayRow::Count: return false;
      default: return true;
    }
  }
  uint8_t count() const {
    uint8_t n = 0;
    for (uint8_t i = 0; i < static_cast<uint8_t>(LoRaFishDisplayRow::Count); ++i)
      n += available(static_cast<LoRaFishDisplayRow>(i));
    return n;
  }
  LoRaFishDisplayRow at(uint8_t position) const {
    for (uint8_t i = 0; i < static_cast<uint8_t>(LoRaFishDisplayRow::Count); ++i) {
      const auto row = static_cast<LoRaFishDisplayRow>(i);
      if (available(row) && position-- == 0) return row;
    }
    return LoRaFishDisplayRow::Timeout;
  }
  // Position of a row in the visible list; 0 when that row is hidden.
  uint8_t index(LoRaFishDisplayRow row) const {
    uint8_t position = 0;
    for (uint8_t i = 0; i < static_cast<uint8_t>(LoRaFishDisplayRow::Count); ++i) {
      const auto candidate = static_cast<LoRaFishDisplayRow>(i);
      if (!available(candidate)) continue;
      if (candidate == row) return position;
      ++position;
    }
    return 0;
  }
};

enum class LoRaFishSetting : uint8_t {
  Theme, Brightness, Rendering, Scales, Body, Eyes, SleepHour, WakeHour, UtcOffset,
  TimeoutAwake, TimeoutAsleep, DimAfter, Volume, WakeSound, SleepSound, MessageSound, MonoDisplayColour, Species, Orientation, DisplayUpdate,
  SpeciesSet, // DX-Pro only: step one of the set-then-species menu (appended so existing values keep their numbers)
  DimSlow // Slow animation when dimmed (appended; Off/On)
};

// Browsing is a draft: only Select produces a value to persist. Back cancels it.
class LoRaFishValuePicker {
  bool editing = false;
  LoRaFishSetting setting = LoRaFishSetting::Theme;
  uint8_t candidate = 0;
  uint8_t valueCount = 0;
  bool backwards = false;
public:
  void open(LoRaFishSetting key, uint8_t value, uint8_t count) {
    backwards = false;
    setting = key;
    valueCount = count;
    candidate = count ? value % count : 0;
    editing = count != 0;
  }
  bool active() const { return editing; }
  LoRaFishSetting key() const { return setting; }
  uint8_t value() const { return candidate; }
  uint8_t count() const { return valueCount; }
  bool reversible() const {
    return setting == LoRaFishSetting::SleepHour || setting == LoRaFishSetting::WakeHour ||
        setting == LoRaFishSetting::UtcOffset;
  }
  bool reverse() const { return backwards; }
  void toggleDirection() { if (editing && reversible()) backwards = !backwards; }
  void step() { move(backwards); }
  void move(bool previous = false) {
    if (editing) candidate = (candidate + (previous ? valueCount - 1 : 1)) % valueCount;
  }
  void cancel() { editing = false; }
  bool select(uint8_t& value) {
    if (!editing) return false;
    value = candidate;
    editing = false;
    return true;
  }
};


// Menu row layout, shared by every menu drawer. Pure integer maths (no driver, no Arduino) so the host
// tests exercise the exact production rules. Units are the driver's own coordinate units: real pixels on
// the native panels and the Cardputer, the 128x64 grid on the OLEDs and the scaled T-Deck.
//
// The pitch comes from the driver (DisplayDriver::menuRowPitch(): font height plus one pixel), never from
// a fixed number, and the visible row count is whatever fits between the header rule and the hint line.
namespace LoRaFishMenuLayout {
constexpr int kTop = 18;        // first row: just below the 16 px header rule
constexpr int kHintGap = 8;     // hint line height on panels taller than the 64 px reference
constexpr int kLegacyPitch = 9; // the pitch the 64 px reference menus have always used (8 px font + 1)

// Hint line baseline. The 64 px reference keeps its historic row (56); taller panels anchor it to the bottom edge.
constexpr int hintY(int height) { return height <= 64 ? 56 : height - kHintGap; }

// Rows that fit between `top` and the hint line (or the panel bottom when the page has no hint). Never 0.
constexpr int rows(int height, int pitch, int top = kTop, bool hint = true) {
  return pitch < 1 ? 1
       : ((hint ? hintY(height) : height) - top) / pitch < 1 ? 1
       : ((hint ? hintY(height) : height) - top) / pitch;
}

// First visible item for a list of `count` items showing `visible` rows. The selection rides the last row until
// the list ends, which is the scrolling rule the menus always had; it is always inside [first, first+visible).
constexpr int first(int selected, int count, int visible) {
  return count <= visible ? 0
       : (selected + 1 > visible ? selected + 1 - visible : 0) > count - visible
           ? count - visible
           : (selected + 1 > visible ? selected + 1 - visible : 0);
}

// Y of row `row`. The 64 px reference with the standard pitch keeps each menu's historic rows exactly;
// everything else (taller panels, the scaled T-Deck) packs rows at the driver's own pitch from kTop.
constexpr int rowY(int height, int pitch, int row, int legacyTop = kTop, int legacyPitch = kLegacyPitch) {
  return (height <= 64 && pitch >= kLegacyPitch) ? legacyTop + row * legacyPitch : kTop + row * pitch;
}

// Convenience forms that read the pitch and height from the driver being drawn on.
template <class Display> inline int rowsFor(Display& d) { return rows(d.height(), d.menuRowPitch()); }
template <class Display> inline int rowYFor(Display& d, int row, int legacyTop = kTop, int legacyPitch = kLegacyPitch) {
  return rowY(d.height(), d.menuRowPitch(), row, legacyTop, legacyPitch);
}
} // namespace LoRaFishMenuLayout
