#pragma once

#include "CustomSX1280.h"
#include "RadioLibWrappers.h"

// 2.4 GHz SX1280 wrapper, ported from the T-Watch edition of Meck (which took
// the driver from GrayHatGuy/MeshCore feat/lilygo-twatch-s3-and-2.4ghz-lora).
class CustomSX1280Wrapper : public RadioLibWrapper {
public:
  CustomSX1280Wrapper(CustomSX1280& radio, mesh::MainBoard& board) : RadioLibWrapper(radio, board) { }

  // Same steps as Meck's radio_set_params() for the SX1280. The preamble
  // stays at the fixed length set by std_init(): the SF-based preamble switch
  // and stuck-IRQ deadlines are SX126x-specific.
  void setParams(float freq, float bw, uint8_t sf, uint8_t cr) override {
    ((CustomSX1280 *)_radio)->setFrequency(freq);
    ((CustomSX1280 *)_radio)->setSpreadingFactor(sf);
    ((CustomSX1280 *)_radio)->setBandwidth(bw);
    ((CustomSX1280 *)_radio)->setCodingRate(cr);
  }

  bool isReceivingPacket() override {
    return ((CustomSX1280 *)_radio)->isReceiving();
  }
  float getCurrentRSSI() override {
    return ((CustomSX1280 *)_radio)->getRSSI(false);   // instantaneous RSSI
  }
  float getLastRSSI() const override { return ((CustomSX1280 *)_radio)->getRSSI(); }
  float getLastSNR() const override { return ((CustomSX1280 *)_radio)->getSNR(); }

  // packetScore(): the base-class version is used. Unlike SX126x, SX128x keeps
  // spreadingFactor protected, so it cannot be read here.

  // No sleep() on the SX1280: LilyGo's own LilyGoWatchS3.cpp skips
  // radio.sleep() on this revision ("SX1280 died here, the reason is not
  // analyzed yet"), and Meck found that putting it into standby during an AGC
  // reset leaves RX dead until the next transmit. So the AGC reset is a no-op
  // (RadioLibWrapper::resetAGC() still restarts receive), and power-off only
  // goes to standby; the AXP2101 cuts the rail moments later anyway.
  void doResetAGC() override { }
  void powerOff() override {
    ((CustomSX1280 *)_radio)->standby();
  }
};
