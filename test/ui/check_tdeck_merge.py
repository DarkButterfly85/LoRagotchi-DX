#!/usr/bin/env python3
"""Compile actual combined UITask touch routing; no hardware/I2C claim."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'examples/companion_radio/ui-new/UITask.cpp').read_text()
a=s.index('  if (tdeckTouchEventReady && _display)');b=s.index('\n#endif',a)
route=s[a:b]
pre=r'''
#include <cassert>
#include <cstdlib>
struct Display {bool on=true; int width(){return 320;} int height(){return 240;} bool isOn(){return on;}} d;
Display* _display=&d;
bool tdeckTouchEventReady=true;
int tdeckTouchEndX=160,tdeckTouchEndY=100,tdeckTouchDeltaX=0,tdeckTouchDeltaY=0;
int _next_refresh=99,c=0,action=0;
enum {KEY_NEXT=1,KEY_PREV=2,KEY_ENTER=3};
int checkDisplayOn(int key){if(!d.on){d.on=true;action=4;return 0;} action=1;return key;}
int handleDoubleClick(int key){action=2;return key;}
int handleLongPress(int key){action=3;return key;}
void run(){c=action=0;tdeckTouchEventReady=true;
'''
main=r'''
}
int main(){
run();assert(c==KEY_ENTER && action==3 && !tdeckTouchEventReady);
tdeckTouchEndY=10;run();assert(c==KEY_PREV && action==2);
tdeckTouchEndY=100;tdeckTouchEndX=10;run();assert(c==KEY_PREV && action==1);
tdeckTouchEndX=310;run();assert(c==KEY_NEXT && action==1);
tdeckTouchEndX=160;tdeckTouchDeltaX=-50;run();assert(c==KEY_NEXT);
tdeckTouchDeltaX=50;run();assert(c==KEY_PREV);
tdeckTouchDeltaX=0;d.on=false;run();assert(c==0 && action==4 && d.on);
tdeckTouchEndX=320;run();assert(c==0 && action==0);
tdeckTouchEndX=160;tdeckTouchDeltaX=30;run();assert(c==0 && action==0);
}
'''
with tempfile.TemporaryDirectory(prefix='tdeck-merge-') as t:
 p=Path(t);(p/'test.cpp').write_text(pre+route+main)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert 'c = handleLongPress(KEY_ENTER, false);' in s
assert 'c = handleLongPress(KEY_ENTER);' in s
assert 'c = handleDoubleClick(KEY_PREV);' in s
print('PASS combined production T-Deck route: select/back/left/right/swipes/wake/bounds/deadzone; L1 distinct Select retained')
