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
#if UI_HAS_JOYSTICK
  // Real GPIO route: arrows browse, centre selects, small Menu backs out.
  auto next=[&](){clicks(task,JOYSTICK_RIGHT,1);};
  auto prev=[&](){clicks(task,JOYSTICK_LEFT,1);};
  auto enter=[&](){clicks(task,PIN_USER_BTN,1);};
  auto back=[&](){clicks(task,PIN_BACK_BTN,1);};
  auto options=[&](){loRaFishPage=0;for(int i=0;i<5;++i)next();assert(loRaFishPage==5);};
  auto choose=[&](LoRaFishOption o){
    for(int i=0;loRaFishOption!=o && i<12;++i)next();assert(loRaFishOption==o);
    enter();
  };
  loRaFishPage=0;
  enter();assert(loRaFishPage==0 && cleans==0); // Aquarium click cannot clean.
  task.ui_started_at=tick; // Ordinary Enter within rescue window must not rescue.
  options();choose(LoRaFishOption::Display);assert(loRaFishPage==12 && the_mesh.rescues==0);
  hold(task,PIN_USER_BTN);assert(the_mesh.rescues==1 && loRaFishPage==12);
  task.ui_started_at=0;
  back();assert(loRaFishPage==5 && loRaFishOption==LoRaFishOption::Display);
  enter();assert(loRaFishPage==12);
  next();assert(loRaFishDisplayOption==1);enter();
  assert(loRaFishPage==13 && loRaFishValuePicker.active());
  int writes=settingsWrites;next();assert(settingsWrites==writes);
  back();assert(!loRaFishValuePicker.active() && loRaFishPage==12 && settingsWrites==writes);
  enter();next();enter();assert(!loRaFishValuePicker.active() && loRaFishPage==12 && settingsWrites==writes+1);
  back();back();assert(loRaFishPage==0);
  int cleanBefore=cleans;hold(task,PIN_USER_BTN);assert(cleans==cleanBefore+1 && loRaFishPage==0);
  task._alert_expiry=0;loRaFishCleaning=true;hold(task,PIN_USER_BTN);assert(cleans==cleanBefore+1);loRaFishCleaning=false;
  loRaFishPoopCount=0;hold(task,PIN_USER_BTN);assert(cleans==cleanBefore+1);loRaFishPoopCount=1;
  options();
  // Classification must happen before acting: no Enter before centre-double Back,
  // and no Back before the dedicated Menu triple sound toggle.
  loRaFishOption=LoRaFishOption::Reset;clicks(task,PIN_USER_BTN,2);assert(loRaFishPage==0 && resets==0);
  options();auto option=loRaFishOption;int toggles=task.buzzerToggles;
  clicks(task,PIN_BACK_BTN,3);assert(task.buzzerToggles==toggles+1 && loRaFishPage==5 && loRaFishOption==option);
  clicks(task,PIN_BACK_BTN,2);assert(loRaFishPage==0);
  options();
  for(int pin:{PIN_USER_BTN,PIN_BACK_BTN}){
    task.display.turnOff();clicks(task,pin,1);assert(task.display.isOn() && loRaFishPage==5);
  }
  for(int pin:{PIN_USER_BTN,PIN_BACK_BTN}){
    task.display.turnOff();clicks(task,pin,2);assert(task.display.isOn() && loRaFishPage==5);
  }
  clicks(task,PIN_USER_BTN,3);assert(loRaFishPage==5); // No centre triple action.
  hold(task,PIN_BACK_BTN);assert(loRaFishPage==5); // No Menu hold action.
  task.display.turnOff();hold(task,PIN_USER_BTN);assert(task.display.isOn() && loRaFishPage==5);
  // Notices and active alerts consume Select without opening the highlighted action.
  loRaFishChannelNotice=true;enter();assert(!loRaFishChannelNotice && loRaFishPage==5);
  loRaFishNameNotice=true;enter();assert(!loRaFishNameNotice && loRaFishPage==5);
  task._alert_expiry=tick+1000;enter();assert(loRaFishPage==5);task._alert_expiry=0;
  // Advert remains a separate, explicit action; Back never transmits.
  choose(LoRaFishOption::Advert);assert(loRaFishPage==LORAFISH_ADVERT_PAGE && the_mesh.sends==0);
  back();assert(loRaFishPage==5 && the_mesh.sends==0);
  // Reset defaults to Cancel, and Menu always cancels even after choosing Yes.
  choose(LoRaFishOption::Reset);assert(loRaFishPage==LORAFISH_RESET_CONFIRM_PAGE);
  enter();assert(resets==0 && loRaFishPage==5);
  enter();next();back();assert(resets==0 && loRaFishPage==5);
  // Schedule, GNSS and all display rows remain reachable (mono and colour).
  choose(LoRaFishOption::Schedule);assert(loRaFishPage==10);
  enter();assert(loRaFishValuePicker.active());back();back();assert(loRaFishPage==5);
  choose(LoRaFishOption::GNSS);int gps=task.gpsToggles;enter();assert(task.gpsToggles==gps+1);back();
  for(bool color:{false,true}) {
    loRaFishColorDisplay=color;choose(LoRaFishOption::Display);
    for(int row=0;row<loRaFishDisplayOptionCount();++row){
      assert(loRaFishDisplayOption==row);enter();
      if(loRaFishValuePicker.active())back();else {enter();assert(loRaFishValuePicker.active());back();back();}
      assert(loRaFishPage==12 && loRaFishDisplayOption==row);
      next();
    }
    back();
  }
