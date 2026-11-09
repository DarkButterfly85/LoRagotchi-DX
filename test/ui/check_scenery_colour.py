#!/usr/bin/env python3
"""Colour scenery for every colour display; monochrome output unchanged.

Host checks of the production scenery code (functions are sliced out of UITask.cpp and compiled
against a recording display). Not a hardware or timing test: nothing here sees a real panel.

* colour panels without a scenery macro of their own (T190, T114, V4 TFT: native; ST7735: 64-row
  logical) draw the colour tank on Water/DX tanks; Air and Land habitats are left as they were
* T-Deck and Cardputer pixels are identical to the build before this change
* monochrome (1-bit OLED, e-ink, colour flag off) pixels are identical to the build before this change
  (test/ui/scenery_legacy_pixels.json, recorded from the pre-change UITask.cpp)
* no scenery code names a board
"""
import argparse, concurrent.futures, json, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / 'examples/companion_radio/ui-new/UITask.cpp'
LEGACY = Path(__file__).with_name('scenery_legacy_pixels.json')


def block(src, marker):
    a = src.index(marker)
    i = src.index('{', a)
    j, depth = i + 1, 1
    while depth:
        depth += (src[j] == '{') - (src[j] == '}')
        j += 1
    return src[a:j]


def maybe(src, marker, wrap=None):
    if marker not in src:
        return ''
    b = block(src, marker)
    return f'#if {wrap}\n{b}\n#endif\n' if wrap else b + '\n'


def preamble(src, func, start_marker, end_marker):
    body = block(src, func)
    a = body.index(start_marker) + len(start_marker)
    b = body.index(end_marker, a)
    return body[a:b]


# Macro sets: what the real build defines for each family of display driver.
MACRO_SETS = {
    'plain': [],                                              # SSD1306/SH1106/SH1107/e-ink/...
    'rgb565': ['-DLORAGOTCHI_RGB565_PANEL=1'],                # ST7735 (T096, Wireless Tracker, T1 ...)
    'rgb565_native': ['-DLORAGOTCHI_RGB565_PANEL=1', '-DLORAGOTCHI_NATIVE_UI=1'],  # T190, T114, V4 TFT
    'tdeck': ['-DLORAGOTCHI_RGB565_PANEL=1', '-DLORAFISH_TDECK_PIXEL_ART=1'],
    'cardputer': ['-DLORAFISH_CARDPUTER_25D=1'],
}
# (name, width, height, colour flag) drawn by each macro set.
DISPLAYS = {
    'plain': [('oled128x64', 128, 64, 0), ('eink250x122', 250, 122, 0)],
    'rgb565': [('st7735_128x64', 128, 64, 1), ('st7735_flag_off', 128, 64, 0)],
    'rgb565_native': [('t190_320x146', 320, 146, 1), ('t114_240x111', 240, 111, 1),
                      ('v4tft_320x216', 320, 216, 1), ('native_flag_off', 320, 146, 0)],
    'tdeck': [('tdeck_128x64', 128, 64, 1)],
    'cardputer': [('cardputer_240x135', 240, 135, 1)],
}
EDITIONS = {
    'dx': ['-DLORAGOTCHI_DXPRO=0'],
    'water': ['-DLORAGOTCHI_WATER_EDITION=1'],
    'air': ['-DLORAGOTCHI_AIR_EDITION=1'],
    'land': ['-DLORAGOTCHI_LAND_EDITION=1'],
    'dxpro': ['-DLORAGOTCHI_DXPRO=1'],
}
TICKS = (0, 1234, 5678, 98765)
# Changed on purpose: colour flag on, a colour panel with no scenery macro, and a tank (not sky/meadow).
COLOUR_SETS = ('rgb565', 'rgb565_native')


def harness(src):
    v = lambda *a: maybe(src, *a)
    colour_def = ''
    m = re.search(r'(// Colour tank scenery.*?\n#endif\n)', src, re.S)
    if m:
        colour_def = m.group(1)
    awake = preamble(src, 'static void drawLoRaFishAquarium(',
                     'loRaFishClock(tb,sizeof(tb),db,sizeof(db));\n', '  int x=0, y=0;')
    sleeping = preamble(src, 'static void drawLoRaFishSleeping(',
                        'loRaFishClock(tb,sizeof(tb),db,sizeof(db));\n',
                        '  drawLoRaFishHeader(display,loRaFishDisplayName(),tb);')
    pre = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "examples/companion_radio/LoRaGotchiVersion.h"
