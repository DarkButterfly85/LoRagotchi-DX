#!/usr/bin/env python3
"""Species-only visitor breeding, using the production gate and breeder.

A guest breeds with the local pet only when its species ID equals the local
species ID. Everything else (other species in the same family, species of the
other family, reserved and unknown IDs) is refused with no egg and no save.
Both editions, both storage branches. RAM file mocks only.
"""
from pathlib import Path
import re,subprocess,tempfile
import check_fish_lifecycle as f

# The refusal must reach the owner through the existing alert mechanism.
breed_case=re.search(r'case LoRaFishOption::Breed:(.*?)break;',f.SOURCE,re.S)
assert breed_case,'Breed menu case not found'
assert re.search(r'if \(breedLoRaFishWithGuest\(\)\) \{.*?showAlert\("Egg saved", 1100\);\s*\} else \{\s*showAlert\("Same species only", 1100\);\s*\}',
                 breed_case.group(1),re.S),'refusal alert missing from Breed case'
print('PASS: refused breeding shows the "Same species only" alert; success still shows "Egg saved"')

code='\n'.join(f.parts[:-1])+f.parts[-1].split('int main() {',1)[0]
code+=r'''
static void guestOf(unsigned species){loragotchiDXGuest.present=true;loragotchiDXGuest.species=species;}
int main() {
  const unsigned lo=LORAGOTCHI_AIR_EDITION ? 256 : 0, hi=LORAGOTCHI_AIR_EDITION ? 274 : 15;
  unsigned bred=0, refused=0;
  for(unsigned local=lo;local<hi;++local) {
    // Exhaustive: every 16-bit guest ID against every local species of this edition.
    for(unsigned guest=0;guest<=65535;++guest) {
      resetAt(5000);randomChoice=1;loRaFishSpecies=local;guestOf(guest);
      const uint8_t scales=loRaFishScaleColor,body=loRaFishColor,eyes=loRaFishEyeColor;
      const bool ok=breedLoRaFishWithGuest();
      if(guest==local) {
        assert(ok && loRaFishPendingEgg && settingsWrites==1);
        assert(loRaFishEggSpecies==local && loRaFishSpecies==local);
        ++bred;
      } else {
        assert(!ok && !loRaFishPendingEgg && settingsWrites==0);
        assert(loRaFishEggSpecies==0 && loRaFishSpecies==local);
        assert(loRaFishScaleColor==scales && loRaFishColor==body && loRaFishEyeColor==eyes);
        ++refused;
      }
    }
  }
  assert(bred==hi-lo && refused==(hi-lo)*65535U);
  pass("same species breeds with an exact egg species; every other guest ID is refused with no egg or save");

  // Named cases for this edition: other family and a different species in-family.
  const unsigned local=LORAGOTCHI_AIR_EDITION ? LoRaFishSpecies::Owl : LoRaFishSpecies::Crab;
  const unsigned sibling=LORAGOTCHI_AIR_EDITION ? LoRaFishSpecies::Parrot : LoRaFishSpecies::ShellDweller;
  const unsigned otherFamily=LORAGOTCHI_AIR_EDITION ? LoRaFishSpecies::Crab : LoRaFishSpecies::Owl;
  const unsigned sameFamilyKinds[]={sibling,otherFamily,LoRaFishSpecies::Eagle,LoRaFishSpecies::TropicalFish};
  for(unsigned guest:sameFamilyKinds) if(guest!=local) {
    resetAt(5000);loRaFishSpecies=local;guestOf(guest);assert(!breedLoRaFishWithGuest() && !loRaFishPendingEgg);
  }
  pass("different species in one family and species of the other family are refused");

  // Colour inheritance and the rest of the lifecycle are unchanged for a same-species pair.
  for(randomChoice=0;randomChoice<=240;randomChoice+=240) {
    resetAt(5000);loRaFishSpecies=local;guestOf(local);
    assert(breedLoRaFishWithGuest() && loRaFishEggSpecies==local && loRaFishPendingEgg);
    if(randomChoice==0) assert(loRaFishEggAppearance.scales==5 && loRaFishEggAppearance.body==4 && loRaFishEggAppearance.eyes==6);
    else assert(loRaFishEggAppearance.scales==3 && loRaFishEggAppearance.body==4 && loRaFishEggAppearance.eyes==5);
    assert(!breedLoRaFishWithGuest() && settingsWrites==1);   // an egg is already pending
    saveLoRaFish();reboot();assert(loRaFishPendingEgg && loRaFishEggSpecies==local && loRaFishGeneration==7);
  }
  pass("same-species colour inheritance, single pending egg and persistence are unchanged");

  // Eligibility is still required: same species does not bypass the other breeding rules.
  resetAt(5000);loRaFishSpecies=local;guestOf(local);loragotchiDXGuest.stage=1;
  assert(!breedLoRaFishWithGuest() && !loRaFishPendingEgg);
  resetAt(LORAFISH_LIFESPAN_MINUTES);loRaFishSpecies=local;guestOf(local);
  assert(!breedLoRaFishWithGuest() && !loRaFishPendingEgg);
  pass("same-species guests still obey the existing eligibility rules");

  // An unknown local ID (retained from a save) never breeds, even with an identical guest ID.
  for(unsigned unknown:{15U,255U,274U,65535U,(unsigned)otherFamily}) {
    resetAt(5000);loRaFishSpecies=unknown;guestOf(unknown);
    assert(!breedLoRaFishWithGuest() && !loRaFishPendingEgg && settingsWrites==0);
  }
  pass("an unknown or other-habitat local ID never breeds, even against an identical guest ID");
}
'''
for edition in ('LORAGOTCHI_WATER_EDITION','LORAGOTCHI_AIR_EDITION'):
    with tempfile.TemporaryDirectory(prefix='species-breeding-') as tmp:
        p=Path(tmp);(p/'test.cpp').write_text(code)
        for platform in ('ESP32','NRF52_PLATFORM'):
            exe=p/platform
            subprocess.run(['g++','-std=c++17','-D'+edition+'=1','-I',str(f.ROOT),'-D'+platform,str(p/'test.cpp'),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
