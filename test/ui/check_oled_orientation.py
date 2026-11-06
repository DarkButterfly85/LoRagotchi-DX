#!/usr/bin/env python3
"""Compile real SH1106/SH1107 wrappers, recording GFX rotation and wake state."""
from pathlib import Path
import subprocess,tempfile
from sh1106_mock import write_headers
root=Path(__file__).resolve().parents[2]
for driver in ['SH1106','SH1107']:
 for baseline in [0,2]:
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);write_headers(p)
   h=p/'Adafruit_SH110X.h';s=h.read_text().replace('inline int beginAddress=', 'inline int rotation=-1; inline int beginAddress=')
   s=s.replace('void setRotation(uint8_t) {}','void setRotation(uint8_t r) {MockOLED::rotation=r;}')
   s=s.replace('  void oled_command(uint8_t c)', '  void oled_commandList(uint8_t*,int) {} void oled_command(uint8_t c)')
   s+=chr(10)+'using Adafruit_SH1107=Adafruit_SH1106G;'+chr(10);h.write_text(s)
   cpp=p/'main.cpp';cpp.write_text(f'''
#include <helpers/ui/{driver}Display.h>
int main() {{
 {driver}Display d;assert(d.supportsOrientation());assert(d.supportsPartialUpdates());
 d.setPartialUpdates(true);d.forceFullRefresh();
 assert(d.begin());assert(MockOLED::rotation=={baseline});
 d.setOrientation(true);assert(MockOLED::rotation=={(baseline+2)&3});
 d.turnOff();d.turnOn();assert(MockOLED::rotation=={(baseline+2)&3});
 d.begin();assert(MockOLED::rotation=={(baseline+2)&3});
 d.setOrientation(false);assert(MockOLED::rotation=={baseline});
 d.endFrame();d.setPartialUpdates(false);d.endFrame();
}}
''')
   subprocess.run(['g++','-std=c++17',f'-DDISPLAY_ROTATION={baseline}','-I'+t,'-I'+str(root/'src'),str(cpp),str(root/f'src/helpers/ui/{driver}Display.cpp'),'-o',str(p/'check')],check=True)
   subprocess.run([str(p/'check')],check=True)
print('PASS production SH1106/SH1107 rotation, board baselines, wake and reinitialization')
