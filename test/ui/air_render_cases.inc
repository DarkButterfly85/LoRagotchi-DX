// Compiled after exact production renderer/stage/home/travel functions.
int main(int argc,char** argv) {
  unsigned checks=0;
  std::array<unsigned long long,18> signatures={};
  const LoRaFishAppearance appearances[]={{0,4,2},{208,38,145},{6,6,6},{7,7,7},{3,255,0}};
  for(unsigned mode=0;mode<2;++mode)for(unsigned index=0;index<18;++index)
  for(unsigned stage=0;stage<4;++stage)for(unsigned theme=0;theme<2;++theme)
  for(const auto& appearance:appearances) {
    const unsigned species=256+index;
    loRaFishSpecies=species;fish.evolution=stage;home=appearance;
    loRaFishColorDisplay=mode;UIColor::window_bkg=mode?(theme?0xffff:0x0861):theme;
    UIColor::primary_txt=mode?(theme?0:0xef7d):1-theme;
    unsigned long long firstHash=0;
    for(unsigned phase=0;phase<2;++phase) {
      tick=10080+phase*280;
      DisplayDriver r,l,h;
      drawFishSpriteForStage(r,32,20,true,stage,appearance,species);
      drawFishSpriteForStage(l,32,20,false,stage,appearance,species);
      drawHomeFishSprite(h,32,20,true);assert(r.pixels==h.pixels);
      if(species)for(int y=0;y<40;++y)for(int x=1;x<64;++x)assert(r.at(x,y)==l.at(64-x,y));
      LoRaFishTravelAnimation a;a.active=true;a.species=species;a.stage=stage;a.appearance=appearance;
      a.started=tick-500;a.startX=12;a.endX=52;DisplayDriver t;
      assert(loRaFishDrawTravelAnimation(t,a));assert(r.pixels==t.pixels);
      a.started=tick-1000;assert(!loRaFishDrawTravelAnimation(t,a));assert(!a.active);
      if(argc>1 && theme==0 && appearance.body==4) {
        char filename[100];snprintf(filename,sizeof(filename),"/species-%u-stage-%u-phase-%u%s.ppm",species,stage,phase,mode?"":"-mono");
        if(!mode)for(auto& c:r.pixels)c=c?0xffff:0;
        r.ppm(std::string(argv[1])+filename);
      }
      if(!mode && !theme && appearance.body==4) {
        if(phase==0)firstHash=r.hash();
        else if(LoRaFishSpecies::steppedByDistance(species)) {
          // Walkers (Penguin, Flamingo...) step their legs by distance walked, so a standing one holds a frame
          // and a 5 px step must change the leg frame.
          DisplayDriver b;drawFishSpriteForStage(b,37,20,true,stage,appearance,species);
          bool differs=false;
          for(int y=0;y<40;++y)for(int x=1;x<58;++x)if(r.at(x,y)!=b.at(x+5,y))differs=true;
          assert(differs);
        }
        else {if(firstHash==r.hash())fprintf(stderr,"No animation species=%u stage=%u\n",species,stage);assert(firstHash!=r.hash());}
      }
      if(!mode && !theme && appearance.body==4 && stage==2) {
        if(phase==0)signatures[index]=r.hash();
        else if(species && !LoRaFishSpecies::steppedByDistance(species))assert(signatures[index]!=r.hash()); // shape, not movement-only animation
      }
      ++checks;
    }
  }
  for(unsigned a=0;a<18;++a)for(unsigned b=a+1;b<18;++b)assert(signatures[a]!=signatures[b]);
  // Unknown ID must be byte-identical to the legacy fallback; identity stays raw.
  DisplayDriver fallback,unknown;LoRaFishAppearance p={4,2,1};
  drawFishSpriteForStage(fallback,32,20,true,2,p,0);
  drawFishSpriteForStage(unknown,32,20,true,2,p,65535);assert(fallback.pixels==unknown.pixels);
  // Air retains Water art for visitors and old saves, including appended ID14.
  for(unsigned stage=0;stage<4;++stage)for(unsigned phase=0;phase<2;++phase)
  for(bool right:{false,true}) {
    loRaFishColorDisplay=false;UIColor::window_bkg=0;UIColor::primary_txt=1;tick=phase*280;
    DisplayDriver actual,expected;
    drawFishSpriteForStage(actual,32,20,right,stage,{0,4,2},LoRaFishSpecies::Anglerfish);
    LoRaFishWaterSprite::draw(expected,32,20,right,LoRaFishSpecies::Anglerfish,stage,
      uint32_t(tick),uint16_t(1),uint16_t(1),uint16_t(0),uint16_t(0));
    assert(actual.pixels==expected.pixels);++checks;
  }
  // Every allele is presentation-only, all stages and mirror directions.
  loRaFishColorDisplay=true;
  for(unsigned id=256;id<274;++id)for(unsigned allele=0;allele<248;++allele) {
    if(!LoRaFishColour::valid(allele))continue;
    const LoRaFishAppearance genes={uint8_t(allele),uint8_t(allele),uint8_t(allele)};
    const auto original=genes;
    for(unsigned stage=0;stage<4;++stage)for(bool right:{false,true}) {
      DisplayDriver d;drawFishSpriteForStage(d,32,20,right,stage,genes,id);
      assert(!memcmp(&genes,&original,sizeof(genes)));++checks;
    }
  }
  // Complete entry/exit intervals, not just an animation midpoint.
  for(unsigned id=256;id<274;++id)for(unsigned stage=0;stage<4;++stage)
  for(bool entering:{false,true})for(unsigned elapsed=0;elapsed<=1000;elapsed+=25) {
    tick=20000+elapsed;LoRaFishTravelAnimation a;a.active=true;a.species=id;a.stage=stage;
    a.appearance=p;a.started=20000;a.startX=entering?-20:32;a.endX=entering?32:84;
    DisplayDriver actual,expected;bool active=loRaFishDrawTravelAnimation(actual,a);
    if(elapsed==1000)assert(!active && !a.active);
    else {assert(active);int x=a.startX+(int)((a.endX-a.startX)*(elapsed/1000.0f));
      drawFishSpriteForStage(expected,x,20,true,stage,p,id);assert(actual.pixels==expected.pixels);}
    ++checks;
  }
  printf("air_checks %u\n",checks);
}
