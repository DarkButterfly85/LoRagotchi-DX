#!/usr/bin/env python3
"""Compile the real SH1106 wrapper against a mocked Adafruit bus boundary.
Also exercise actual L1 button/menu handlers through that wrapper in all editions.
No physical OLED brightness, I2C electrical or persistence claim.
"""
from pathlib import Path
import os
import subprocess
import tempfile
from sh1106_mock import write_headers

root = Path(__file__).resolve().parents[2]
harness = r'''
#include <cassert>
#include <cstdio>
#include <helpers/ui/SH1106Display.h>
static void last(int command,int value=0){
  assert(!MockOLED::events.empty());
  assert(MockOLED::events.back()==std::make_pair(command,value));
}
int main(){
  MockOLED::reset();Wire.present=DISPLAY_ADDRESS;
  SH1106Display panel; DisplayDriver& display=panel; // virtual override, not a test subclass
  assert(!display.isOn());
  display.turnOn();display.turnOff();display.setBrightness(64);
  assert(MockOLED::events.empty());
  assert(panel.begin() && display.isOn());
  assert(MockOLED::beginAddress==DISPLAY_ADDRESS && MockOLED::begins==1);last(0x81,64);
  // Every byte, including zero (contrast zero is not DISPLAYOFF).
  for(int b=0;b<=255;++b){display.setBrightness(b);last(0x81,b);assert(display.isOn());}
  display.turnOff();assert(!display.isOn());last(SH110X_DISPLAYOFF);
  auto count=MockOLED::events.size();
  display.setBrightness(128);display.setBrightness(192);assert(MockOLED::events.size()==count);
  display.turnOn();assert(display.isOn());last(0x81,192);
  assert(MockOLED::events[count].first==SH110X_DISPLAYON && MockOLED::begins==1);
  assert(panel.begin());last(0x81,192); // re-init overwrites Adafruit's default contrast
  display.turnOff();display.turnOff();assert(!display.isOn());
  display.turnOn();display.turnOn();assert(display.isOn());last(0x81,192);
  // Probe failure, allocation/init failure, and failed re-init must all be safe.
  for(int failure=0;failure<3;++failure){
    MockOLED::reset();Wire.present=DISPLAY_ADDRESS;SH1106Display broken;DisplayDriver& base=broken;
    if(failure==2)assert(broken.begin());
    if(failure==0)Wire.present=0;else MockOLED::beginOK=false;
    base.setBrightness(64);assert(!broken.begin() && !base.isOn());
    count=MockOLED::events.size();
    base.turnOn();base.turnOff();base.setBrightness(128);
    assert(!base.isOn() && MockOLED::events.size()==count);
    Wire.present=DISPLAY_ADDRESS;MockOLED::beginOK=true;
    assert(broken.begin() && base.isOn());last(0x81,128);
  }
  // Configured SA0 address wins; fallback tries precisely the other address.
  MockOLED::reset();Wire.present=DISPLAY_ADDRESS^1;SH1106Display fallback;
  assert(fallback.begin() && MockOLED::beginAddress==(DISPLAY_ADDRESS^1));
  assert(Wire.probes==std::vector<int>({DISPLAY_ADDRESS,DISPLAY_ADDRESS^1}));
  MockOLED::reset();Wire.present=DISPLAY_ADDRESS;SH1106Display defaults;assert(defaults.begin());last(0x81,255);
  assert(Wire.probes==std::vector<int>({DISPLAY_ADDRESS}));
  puts("PASS real SH1106 wrapper: virtual contrast bytes, default/cache, init/wake/off guards, probe fallback and failure recovery");
}
'''
with tempfile.TemporaryDirectory(prefix="sh1106-brightness-") as directory:
    directory = Path(directory)
    write_headers(directory)
    cpp = directory / "wrapper.cpp"
    cpp.write_text(harness)
    for address in ["0x3C", "0x3D"]:
        binary = directory / "wrapper"
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
                        "-DDISPLAY_ADDRESS=" + address, "-I" + str(directory), "-I" + str(root / "src"),
                        str(cpp), str(root / "src/helpers/ui/SH1106Display.cpp"), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
subprocess.run(["python3", str(Path(__file__).with_name("check_l1_buttons.py"))],
               env=dict(os.environ, LORAGOTCHI_TEST_SH1106="1"), check=True)
