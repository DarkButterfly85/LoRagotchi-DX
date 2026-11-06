#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Physical, page-major framebuffer comparison. No hashes or draw-call heuristics.
// Sink must acknowledge every command/data transaction. Failed writes invalidate
// the entire shadow: the next attempt repairs even a partly updated panel.
template <size_t Width, size_t Pages> class MonoPagePresenter {
  uint8_t shadow[Width * Pages];
  bool valid = false;
public:
  void invalidate() { valid = false; }
  template <typename Sink> bool present(const uint8_t* frame, Sink& sink, bool partial = true) {
    if (!frame) { invalidate(); return false; }
    for (size_t page = 0; page < Pages; ++page) {
      const uint8_t* row = frame + page * Width;
      size_t first = 0, last = Width;
      bool compare = valid && partial;
#ifdef LORAFISH_MONO_FULL_FRAMES
      compare = false; // Diagnostic fallback with checked transport.
#endif
      if (compare) {
        while (first < Width && row[first] == shadow[page * Width + first]) ++first;
        if (first == Width) continue;
        while (last > first && row[last-1] == shadow[page * Width + last-1]) --last;
      }
      if (!sink.writePage(page, first, row + first, last - first)) {
        invalidate(); return false;
      }
    }
    memcpy(shadow, frame, sizeof(shadow));
    valid = true;
    return true;
  }
};
