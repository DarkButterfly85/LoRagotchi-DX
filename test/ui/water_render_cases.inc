// Compiled after exact production renderer/stage/home/travel functions.
int main(int argc,char** argv) {
  unsigned checks=0;
  std::array<unsigned long long,15> signatures={};
  const LoRaFishAppearance appearances[]={{0,4,2},{208,38,145},{6,6,6},{7,7,7},{3,255,0}};
  for(unsigned mode=0;mode<2;++mode)for(unsigned species=0;species<15;++species)
  for(unsigned stage=0;stage<4;++stage)for(unsigned theme=0;theme<2;++theme)
  for(const auto& appearance:appearances) {
    loRaFishSpecies=species;fish.evolution=stage;home=appearance;
    loRaFishColorDisplay=mode;UIColor::window_bkg=mode?(theme?0xffff:0x0861):theme;
    UIColor::primary_txt=mode?(theme?0:0xef7d):1-theme;
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
      if(!mode && !theme && appearance.body==4 && stage==2) {
        if(phase==0)signatures[species]=r.hash();
        else if(species)assert(signatures[species]!=r.hash()); // shape, not movement-only animation
      }
      ++checks;
    }
  }
  for(unsigned a=1;a<15;++a)for(unsigned b=a+1;b<15;++b)assert(signatures[a]!=signatures[b]);
  // The arched stalk and isolated bulb must survive both phases, every age,
  // both monochrome themes and mirroring (not merely a coloured glint).
  for(unsigned theme=0;theme<2;++theme)for(unsigned stage=0;stage<4;++stage) {
    loRaFishColorDisplay=false;UIColor::window_bkg=theme;UIColor::primary_txt=1-theme;
    unsigned long long phaseHash=0;
    for(unsigned phase=0;phase<2;++phase) {
      tick=phase*280;DisplayDriver d;
      drawFishSpriteForStage(d,32,20,true,stage,{0,4,2},LoRaFishSpecies::Anglerfish);
      const unsigned width=stage==0?20:stage==1?26:32,height=stage==0?15:stage==1?19:24;
      bool stalk=false,bulb=false;
      for(unsigned dy=0;dy<height;++dy)for(unsigned dx=0;dx<width;++dx) {
        unsigned sx=dx*32/width,sy=dy*24/height;
        if(d.at(32+int(dx)-int(width)/2,20+int(dy)-int(height)/2)==theme)continue;
        if(sx>=16 && sx<=23 && sy<=3)stalk=true;
        if(sx>=24 && sx<=29 && sy>=4 && sy<=8)bulb=true;
      }
      assert(stalk && bulb);
      if(!phase)phaseHash=d.hash();else assert(phaseHash!=d.hash());
    }
  }
  // Unknown ID must be byte-identical to the legacy fallback; identity stays raw.
  DisplayDriver fallback,unknown;LoRaFishAppearance p={4,2,1};
  drawFishSpriteForStage(fallback,32,20,true,2,p,0);
  drawFishSpriteForStage(unknown,32,20,true,2,p,65535);assert(fallback.pixels==unknown.pixels);
  // Air is intentionally unsupported in Water art, never a mask array index.
  for(unsigned id=256;id<274;++id) {
    DisplayDriver oldFish,airFallback;
    drawFishSpriteForStage(oldFish,32,20,true,2,p,0);
    drawFishSpriteForStage(airFallback,32,20,true,2,p,id);
    assert(oldFish.pixels==airFallback.pixels);
  }
  // Every allele is presentation-only, all stages and mirror directions.
  loRaFishColorDisplay=true;
  for(unsigned id=1;id<15;++id)for(unsigned allele=0;allele<248;++allele) {
    if(!LoRaFishColour::valid(allele))continue;
    const LoRaFishAppearance genes={uint8_t(allele),uint8_t(allele),uint8_t(allele)};
    const auto original=genes;
    for(unsigned stage=0;stage<4;++stage)for(bool right:{false,true}) {
      DisplayDriver d;drawFishSpriteForStage(d,32,20,right,stage,genes,id);
      assert(!memcmp(&genes,&original,sizeof(genes)));++checks;
    }
  }
  // Complete entry/exit intervals, not just an animation midpoint.
  for(unsigned id=1;id<15;++id)for(unsigned stage=0;stage<4;++stage)
  for(bool entering:{false,true})for(unsigned elapsed=0;elapsed<=1000;elapsed+=25) {
    tick=20000+elapsed;LoRaFishTravelAnimation a;a.active=true;a.species=id;a.stage=stage;
    a.appearance=p;a.started=20000;a.startX=entering?-20:32;a.endX=entering?32:84;
    DisplayDriver actual,expected;bool active=loRaFishDrawTravelAnimation(actual,a);
    if(elapsed==1000)assert(!active && !a.active);
    else {assert(active);int x=a.startX+(int)((a.endX-a.startX)*(elapsed/1000.0f));
      drawFishSpriteForStage(expected,x,20,true,stage,p,id);assert(actual.pixels==expected.pixels);}
    ++checks;
  }
  printf("water_checks %u\n",checks);
}