#include "examples/companion_radio/LoRaFishSpecies.h"
using ColorVal=uint16_t;
struct UIColor{static ColorVal window_bkg,secondary_txt,primary_txt;};
ColorVal UIColor::window_bkg=0,UIColor::secondary_txt=1,UIColor::primary_txt=1;
static bool loRaFishColorDisplay=false;
static uint16_t loRaFishSpecies=0;
static unsigned long tick=0;
static unsigned long millis(){return tick;}
struct UITask{};
struct DisplayDriver{
 int w,h;std::vector<uint16_t>px;uint16_t color=0;
 DisplayDriver(int ww,int hh):w(ww),h(hh),px((size_t)ww*hh,0){}
 int width()const{return w;}int height()const{return h;}
 void setColor(ColorVal c){color=c;}
 void fillRect(int x,int y,int ww,int hh){
  for(int j=std::max(0,y);j<std::min(h,y+hh);++j)for(int i=std::max(0,x);i<std::min(w,x+ww);++i)px[(size_t)j*w+i]=color;}
 void drawRect(int x,int y,int ww,int hh){fillRect(x,y,ww,1);fillRect(x,y+hh-1,ww,1);fillRect(x,y,1,hh);fillRect(x+ww-1,y,1,hh);}
 uint16_t at(int x,int y)const{return px[(size_t)y*w+x];}
 unsigned long long hash()const{unsigned long long k=14695981039346656037ULL;
  for(uint16_t c:px)for(unsigned b:{unsigned(c&255),unsigned(c>>8)}){k^=b;k*=1099511628211ULL;}return k;}
};
#define LORAFISH_SCENERY_CANVAS(d) (d)   /* the non-T-Watch definition in UITask.cpp */
static const char* loRaFishDisplayName(){return "x";}
static void drawLoRaFishHeader(DisplayDriver&,const char*,const char*){}
static void drawLoRaFishTankBattery(DisplayDriver&,UITask*,const char*){}
'''
    body = colour_def + '\n'
    body += v('static inline void fishPixel(') + v('static void fishLine(')
    body += v('static void drawCardputerTankDepth(',
              'defined(LORAFISH_CARDPUTER_25D) || defined(LORAFISH_COLOUR_TANK)')
    body += v('static void drawTDeckPixelAquarium(',
              'defined(LORAFISH_TDECK_PIXEL_ART) || defined(LORAFISH_COLOUR_TANK)')
    body += v('static void drawLoRaFishBubbles(')
    body += v('static void drawLoRaFishAirHabitat(', 'LORAGOTCHI_HAS_AIR')
    body += v('static void drawLoRaFishLandHabitat(', 'LORAGOTCHI_HAS_LAND')
    body += v('static bool loRaFishAnimalHome(')
    body += v('static void drawLoRaFishColourTank(', 'defined(LORAFISH_COLOUR_TANK)')
    body += v('static bool loRaFishColourTank(')
    body += v('static void drawLoRaFishNativeScenery(')
    body += v('static void drawLoRaFishWaterNativeScenery(', 'LORAGOTCHI_DXPRO')
    body += v('static void drawLoRaFishHomeScenery(', 'LORAGOTCHI_DXPRO')
    body += f'''
static void sceneAwake(DisplayDriver& display,UITask* task){{
 const int w=display.width(),h=display.height();char tb[8],db[24];(void)task;(void)w;(void)h;(void)db;tb[0]=0;
{awake}
}}
static void sceneSleeping(DisplayDriver& display,UITask* task){{
 const int w=display.width(),h=display.height();char tb[8],db[24];(void)task;(void)w;(void)h;(void)db;tb[0]=0;
{sleeping}
}}
'''
    main = r'''