#ifdef PIN_BUZZER
  choose(LoRaFishOption::Sound);assert(loRaFishPage==14);
  for(int row=0;row<4;++row){
    assert(loRaFishSoundField==row);enter();assert(loRaFishValuePicker.active());
    writes=settingsWrites;int previews=task.buzzer.previews;next();back();
    assert(loRaFishPage==14 && settingsWrites==writes && task.buzzer.previews==previews);
    enter();next();enter();assert(settingsWrites==writes+1);
    bool audible=row==0 ? loRaFishBuzzerVolume>0 : row==1 ? loRaFishWakeSound>0 :
        row==2 ? loRaFishSleepSound>0 : loRaFishMessageSound>0;
    assert(task.buzzer.previews==previews+(audible ? 1 : 0));
    if(row==0)assert(task.buzzer.volume==loRaFishBuzzerVolume);
    next();
  }
  back();assert(loRaFishOption==LoRaFishOption::Sound);
#endif
  // DX picker opening/browsing is inert; sleeping send remains blocked.
  back();assert(loRaFishPage==0);for(int i=0;i<4;++i)next();assert(loRaFishPage==4);
  enter();assert(loRaFishPage==LORAFISH_DX_CONTACT_PAGE && the_mesh.dxSends==0);
  next();prev();fishSleeping=true;enter();assert(the_mesh.dxSends==0);fishSleeping=false;task._alert_expiry=0;
  back();assert(loRaFishPage==4);
  // L1-specific instructions fit and accurately describe Enter/save/Back.
  task.display.clearBounds();drawLoRaFishMenuHint(task.display);
  assert(task.display.printed.back()=="CENTER:OK MENU:BACK");
  loRaFishPage=13;openLoRaFishValue(LoRaFishSetting::Brightness);
  task.display.clearBounds();drawLoRaFishValuePicker(task.display);cancelLoRaFishValue();
  loRaFishPage=4;task.display.clearBounds();drawLoRaFishDX(task.display);
  loRaFishPage=LORAFISH_DX_CONTACT_PAGE;task.display.clearBounds();drawLoRaFishDX(task.display);
  assert(resets==0 && the_mesh.sends==0 && the_mesh.dxSends==0);
  // Explicit Enter can still perform each guarded action; browsing never did.
  back();enter();enter();assert(the_mesh.dxSends==1 && loragotchiDXHome.pending);
  back();back();options();choose(LoRaFishOption::Advert);
  enter();assert(the_mesh.sends==1 && loRaFishPage==5);task._alert_expiry=0;
  choose(LoRaFishOption::Reset);next();enter();assert(resets==1);task._alert_expiry=0;
  // Entry routing remains usable with no contacts and during every travel phase.
  for(int contacts:{0,3})for(int phase=0;phase<4;++phase){
    the_mesh.contacts=contacts;loragotchiDXHome.pending=phase==1;
    loragotchiDXHome.committing=phase==2;loragotchiDXHome.away=phase==3;
    int sent=the_mesh.dxSends;options();choose(LoRaFishOption::Display);
    assert(loRaFishPage==12 && the_mesh.dxSends==sent);back();back();
  }
#else
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
#endif
  puts("PASS GPIO-to-menu: single Enter/Back, legacy double/hold, save/cancel, sound, rescue, wake-only, clean, optional rows, guarded actions");
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
        for edition, water, air in [("DX", 0, 0), ("Water", 1, 0), ("Air", 0, 1)]:
            for sound in [False, True]:
                cpp = temp / "buttons.cpp"
                cpp.write_text("\n".join(parts + [preamble, constructors, tests]))
                args = ["g++", "-std=c++17", "-DDISPLAY_CLASS=1", "-DPIN_USER_BTN=29" if board.startswith("wio") else "-DPIN_USER_BTN=0",
                        "-DUI_HAS_JOYSTICK="+str(int(board.startswith("wio"))), "-DWIO_TRACKER_L1=1" if board.startswith("wio") else "-DHELv=1",
                        "-DPIN_BACK_BTN=13", "-DJOYSTICK_LEFT=27", "-DJOYSTICK_RIGHT=28", "-DLORAGOTCHI_WATER_EDITION="+str(water), "-DLORAGOTCHI_AIR_EDITION="+str(air),
                        "-I"+str(temp), "-I"+str(root), "-I"+str(root / "src"), str(cpp), str(root / "src/helpers/ui/MomentaryButton.cpp"), "-o", str(temp / "buttons")]
                if sound: args.append("-DPIN_BUZZER=12")
                subprocess.run(args, check=True)
                print(f"{board} edition={edition} sound={sound}", flush=True)
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
