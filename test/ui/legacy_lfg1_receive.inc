// Verbatim receive body: owner fork f310240 MyMesh.cpp queueMessage LORAFISH_UI.
void MyMesh::receive(const ContactInfo& from,const char* text){
  if (text && strncmp(text,"LEG1|",5)==0) {
    char reply[80]={};
    if (loragotchiEggMessage(from.id.pub_key,text,reply,sizeof(reply)) && reply[0]) {
      uint32_t hash=0,timeout=0;
      sendMessage(from,getRTCClock()->getCurrentTime(),0,reply,hash,timeout);
    }
    return;
  }
  if (text && strncmp(text,"LFG1|",5)==0) {
    expireLoRaFishReservation();
    unsigned long tx=0,fid=0;
    Serial.printf("[LFG1 PEER] RX from='%s' text=%s\n",from.name,text);

    const bool fromDestination=loragotchiDXHome.destinationKnown &&
        !memcmp(loragotchiDXHome.destinationKey,from.id.pub_key,32);
    if (strncmp(text,"LFG1|REQ|",9)==0) {
      unsigned st=2; char nm[24]="DX Fish";
      int n=sscanf(text+9,"%lu|%lu|%u|%23[^\n]",&tx,&fid,&st,nm);
      if(n>=3) {
        const bool sameTx=(loragotchiDXGuest.txid==tx && loragotchiDXGuest.fishid==fid &&
            loragotchiDXGuest.ownerKnown && !memcmp(from.id.pub_key,loragotchiDXGuest.ownerKey,32));
        char reply[80];
        if(sameTx && (loragotchiDXReservation.expired || loragotchiDXGuestReturn.status!=LoRaFishGuestReturn::Idle)) {
          if (!loragotchiDXReservation.expired && loragotchiDXGuestReturn.status != LoRaFishGuestReturn::Confirmed) return;
          snprintf(reply,sizeof(reply),"LFG1|RETURN|%lu|%lu|%c%s",tx,fid,loragotchiDXLocalColorCapable?'C':'M',
              loragotchiDXReservation.expired ? "|CANCEL1" : "");
          uint32_t hash=0,timeout=0;sendMessage(from,getRTCClock()->getCurrentTime(),0,reply,hash,timeout);
          return;
        }
        if((!loragotchiDXGuest.present && !loragotchiDXGuest.reserved) || sameTx) {
          if(!sameTx) {
            loragotchiDXGuest=LoRaGotchiDXGuestState{};
            loragotchiDXGuestReturn=LoRaFishGuestReturn{};
            loRaFishArrival=LoRaFishArrival{};
            memcpy(loragotchiDXGuest.ownerKey,from.id.pub_key,32);loragotchiDXGuest.ownerKnown=true;
            loragotchiDXGuest.txid=tx; loragotchiDXGuest.fishid=fid;
            loragotchiDXGuest.stage=(uint8_t)st;
            strncpy(loragotchiDXGuest.guestName,nm,sizeof(loragotchiDXGuest.guestName)-1);
            loragotchiDXGuest.guestName[sizeof(loragotchiDXGuest.guestName)-1]=0;
            strncpy(loragotchiDXGuest.homeName,from.name,sizeof(loragotchiDXGuest.homeName)-1);
            loragotchiDXGuest.homeName[sizeof(loragotchiDXGuest.homeName)-1]=0;
            loragotchiDXGuest.reserved=true;
            loragotchiDXReservation.start(millis());
            loragotchiDXSave();
          }
          snprintf(reply,sizeof(reply),"LFG1|ACK|%lu|%lu",tx,fid);
        } else {
          snprintf(reply,sizeof(reply),"LFG1|BUSY|%lu|%lu",tx,fid);
        }
        uint32_t ack=0,to=0;
        int r=sendMessage(from,getRTCClock()->getCurrentTime(),0,reply,ack,to);
        Serial.printf("[LFG1 PEER] %s TX result=%d\n", sameTx || (!loragotchiDXGuest.present && loragotchiDXGuest.reserved) ? "ACK" : "BUSY",r);
      }
    } else if (strncmp(text,"LFG1|ACK|",9)==0 && fromDestination &&
        sscanf(text+9,"%lu|%lu",&tx,&fid)==2 &&
        loragotchiDXHome.pending && !loragotchiDXVisit.exhausted(millis()) &&
        loragotchiDXVisit.phase!=LoRaFishVisit::Commit &&
        tx==loragotchiDXHome.txid && fid==loragotchiDXHome.fishid) {
      loRaFishCommitFrame.prepare(from.id.pub_key, tx, fid,
        loragotchiDXLocalHasColorGenes, loragotchiDXLocalColorIndex,
        loragotchiDXLocalScalesColorIndex, loragotchiDXLocalEyesColorIndex,
        loragotchiDXLocalMonoPixelTint, loragotchiDXLocalMonoPanel);
      // Duplicate acceptance cannot reset the retry budget or appearance.
      loragotchiDXVisit.begin(LoRaFishVisit::Commit, millis());
      int r=sendLoRaFishCommit(from);
      Serial.printf("[LFG1 PEER] COMMIT TX result=%d; waiting for ARRIVED\n",r);
    } else if (strncmp(text,"LFG1|ARRIVED|",13)==0 && fromDestination &&
               sscanf(text+13,"%lu|%lu",&tx,&fid)==2 &&
               loragotchiDXHome.committing && tx==loragotchiDXHome.txid && fid==loragotchiDXHome.fishid) {
      loragotchiDXHome.pending=false;
      loragotchiDXHome.committing=false;
      loragotchiDXHome.away=true;
      // A user recall already in flight must continue despite late ARRIVED.
      if (loragotchiDXVisit.phase != LoRaFishVisit::Recall) loragotchiDXVisit.stop();
      loragotchiDXHome.returned=false;
      strncpy(loragotchiDXHome.destinationName,from.name,sizeof(loragotchiDXHome.destinationName)-1);
      loragotchiDXHome.destinationName[sizeof(loragotchiDXHome.destinationName)-1]=0;
      loragotchiDXSave();
      Serial.println("*** DX FISH CONFIRMED ARRIVED ***");
    } else if (strncmp(text,"LFG1|COMMIT|",12)==0 &&
           sscanf(text+12,"%lu|%lu",&tx,&fid)==2) {
      if((loragotchiDXGuest.reserved || loragotchiDXGuest.present || loragotchiDXReservation.expired ||
          loragotchiDXGuestReturn.status != LoRaFishGuestReturn::Idle) &&
         tx==loragotchiDXGuest.txid && fid==loragotchiDXGuest.fishid &&
         loragotchiDXGuest.ownerKnown && !memcmp(loragotchiDXGuest.ownerKey,from.id.pub_key,32)) {
        // Keep the completed transaction as a tombstone until a new visit.
        // A late COMMIT must replay RETURN, never resurrect the guest.
        if(loragotchiDXReservation.expired || loragotchiDXGuestReturn.status!=LoRaFishGuestReturn::Idle) {
          if (!loragotchiDXReservation.expired && loragotchiDXGuestReturn.status != LoRaFishGuestReturn::Confirmed) return;
          char returned[80];snprintf(returned,sizeof(returned),"LFG1|RETURN|%lu|%lu|%c%s",tx,fid,loragotchiDXLocalColorCapable?'C':'M',
              loragotchiDXReservation.expired ? "|CANCEL1" : "");
          uint32_t hash=0,timeout=0;sendMessage(from,getRTCClock()->getCurrentTime(),0,returned,hash,timeout);return;
        }
        char colorMode='M'; unsigned bodyColor=0,scalesColor=0,eyesColor=0,monoPixelTint=0xFFFF;
        const int fields=sscanf(text+12,"%lu|%lu|%c|%u|%u|%u|%u",
            &tx,&fid,&colorMode,&bodyColor,&scalesColor,&eyesColor,&monoPixelTint);
        if (fields>=7 || !loragotchiDXGuest.present) {
          uint8_t hueBody=0, hueScales=0, hueEyes=0;
          const bool hasHues=fields>=7 && LoRaFishColour::extension(
              strstr(text,"|H1|"),hueBody,hueScales,hueEyes);
          loragotchiDXGuest.colorCapable=(fields>=4 && colorMode=='C');
          loragotchiDXGuest.color=(fields>=4 && bodyColor<=6) ? (uint8_t)bodyColor : 6;
          loragotchiDXGuest.scalesColor=(fields>=5 && scalesColor<=6) ? (uint8_t)scalesColor : loragotchiDXGuest.color;
          loragotchiDXGuest.eyesColor=(fields>=6 && eyesColor<=6) ? (uint8_t)eyesColor : loragotchiDXGuest.color;
          loragotchiDXGuest.monoPixelTint=(fields>=7 && monoPixelTint<=0xFFFF) ? (uint16_t)monoPixelTint : 0xFFFF;
          const char* panel=strstr(text, "|P1|"); unsigned panelValue=0;
          if (panel && sscanf(panel, "|P1|%u", &panelValue)==1 && panelValue < 3)
            loragotchiDXGuest.monoPanel=(uint8_t)panelValue;
          else loragotchiDXGuest.monoPanel=0;
          if (hasHues) {
            loragotchiDXGuest.color=hueBody; loragotchiDXGuest.scalesColor=hueScales;
            loragotchiDXGuest.eyesColor=hueEyes;
          }
        }
        const bool firstArrival = !loragotchiDXGuest.present;
        loragotchiDXGuest.reserved=false;
        loragotchiDXGuest.present=true;
        loragotchiDXSave();
        if(firstArrival)
          Serial.printf("*** DX FISH ARRIVED: %s from %s ***\n",loragotchiDXGuest.guestName,loragotchiDXGuest.homeName);
        else
          Serial.println("[LFG1 PEER] duplicate COMMIT; confirmation budget unchanged");

        // One bounded confirmation job per visit. Duplicate COMMITs cannot
        // restart its budget or bypass pacing, including after ACK/exhaustion.
        if (!loRaFishArrival.matches(from.id.pub_key, tx, fid))
          loRaFishArrival.start(from.id.pub_key, tx, fid, millis());
        serviceLoRaFishArrival();
      }
    } else if (strncmp(text,"LFG1|BUSY|",10)==0 && fromDestination && loragotchiDXHome.pending &&
        loragotchiDXVisit.phase!=LoRaFishVisit::Commit &&
        sscanf(text+10,"%lu|%lu",&tx,&fid)==2 && tx==loragotchiDXHome.txid && fid==loragotchiDXHome.fishid) {
      loragotchiDXHome.pending=false; loragotchiDXHome.committing=false; loragotchiDXHome.away=false; loragotchiDXSave();
      loragotchiDXVisit.stop();
      Serial.println("[LFG1 PEER] destination busy");
    } else if (strncmp(text,"LFG1|RECALL|",12)==0 &&
               sscanf(text+12,"%lu|%lu",&tx,&fid)==2) {
      if(tx==loragotchiDXGuest.txid && fid==loragotchiDXGuest.fishid &&
          loragotchiDXGuest.ownerKnown && !memcmp(loragotchiDXGuest.ownerKey,from.id.pub_key,32)) {
        if(loragotchiDXGuest.reserved) {
          loragotchiDXReservation.due=millis();expireLoRaFishReservation();
        }
        if(loragotchiDXGuest.present) returnLoRaFishGuest();
        else {
          char reply[80];snprintf(reply,sizeof(reply),"LFG1|RETURN|%lu|%lu|%c%s",tx,fid,
              loragotchiDXLocalColorCapable?'C':'M',loragotchiDXReservation.expired ? "|CANCEL1" : "");
          uint32_t ack=0,to=0;sendMessage(from,getRTCClock()->getCurrentTime(),0,reply,ack,to);
        }
      }
    } else if (strncmp(text,"LFG1|RETURN|",12)==0 && fromDestination &&
               (loragotchiDXHome.pending || loragotchiDXHome.committing || loragotchiDXHome.away) &&
               sscanf(text+12,"%lu|%lu",&tx,&fid)==2 &&
               tx==loragotchiDXHome.txid && fid==loragotchiDXHome.fishid) {
      char returnMode=0;
      const bool hasReturnMode=sscanf(text+12,"%lu|%lu|%c",&tx,&fid,&returnMode)==3;
      char cancelled[80];
      snprintf(cancelled,sizeof(cancelled),"LFG1|RETURN|%lu|%lu|%c|CANCEL1",tx,fid,returnMode);
      const bool cancelledReservation=hasReturnMode && strcmp(text,cancelled)==0;
      loragotchiDXReturnedFromMonochrome=!cancelledReservation && hasReturnMode && returnMode=='M';
      loragotchiDXHome.completedVisit = !cancelledReservation &&
          (loragotchiDXHome.committing || loragotchiDXHome.away);
      // Opt-in, backwards-compatible capability claim from the actual visit
      // destination, not inferred from its mutable display name or fish emoji.
      char communityReturn[80];
      snprintf(communityReturn,sizeof(communityReturn),"LFG1|RETURN|%lu|%lu|C|AQUARIUM1",tx,fid);
      loragotchiDXHome.communityVisit = loragotchiDXHome.completedVisit &&
          strcmp(text,communityReturn) == 0;
      loragotchiDXHome.pending=false; loragotchiDXHome.committing=false; loragotchiDXHome.away=false; loragotchiDXHome.returned=true; loragotchiDXSave();
      loragotchiDXVisit.stop();
      Serial.println("*** DX FISH RETURNED HOME ***");
    }
    return;
  }
}
