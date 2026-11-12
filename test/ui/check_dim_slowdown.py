#!/usr/bin/env python3
"""Slow animation when dimmed: default Off, render timer, settings tail, menu wiring.

python3 test/ui/check_dim_slowdown.py (Python 3 and g++). No firmware build, no hardware.
The real UITask.cpp timer block, helper and settings tail are cut out of the source and
compiled in a tiny harness, so the checks run the production lines, not a copy.
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
UI = (ROOT / 'examples/companion_radio/ui-new/UITask.cpp').read_text()
MENU = (ROOT / 'examples/companion_radio/ui-new/LoRaFishMenu.h').read_text()
DRV = (ROOT / 'src/helpers/ui/DisplayDriver.h').read_text()


def between(text, start, end, include_end=False):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b + (len(end) if include_end else 0)]


# ---- static wiring -------------------------------------------------------
assert 'static uint8_t loRaFishDimSlow = 0;' in UI, 'default must be Off'
assert 'static bool loRaFishDimSlowSupported = false;' in UI
assert re.search(r'loadLoRaFishSettings\(\) \{\s*loRaFishOrientation = 0;\s*loRaFishPartial = 0;\s*loRaFishDimSlow = 0;', UI), \
    'load must reset the setting to Off before reading the file'
assert 'loRaFishDimSlowSupported = display && display->supportsBrightness() && !display->isEink();' in UI, \
    'never on e-ink, never where dimming does nothing'
assert 'virtual bool supportsBrightness() const { return false; }' in DRV, 'drivers without dimming default to unsupported'
for drv in ('src/helpers/ui/SSD1306Display.h', 'src/helpers/ui/SH1106Display.h', 'src/helpers/ui/ST7735Display.h'):
    assert 'supportsBrightness() const override { return true; }' in (ROOT / drv).read_text(), drv
for drv in ('src/helpers/ui/ST7789Display.h', 'src/helpers/ui/ST7789LCDDisplay.h', 'src/helpers/ui/GxEPDDisplay.h',
            'src/helpers/ui/E213Display.h', 'src/helpers/ui/E290Display.h'):
    assert 'supportsBrightness' not in (ROOT / drv).read_text(), drv + ' (T190/e-ink path) must stay unsupported'
# enum appended after the existing last value, so saved/ordered values keep their numbers
assert re.search(r'SpeciesSet,[^\n]*\n\s*DimSlow', MENU)
assert '"SLOW WHEN DIM"' in UI and UI.count('LoRaFishSetting::DimSlow') >= 4
assert '"Slow when dimmed"' in UI
# Display menu row exists only when supported, appended after the existing rows
assert 'rows.dimSlow = loRaFishDimSlowSupported;' in UI
assert re.search(r'DisplayUpdate,\s*DimSlow,\s*(SerialSpeed,\s*)?Count', MENU)   # SerialSpeed was appended after DimSlow (Nova baud setting)

# ---- settings format: one optional tail, size 106 -> 112 ----------------
assert 'LORAFISH_SETTINGS_SIZE = 112;' in UI
assert 'memcpy(data+106,"DIM1",4); data[110]=loRaFishDimSlow ? 1 : 0; data[111]=0;' in UI
art_crc = UI.index('data[104]=artCRC; data[105]=artCRC>>8;')
assert UI.index('memcpy(data+106,"DIM1",4)') > art_crc, 'ART1 block and its CRC are untouched'
assert 'LoRaFishSpecies::checksum(data+90,14)' in UI, 'ART1 checksum range unchanged'

# ---- harness: real timer block + helper + settings tail ------------------
timer = between(UI, '    if (loRaFishNovaNotice || loRaFishChannelNotice || loRaFishNameNotice) return 2000;',
                '    return 2000;                                     // static pages', True)
helper = between(UI, 'static bool loRaFishDimSlowActive() {', '\n}\n', True)
tail = between(UI, '    uint8_t dimSlow[6] = {};', 'loRaFishDimSlow = dimSlow[4];', True)
art_read = between(UI, '    const bool hasArt=f.read(art,sizeof(art))==sizeof(art);', '\n')
encode_tail = between(UI, '  memcpy(data+106,"DIM1"', '\n', True)

HARNESS = r'''
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#define LORAFISH_UI 1
#ifndef LORAFISH_DX_CONTACT_PAGE_VALUE
#define LORAFISH_DX_CONTACT_PAGE_VALUE 4
#endif
static constexpr uint8_t LORAFISH_DX_CONTACT_PAGE = LORAFISH_DX_CONTACT_PAGE_VALUE;
static constexpr uint8_t LORAFISH_RANGE_PAGE = 21;
static bool loRaFishNovaNotice=false, loRaFishChannelNotice=false, loRaFishNameNotice=false, loRaFishScreenDimmed=false;
static bool loRaFishDimSlowSupported=true;
static uint8_t loRaFishDimSlow=0, loRaFishPage=0, loRaFishSimulationMode=0;
@@HELPER@@
static int timerDelay() {
@@TIMER@@
}
struct File {
  std::vector<uint8_t> b; size_t c=0;
  int read(uint8_t* d, size_t n){ size_t a=c<b.size()?b.size()-c:0; size_t k=n<a?n:a; if(k) memcpy(d,b.data()+c,k); c+=k; return (int)k; }
};
static void load(File& f) {
  loRaFishDimSlow = 0;
  uint8_t art[16]={};
@@ARTREAD@@
  (void)hasArt;
@@TAIL@@
}
static void encodeTail(uint8_t* data) {
@@ENCODE@@
}
int main(int argc,char**argv) {
  auto expect=[](bool ok,const char* what){ if(!ok){ printf("FAIL %s\n",what); exit(1);} };
  expect(loRaFishDimSlow==0, "default is Off");
  // Setting Off: timer unchanged whether dimmed or not.
  for (int mode=0;mode<3;++mode) {
    loRaFishSimulationMode=mode;
    loRaFishDimSlow=0; loRaFishScreenDimmed=false; int base=timerDelay();
    loRaFishScreenDimmed=true; expect(timerDelay()==base, "Off + dimmed leaves the timer unchanged");
    // On but not dimmed: unchanged.
    loRaFishDimSlow=1; loRaFishScreenDimmed=false; expect(timerDelay()==base, "On + not dimmed leaves the timer unchanged");
    // On and dimmed: one redraw per second.
    loRaFishScreenDimmed=true; expect(timerDelay()==1000, "On + dimmed returns 1000 ms");
    // Unsupported panel (e-ink / no real dimming): never changes the timer.
    loRaFishDimSlowSupported=false; expect(timerDelay()==base, "unsupported panel unchanged");
    loRaFishDimSlowSupported=true;
  }
  // Other pages are never touched.
  loRaFishDimSlow=1; loRaFishScreenDimmed=true;
  for (int page : {1,2,3,4,5,6,8,12}) { loRaFishPage=page; int d=timerDelay(); expect(d==1000||d==2000, "other pages keep their cadence"); }
  loRaFishPage=2; expect(timerDelay()==1000, "clock page 1000");
  loRaFishPage=3; expect(timerDelay()==2000, "static page 2000 even when dimmed");
  loRaFishPage=0; loRaFishSimulationMode=0; loRaFishDimSlow=0; loRaFishScreenDimmed=true;
  int normal=timerDelay(); printf("NORMAL %d\n",normal);
  // Settings tail.
  uint8_t rec[112]={}; memset(rec,0xAA,sizeof(rec)); // base bytes irrelevant to the tail
  loRaFishDimSlow=1; encodeTail(rec);
  expect(!memcmp(rec+106,"DIM1",4) && rec[110]==1 && rec[111]==0, "On encodes DIM1,1,0");
  loRaFishDimSlow=0; encodeTail(rec);
  expect(!memcmp(rec+106,"DIM1",4) && rec[110]==0 && rec[111]==0, "Off encodes DIM1,0,0");
  // Fake CRC-valid ART1 is not needed: loader only needs 16 readable bytes before the tail.
  auto fileOf=[&](size_t total, uint8_t on, const char* tag="DIM1", uint8_t pad=0){
    File f; f.b.assign(total,0); f.c=90;  // position at the ART1 block, like the real reader
    if(total>=112){ memcpy(&f.b[106],tag,4); f.b[110]=on; f.b[111]=pad; }
    return f; };
  { File f=fileOf(112,1); load(f); expect(loRaFishDimSlow==1, "new 112-byte file with On loads On"); }
  { File f=fileOf(112,0); load(f); expect(loRaFishDimSlow==0, "new file with Off loads Off"); }
  { File f=fileOf(106,1); load(f); expect(loRaFishDimSlow==0, "old 106-byte save loads default Off"); }
  { File f=fileOf(90+10,1); load(f); expect(loRaFishDimSlow==0, "older/short save loads default Off"); }
  { File f=fileOf(112,2); load(f); expect(loRaFishDimSlow==0, "out-of-range value ignored"); }
  { File f=fileOf(112,1,"XXXX"); load(f); expect(loRaFishDimSlow==0, "wrong tag ignored"); }
  { File f=fileOf(112,1,"DIM1",1); load(f); expect(loRaFishDimSlow==0, "non-zero reserved ignored"); }
  { File f=fileOf(110,1); load(f); expect(loRaFishDimSlow==0, "truncated tail ignored"); }
  printf("OK\n");
}
'''
HARNESS = (HARNESS.replace('@@HELPER@@', helper).replace('@@TIMER@@', timer)
           .replace('@@ARTREAD@@', art_read).replace('@@TAIL@@', tail).replace('@@ENCODE@@', encode_tail.strip()))
# The tail is guarded by hasArt in production; keep that guard when the tail was cut out.
assert 'hasArt &&' in UI[UI.index('uint8_t dimSlow[6]'):UI.index('uint8_t dimSlow[6]') + 160]

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / 'h.cpp'
    src.write_text(HARNESS)
    for label, flags in (('standard', []),
                         ('cardputer-25d', ['-DLORAFISH_CARDPUTER_25D']),
                         ('cardputer-25d-10fps', ['-DLORAFISH_CARDPUTER_25D', '-DLORAFISH_25D_10FPS'])):
        exe = Path(tmp) / ('h_' + label)
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Werror', '-Wno-unused-function', '-o', str(exe), str(src)] + flags,
                       check=True)
        out = subprocess.run([str(exe)], capture_output=True, text=True)
        assert out.returncode == 0 and out.stdout.strip().endswith('OK'), (label, out.stdout, out.stderr)
        print(label, 'timer/settings checks PASS')

# E-ink: nothing in the e-ink drivers or the 1 fps mode was changed by this feature.
import subprocess as sp
changed = sp.run(['git', '-C', str(ROOT), 'diff', '--name-only', 'origin/feat/natural-idle-water...HEAD'],
                 capture_output=True, text=True).stdout.split()
for name in changed:
    assert not re.search(r'(GxEPD|E213|E290|Eink|eink|EInk)', name), 'e-ink driver touched: ' + name
print('Slow animation when dimmed: default Off, timer rules, settings tail, e-ink untouched PASS')

