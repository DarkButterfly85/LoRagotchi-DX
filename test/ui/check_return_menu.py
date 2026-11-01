#!/usr/bin/env python3
"""New return action reached from the actual aquarium route, with and without buzzer."""
from pathlib import Path
import runpy,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
fixture=runpy.run_path(str(root/'test/ui/check_menu_navigation.py'))
parts=fixture['parts'][:-1]+[fixture['parts'][-1].split('int main(){',1)[0]]
parts.append(r'''
int main(){
 for(bool away:{false,true}) {
   UITask empty;tick=100000;empty.ui_started_at=0;loRaFishPage=0;loragotchiDXGuest.present=false;
   loragotchiDXHome.away=away;
   for(int i=0;i<5;i++)shortPress(KEY_NEXT);
   assert(loRaFishPage==5);
   for(int i=0;i<12;i++){shortPress(KEY_NEXT);assert(loRaFishOption!=LoRaFishOption::ReturnGuest);}
 }
 loragotchiDXHome.away=false;
 UITask task;tick=100000;task.ui_started_at=0;loRaFishPage=0;loragotchiDXGuest.present=true;
 for(int i=0;i<5;i++)shortPress(KEY_NEXT);
 assert(loRaFishPage==5 && the_mesh.returnCalls==0);
 for(int i=0;i<12 && loRaFishOption!=LoRaFishOption::ReturnGuest;i++)shortPress(KEY_NEXT);
 assert(loRaFishOption==LoRaFishOption::ReturnGuest);
 task.display.clearBounds();drawLoRaFishOptions(task.display,&task);
 assert(the_mesh.returnCalls==0);
 task.display.turnOff();task.handleLongPress(KEY_ENTER);
 assert(task.display.isOn() && the_mesh.returnCalls==0);
 task.handleLongPress(KEY_ENTER);assert(the_mesh.returnCalls==1 && task.alert=="Return queued");
 task._alert_expiry=0;loragotchiDXGuest.present=false;task.handleLongPress(KEY_ENTER);
 assert(the_mesh.returnCalls==1 && loRaFishOption==LoRaFishOption::Advert);
 for(auto status:{LoRaFishGuestReturn::Pending,LoRaFishGuestReturn::Failed,LoRaFishGuestReturn::Confirmed}){
   loragotchiDXGuestReturn.status=status;loRaFishPage=4;
   for(int state=0;state<4;state++) {
     loragotchiDXHome.away=state==1;loragotchiDXHome.pending=state==2;loragotchiDXHome.committing=state==3;
     task.display.clearBounds();drawLoRaFishDX(task.display);
   }
 }
 loragotchiDXHome.away=false;loragotchiDXHome.pending=false;loragotchiDXHome.committing=true;
 loragotchiDXHome.destinationKey[0]=1;loragotchiDXHome.destinationKnown=true;
 loRaFishDXDestinationKnown=false;loragotchiDXHome.destinationIndex=0;
 for(auto phase:{LoRaFishVisit::Unconfirmed,LoRaFishVisit::Recall}) {
   loragotchiDXVisit.phase=phase;loRaFishPage=4;
   task.display.clearBounds();drawLoRaFishDX(task.display);
   const std::string expected=phase==LoRaFishVisit::Unconfirmed?"UNCONFIRMED":"RECALLING...";
   assert(std::find(task.display.printed.begin(),task.display.printed.end(),expected)!=task.display.printed.end());
   const auto before=the_mesh.dxSends;task._alert_expiry=0;
   task.handleLongPress(KEY_ENTER);assert(loRaFishPage==LORAFISH_DX_CONTACT_PAGE && the_mesh.dxSends==before);
   task.handleLongPress(KEY_ENTER);assert(the_mesh.lastMessage.find("LFG1|RECALL|")==0);
 }
 puts("PASS aquarium-to-Options Send visitor home, browse versus send, vanished guest guard, status text bounds");
}
''')
with tempfile.TemporaryDirectory(prefix='lrx-menu-') as tmp:
    path=Path(tmp);cpp=path/'menu.cpp';cpp.write_text('\n'.join(parts))
    for sound in (False,True):
        exe=path/('menu'+str(sound));args=['g++','-std=c++17','-I',str(root),'-I',str(root/'src')]
        if sound:args+=['-DPIN_BUZZER=1']
        subprocess.run(args+[str(cpp),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
