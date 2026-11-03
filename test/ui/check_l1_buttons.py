#!/usr/bin/env python3
"""Host GPIO-timeline regression using real board constructors, button recognizer,
and UITask input dispatch/menu handlers. No physical-board claim."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("menu", Path(__file__).with_name("check_menu_navigation.py"))
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)
source = menu.source
start = source.index("#if UI_HAS_JOYSTICK\n", source.index("void UITask::loop()"))
end = source.index("#if defined(UI_HAS_ROTARY_INPUT)", start)
dispatch = source[start:end]
parts = list(menu.parts)
# Retain all production handler bodies and test stubs, replace only test main.
parts[-1] = parts[-1].split("int main(){", 1)[0]
parts = [p.replace("  char handleTripleClick(char);", "  char handleTripleClick(char);\n  char pollButtons();") for p in parts]
preamble = r'''
#include <helpers/ui/MomentaryButton.h>
static int levels[64];
int digitalRead(int pin){return levels[pin];}
int analogRead(int pin){return levels[pin];}
void pinMode(int,int){}
#define KEY_SELECT 's'
'''
tests = r'''
char UITask::pollButtons(){char c=0;
DISPATCH
return c;}
static void poll(UITask& task){char c=task.pollButtons();if(c)shortPress(c);}
static void step(UITask& task,int ms){for(int i=0;i<ms;++i){++tick;poll(task);}}
static void press(UITask& task,int pin,int duration=40){levels[pin]=LOW;step(task,duration);levels[pin]=HIGH;step(task,1);}
static void clicks(UITask& task,int pin,int count){for(int i=0;i<count;++i){press(task,pin);step(task,60);}step(task,281);}
static void hold(UITask& task,int pin){press(task,pin,1001);step(task,281);}
int main(){
  for(auto& level:levels)level=HIGH;
  UITask task;
  user_btn.begin();
#if UI_HAS_JOYSTICK
  joystick_left.begin();joystick_right.begin();back_btn.begin();
#endif
  // Reach Options from aquarium through actual GPIO click timelines.
  loRaFishPage=0;
  for(int i=0;i<5;++i)clicks(task,PIN_USER_BTN,1);
  assert(loRaFishPage==5);
  clicks(task,PIN_USER_BTN,2);
  fprintf(stderr,"center double from Options -> page %u\n",loRaFishPage);
  assert(loRaFishPage==0);
  for(int i=0;i<5;++i)clicks(task,PIN_USER_BTN,1);
  loRaFishOption=LoRaFishOption::Display;hold(task,PIN_USER_BTN);
  assert(loRaFishPage==12);
  clicks(task,PIN_USER_BTN,2);assert(loRaFishPage==5 && loRaFishOption==LoRaFishOption::Display);
  hold(task,PIN_USER_BTN);assert(loRaFishPage==12);
  loRaFishPage=13;openLoRaFishValue(LoRaFishSetting::Brightness);
  int writes=settingsWrites;clicks(task,PIN_USER_BTN,1);
  clicks(task,PIN_USER_BTN,2);assert(!loRaFishValuePicker.active() && loRaFishPage==12 && settingsWrites==writes);
  clicks(task,PIN_USER_BTN,2);assert(loRaFishPage==5);
  task.display.turnOff();clicks(task,PIN_USER_BTN,2);assert(task.display.isOn() && loRaFishPage==5);
#if UI_HAS_JOYSTICK
  // Dedicated L1 Menu/User key is separate from the centre press.
  loRaFishPage=5;loRaFishOption=LoRaFishOption::Display;
  clicks(task,PIN_BACK_BTN,2);
  fprintf(stderr,"separate Menu/User double from Options -> page %u\n",loRaFishPage);
  assert(loRaFishPage==0);
  loRaFishPage=5;auto option=loRaFishOption;
  clicks(task,PIN_BACK_BTN,1);assert(loRaFishPage==5 && loRaFishOption==option);
  int toggles=task.buzzerToggles;clicks(task,PIN_BACK_BTN,3);assert(task.buzzerToggles==toggles+1);
  loRaFishOption=LoRaFishOption::Advert;clicks(task,JOYSTICK_RIGHT,1);
  assert(loRaFishOption!=LoRaFishOption::Advert);clicks(task,JOYSTICK_LEFT,1);
  assert(loRaFishOption==LoRaFishOption::Advert);
#endif
  assert(resets==0 && the_mesh.sends==0 && the_mesh.dxSends==0);
  puts("PASS GPIO-to-menu: entry, double Back, parent return, hold Select, editor cancel/no writes, wake-only, directional navigation, triple preserved");
}
'''.replace("DISPATCH", dispatch)

with tempfile.TemporaryDirectory(prefix="loragotchi-buttons-") as temp:
    temp = Path(temp)
    (temp / "Arduino.h").write_text("""#pragma once