struct Spec{const char* name;int w,h;bool colour;};
int main(int argc,char** argv){
 const Spec specs[]={DISPLAY_TABLE};
 // First species of each habitat set, from the production registry.
 uint16_t water=0,air=0,land=0;
 for(uint16_t id=600;id-->0;){   // lowest id of each set wins (water is id 0)
  if(LoRaFishSpecies::waterKnown(id))water=id;
  if(LoRaFishSpecies::airKnown(id))air=id;
  if(LoRaFishSpecies::landKnown(id))land=id;
 }
 assert(LoRaFishSpecies::waterKnown(water)&&LoRaFishSpecies::airKnown(air)&&LoRaFishSpecies::landKnown(land));
 for(const Spec& s:specs){
  const ColorVal midnight[]={0x0861,0x9CF3,0xEF7D};
  UIColor::window_bkg=s.colour?midnight[0]:0;UIColor::secondary_txt=s.colour?midnight[1]:1;
  UIColor::primary_txt=s.colour?midnight[2]:1;loRaFishColorDisplay=s.colour;
  const uint16_t ids[3]={water,air,land};const char* names[3]={"water","air","land"};
  for(int k=0;k<3;++k){
#if !LORAGOTCHI_DXPRO
   if(k)break;          // single-edition builds ignore the species id for scenery
#endif
   loRaFishSpecies=ids[k];
   for(unsigned long t:{TICKS}){
    tick=t;
    DisplayDriver a(s.w,s.h),z(s.w,s.h);
    a.px.assign(a.px.size(),UIColor::window_bkg);z.px.assign(z.px.size(),UIColor::window_bkg);
    UITask task;sceneAwake(a,&task);sceneSleeping(z,&task);
    printf("%s.%s.awake.%lu %016llx\n",s.name,names[k],t,a.hash());
    printf("%s.%s.sleep.%lu %016llx\n",s.name,names[k],t,z.hash());
#if defined(METRICS) && defined(LORAFISH_COLOUR_TANK)
    if(s.colour&&k==0){
     // Tank rows (17 .. h-17) are fully painted water/reef/sand, never left on the window colour.
     int bare=0;for(int y=17;y<s.h-17;++y)for(int x=0;x<s.w;++x)if(a.at(x,y)==UIColor::window_bkg)++bare;
     printf("%s.bare.%lu %d\n",s.name,t,bare);
     std::vector<uint16_t> seen;for(int y=0;y<s.h;++y)for(int x=std::max(0,s.w-40);x<s.w;++x){
      uint16_t c=a.at(x,y);if(std::find(seen.begin(),seen.end(),c)==seen.end())seen.push_back(c);}
     printf("%s.rightcolours.%lu %d\n",s.name,t,(int)seen.size());
     if(s.w>240){
      // Layout is the 240 px one, repeated: the left 240 columns match a 240-wide render.
      DisplayDriver n(240,s.h);n.px.assign(n.px.size(),UIColor::window_bkg);
      DisplayDriver q(s.w,s.h);q.px.assign(q.px.size(),UIColor::window_bkg);
      drawLoRaFishColourTank(n);drawLoRaFishColourTank(q);
      bool same=true;for(int y=0;y<s.h;++y)for(int x=0;x<240;++x)if(n.at(x,y)!=q.at(x,y))same=false;
      printf("%s.leftmatch.%lu %d\n",s.name,t,same?1:0);
      // Light shafts (0x2B75) continue past x=240 instead of stopping at the Cardputer width.
      int shafts=0;for(int y=0;y<s.h;++y)for(int x=240;x<s.w;++x)if(q.at(x,y)==0x2B75)++shafts;
      printf("%s.shafts.%lu %d\n",s.name,t,shafts);
     }
    }
#endif
   }
  }
 }
 (void)argc;(void)argv;
}
'''
    return pre + body + main


def build_and_run(src, edition, mset, metrics, tmp):
    code = harness(src)
    table = ','.join(f'{{"{n}",{w},{h},{int(c)}}}' for n, w, h, c in DISPLAYS[mset])
    code = code.replace('DISPLAY_TABLE', table).replace('{TICKS}', '{' + ','.join(f'{t}UL' for t in TICKS) + '}')
    name = f'{edition}-{mset}'
    cpp = Path(tmp) / f'{name}.cpp'
    cpp.write_text(code)
    exe = Path(tmp) / name
    cmd = ['g++', '-std=c++17', '-O0', '-w', '-I', str(ROOT), '-I', str(ROOT / 'src'),
           *MACRO_SETS[mset], *EDITIONS[edition], str(cpp), '-o', str(exe)]
    if metrics:
        cmd.append('-DMETRICS')
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:3000]
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    return {f'{edition}.{mset}.{k}': v for k, v in (l.split() for l in out.splitlines())}


def run_all(src, metrics=False):
    results = {}
    with tempfile.TemporaryDirectory(prefix='dx-scenery-') as tmp:
        jobs = [(e, m) for e in EDITIONS for m in MACRO_SETS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(build_and_run, src, e, m, metrics, tmp) for e, m in jobs]
            for f in futs:
                results.update(f.result())
    return results


def changed(key):
    """True for the scenes that should now draw the colour tank."""
    edition, mset, rest = key.split('.', 2)
    if mset not in COLOUR_SETS:
        return False
    display, kind = rest.split('.')[:2]
    if display in ('st7735_flag_off', 'native_flag_off'):
        return False
    if edition in ('air', 'land'):
        return False
    if edition == 'dxpro':
        return kind == 'water'
    return True   # dx and water editions: a tank whatever the species id


def static_checks(src):
    ui = src
    # 1. Which drivers announce a colour RGB565 panel.
    defining = set()
    for p in list((ROOT / 'src/helpers/ui').glob('*.h')) + list((ROOT / 'variants').glob('*/*.h')):
        t = p.read_text(errors='ignore')
        if re.search(r'^\s*#\s*define\s+LORAGOTCHI_RGB565_PANEL\b', t, re.M):
            defining.add(p.name)
            assert re.search(r'bool supportsColor\(\) const override \{ return true; \}', t), \
                f'{p.name} announces a colour panel but supportsColor() is not true'
    assert defining == {'ST7735Display.h', 'ST7789LCDDisplay.h'}, defining
    # Every 1-bit / e-ink / null / OLED-library driver is absent from that set.
    for mono in ('SSD1306Display.h', 'SH1106Display.h', 'SH1107Display.h', 'OLEDDisplay.h', 'U8g2Display.h',
                 'GxEPDDisplay.h', 'E213Display.h', 'E290Display.h', 'NullDisplayDriver.h',
                 'ST7789Display.h', 'NV3001BDisplay.h'):
        assert mono not in defining, mono
        t = (ROOT / 'src/helpers/ui' / mono).read_text(errors='ignore')
        assert not re.search(r'supportsColor\(\) const override \{ return true; \}', t), mono
    # 2. The macro rule itself: colour panels, never in front of the T-Deck / Cardputer scenery.
    assert ('#if defined(LORAGOTCHI_RGB565_PANEL) && !defined(LORAFISH_CARDPUTER_25D) && '
            '!defined(LORAFISH_TDECK_PIXEL_ART)\n#define LORAFISH_COLOUR_TANK 1\n#endif') in ui
    # 3. No scenery code names a board.
    boards = re.compile(r'HELTEC|LILYGO|TDECK|T190|T114|T096|T-?DECK|CARDPUTER|M5|TWATCH|WATCH|\bV[34]\b|RAK|ESP32|NRF|'
                        r'THINKNODE|WIO|XIAO|STATION|TBEAM|ST77|SSD1306|SH110|E213|E290', re.I)
    for fn in ('static void drawCardputerTankDepth(', 'static void drawTDeckPixelAquarium(',
               'static void drawLoRaFishColourTank(', 'static bool loRaFishColourTank('):
        body = block(ui, fn)
        body = re.sub(r'//[^\n]*', '', body)       # comments may say 'Cardputer'; code may not
        body = body[body.index('{'):]               # the name of the function is not its body
        body = body.replace('drawCardputerTankDepth', '').replace('drawTDeckPixelAquarium', '')  # layout names
        assert not boards.search(body), (fn, boards.search(body).group(0))
    # 4. Every colour tank call is guarded by the runtime colour flag; the grey perimeter is only
    #    skipped through loRaFishColourTank(), which is false on mono.
    for m in re.finditer(r'^.*drawLoRaFishColourTank\(display\).*$', ui, re.M):
        assert 'loRaFishColorDisplay' in m.group(0), m.group(0)
    assert len(re.findall(r'drawLoRaFishColourTank\(display\)', ui)) == 4
    assert len(re.findall(r'if \(!loRaFishColourTank\(\)\) drawLoRaFish(Home|Native)Scenery\(display\);', ui)) == 4
    body = block(ui, 'static bool loRaFishColourTank(')
    assert 'return loRaFishColorDisplay && !loRaFishAnimalHome();' in body and 'return false;' in body
    # 5. Tall panels use the Cardputer layout, 64-row panels the T-Deck layout.
    body = block(ui, 'static void drawLoRaFishColourTank(')
    assert re.sub(r'\s+', '', body).endswith('if(d.height()>64)drawCardputerTankDepth(d);elsedrawTDeckPixelAquarium(d);}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--record-baseline-from', type=Path,
                    help='Maintenance only: record pre-change pixel signatures from an old UITask.cpp')
    args = ap.parse_args()
    if args.record_baseline_from:
        res = run_all(args.record_baseline_from.read_text())
        LEGACY.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
        print('recorded', len(res), 'legacy signatures')
        return
    src = UI.read_text()
    static_checks(src)
    print('PASS drivers: only the ST7789 LCD and ST7735 drivers announce a colour RGB565 panel; '
          'mono/e-ink/1-bit drivers do not; no scenery function names a board')
    legacy = json.loads(LEGACY.read_text())
    now = run_all(src, metrics=True)
    sig = {k: v for k, v in now.items() if k.rsplit('.', 2)[-2] in ('awake', 'sleep')}
    assert set(sig) == set(legacy), set(sig) ^ set(legacy)
    n_same = n_changed = 0
    for k in sorted(sig):
        if changed(k):
            assert sig[k] != legacy[k], f'colour display still draws the old scenery: {k}'
            n_changed += 1
        else:
            assert sig[k] == legacy[k], f'pixels changed where they must not: {k}'
            n_same += 1
    print(f'PASS {n_same} scene signatures identical to the pre-change build '
          '(OLED 128x64, e-ink, colour-flag-off, Air/Land habitats, T-Deck, Cardputer)')
    print(f'PASS {n_changed} colour-display tank scenes differ from the old build (colour tank drawn)')
    # Colour tank metrics: tank rows fully painted, wide panels keep the layout and fill their width.
    seen = {'bare': 0, 'rightcolours': 0, 'leftmatch': 0, 'shafts': 0}
    for k, v in now.items():
        parts = k.split('.')
        if len(parts) < 4 or parts[-2] not in seen:
            continue
        seen[parts[-2]] += 1
        edition, mset, display = parts[0], parts[1], parts[2]
        if not changed(f'{edition}.{mset}.{display}.water.awake.0'):
            continue
        if parts[-2] == 'bare':
            assert int(v) == 0, (k, v)
        if parts[-2] == 'rightcolours':
            assert int(v) >= 5, (k, v)          # reef, sand, weed and water reach the right edge
        if parts[-2] == 'shafts':
            assert int(v) > 0, (k, v)
        if parts[-2] == 'leftmatch':
            assert v == '1', (k, v)
    assert all(seen.values()), seen
    # ST7735 shares the T-Deck layout exactly: same logical frame, same pixels.
    for e in ('dx', 'water', 'dxpro'):
        for t in TICKS:
            for scene in ('awake', 'sleep'):
                a = now[f'{e}.rgb565.st7735_128x64.water.{scene}.{t}']
                b = now[f'{e}.tdeck.tdeck_128x64.water.{scene}.{t}']
                assert a == b, (e, scene, t)
    print('PASS colour tank: tank rows fully painted, reef/weed reach the right edge of 320 px panels, '
          'left 240 columns equal the Cardputer layout, ST7735 equals the T-Deck frame')


if __name__ == '__main__':
    main()