#include <cstdint>
#define HIGH 1
#define LOW 0
#define INPUT 0
#define INPUT_PULLUP 2
#define INPUT_PULLDOWN 3
unsigned long millis();
int digitalRead(int);
int analogRead(int);
void pinMode(int,int);
""")
    for board in ["wio-tracker-l1", "wio-tracker-l1-1w", "heltec_v3", "heltec_v4"]:
        target = (root / "variants" / board / "target.cpp").read_text()
        # Extract the literal production object declarations (including conditional flags).
        constructors = "#ifdef DISPLAY_CLASS" + target.split("#ifdef DISPLAY_CLASS", 1)[1].split("bool radio_init", 1)[0]
        constructors = "\n".join(line for line in constructors.splitlines() if "DISPLAY_CLASS display" not in line)
        for water in [0, 1]:
            for sound in [False, True]:
                cpp = temp / "buttons.cpp"
                cpp.write_text("\n".join(parts + [preamble, constructors, tests]))
                args = ["g++", "-std=c++17", "-DDISPLAY_CLASS=1", "-DPIN_USER_BTN=29" if board.startswith("wio") else "-DPIN_USER_BTN=0",
                        "-DUI_HAS_JOYSTICK="+str(int(board.startswith("wio"))), "-DWIO_TRACKER_L1=1" if board.startswith("wio") else "-DHELv=1",
                        "-DPIN_BACK_BTN=13", "-DJOYSTICK_LEFT=27", "-DJOYSTICK_RIGHT=28", "-DLORAGOTCHI_WATER_EDITION="+str(water),
                        "-I"+str(temp), "-I"+str(root), "-I"+str(root / "src"), str(cpp), str(root / "src/helpers/ui/MomentaryButton.cpp"), "-o", str(temp / "buttons")]
                if sound: args.append("-DPIN_BUZZER=12")
                subprocess.run(args, check=True)
                print(f"{board} water={water} sound={sound}", flush=True)
                subprocess.run([str(temp / "buttons")], check=True)

    # Stock MeshCore keeps immediate centre clicks; only LoRagotchi opts in.
    for board in ['wio-tracker-l1', 'wio-tracker-l1-1w']:
        target = (root / 'variants' / board / 'target.cpp').read_text()
        constructors = '#ifdef DISPLAY_CLASS' + target.split('#ifdef DISPLAY_CLASS', 1)[1].split('bool radio_init', 1)[0]
        constructors = '\n'.join(line for line in constructors.splitlines() if 'DISPLAY_CLASS display' not in line)
        cpp = temp / 'stock.cpp'
        cpp.write_text(r'''
#include <cassert>
#include <helpers/ui/MomentaryButton.h>
static unsigned long tick=100;static int levels[64];
unsigned long millis(){return tick;}
int digitalRead(int p){return levels[p];}int analogRead(int p){return levels[p];}
void pinMode(int,int){}
''' + constructors + r'''
int main(){
  for(auto& level:levels)level=HIGH;
  user_btn.begin();
  for(int i=0;i<2;++i){
    levels[PIN_USER_BTN]=LOW;++tick;assert(user_btn.check()==BUTTON_EVENT_NONE);
    tick+=40;levels[PIN_USER_BTN]=HIGH;assert(user_btn.check()==BUTTON_EVENT_CLICK);
    tick+=60;assert(user_btn.check()==BUTTON_EVENT_NONE);
  }
}
''')
        subprocess.run(['g++', '-std=c++17', '-DDISPLAY_CLASS=1', '-DPIN_USER_BTN=29', '-DPIN_BACK_BTN=13', '-DJOYSTICK_LEFT=27', '-DJOYSTICK_RIGHT=28', '-I'+str(temp), '-I'+str(root/'src'), str(cpp), str(root/'src/helpers/ui/MomentaryButton.cpp'), '-o', str(temp/'stock')], check=True)
        subprocess.run([str(temp/'stock')], check=True)
        print('PASS stock immediate-click behavior unchanged:', board, flush=True)
