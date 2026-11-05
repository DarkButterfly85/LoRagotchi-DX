#!/usr/bin/env python3
"""Original Water pixel art, semantic 2-bit masks. Pillow is generation-only.
0 transparent, 1 body/border, 2 scales/fins, 3 eyes/detail. Never stores RGB frames.
Run from any directory; generated header is deterministic.
"""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
W,H=32,24
names=['Blowfish','Shark','Dolphin','Whale','Seal','Shrimp','Squid','Lobster','Crab','Octopus','Jellyfish','Shell-dweller','Sea star','Anglerfish']
def frame(species,phase):
    im=Image.new('L',(W,H)); d=ImageDraw.Draw(im)
    def poly(p,c=1): d.polygon(p,fill=c)
    def line(p,c=2): d.line(p,fill=c)
    def ellipse(b,c=1): d.ellipse(b,fill=c)
    f=phase*2-1
    if species==1:
        poly([(7,11),(2,7+phase),(3,16-phase),(8,14)])
        for x,y in [(10,5),(16,3),(22,5),(26,10),(24,17),(18,21),(11,19),(7,14)]:
            poly([(x-2,y+2),(x,y-3),(x+2,y+2)])
        ellipse((7,5,26,20)); ellipse((10,8,23,17),2)
        for x,y in [(12,10),(17,8),(15,15),(21,14)]:d.point((x,y),1)
        d.point((24,10),3);line([(25,14),(28,14+phase)],3)
    elif species in (2,3):
        poly([(3,12),(0,7+phase),(1,18-phase),(6,14),(11,16),(22,16),(26,13),(31,12),(25,10),(20,9),(17,3 if species==2 else 5),(13,9),(7,10)])
        poly([(14,15),(19,20+phase),(21,15)],2)
        line([(7,14),(24,14)],2); d.point((25,11),3)
        if species==2:
            for x in [22,23]:line([(x,11),(x,13)],3)
            line([(27,13),(30,13)],3)
        else:
            poly([(25,10),(31,10),(30,11),(25,12)])
            line([(28,13),(31,12)],3);d.point((25,10),3)
    elif species==4:
        ellipse((3,6,26,19));poly([(24,12),(31,7+phase),(29,13),(31,19-phase),(24,16)])
        poly([(13,17),(17,22-phase),(20,17)],2)
        line([(5,16),(14,17)],2);line([(4,14),(10,15)],3);d.point((7,11),3)
        if phase:line([(15,5),(14,2),(11,1)],2);line([(14,2),(18,1)],2)
    elif species==5:
        poly([(8,12),(2,7+phase),(4,13),(1,18-phase),(8,16),(14,18),(23,16),(27,13),(29,12),(24,10)])
        ellipse((21,7,28,14));poly([(14,16),(18,21-phase),(20,16)],2)
        d.point((26,9),3);line([(27,12),(31,12)],2);line([(28,13),(30,15)],2)
    elif species==6:
        poly([(7,13),(11,9),(18,8),(23,10),(25,13),(21,15),(17,12),(12,12),(9,15)])
        poly([(7,13),(3,10),(4,15),(8,15)],2)
        for x in [10,14,18,22]:line([(x,12),(x-1+phase,17),(x-3+phase,19)],2)
        for x in [13,17,21]:line([(x,10),(x-1,13)],3)
        line([(24,12),(29,9-phase),(31,9-phase)],2);line([(25,13),(31,13+phase)],2);d.point((23,11),3)
    elif species==7:
        poly([(4,12),(9,6),(20,6),(24,10),(24,16),(20,19),(9,19)])
        poly([(5,12),(1,8+phase),(2,17-phase),(7,14)],2)
        for y in [8,11,14,17]:line([(23,y),(27,y+f),(31,y+f-phase)],2)
        d.point((21,10),3);line([(10,17),(18,17)],2)
    elif species==8:
        poly([(3,12),(1,8),(5,9),(7,11),(19,10),(22,13),(19,16),(7,15),(4,18),(1,17),(3,14)])
        for x in [8,11,14,17]:line([(x,10),(x,16)],3);line([(x,16),(x-2+phase,20)],2)
        for y in [5,19]:
            line([(19,12),(24,y),(27,y)],2);ellipse((25,y-3,31,y+3));poly([(28,y),(31,y-2),(31,y+1)],0)
    elif species==9:
        ellipse((8,10,24,18));line([(12,9),(12,7)],1);line([(20,9),(20,7)],1)
        for x,sign in [(9,-1),(23,1)]:
            line([(x,12),(x+sign*4,7+phase),(x+sign*6,5+phase)],2)
            ellipse((x+sign*6-3,2+phase,x+sign*6+3,8+phase))
            poly([(x+sign*6,4+phase),(x+sign*6+4,2+phase),(x+sign*6+4,6+phase)],0)
        for x,sign in [(10,-1),(22,1)]:
            for y in [14,16,18]:line([(x,y),(x+sign*4,y+2+phase)],2)
        d.point((12,10),3);d.point((20,10),3)
    elif species==10:
        ellipse((10,3,23,16));poly([(11,10),(22,10),(24,17),(8,17)])
        for x in range(6,29,3):
            line([(15+(x-16)//2,14),(x,19-phase),(x+f,21-phase),(x+f*2,20-phase)],2)
        d.point((13,9),3);d.point((20,9),3)
    elif species==11:
        ellipse((7,3+phase,25,18-phase));d.rectangle((6,12,26,19),fill=0)
        poly([(7,11),(10,13-phase),(13,11),(16,13-phase),(19,11),(22,13-phase),(25,11)],2)
        for x in [9,13,17,21,24]:line([(x,13),(x+f,16),(x-f,20),(x,22)],2)
        line([(13,5+phase),(19,5+phase)],2)
    elif species==12:
        ellipse((4,5,22,21));ellipse((7,8,19,18),3);ellipse((9,9,17,16),1);line([(16,10),(12,10),(11,13),(14,14),(16,13)],3)
        poly([(18,17),(26,16),(27,13),(30,13),(30,19),(24,21),(14,21)],2)
        line([(27,14),(26,10+phase)],1);line([(30,14),(31,10-phase)],1)
        d.point((26,10+phase),3);d.point((31,10-phase),3)
    elif species==13:
        poly([(16,2),(19,9),(28,8+phase),(22,14),(25-phase,22),(16,18),(7+phase,22),(10,14),(3,8+phase),(13,9)])
        line([(16,7),(16,15),(10,19)],2);line([(16,15),(22,19)],2);line([(9,11),(16,15),(23,11)],2)
        d.point((14,12),3);d.point((18,12),3)
    elif species==14:
        # Deep-sea lantern silhouette: broad jaw, scalloped fins and a separate
        # arched lure. Two-pixel stalk and 5px bulb survive juvenile sampling.
        poly([(8,13),(2,8+phase*2),(3,13),(1,19-phase*2),(9,17)],2)
        poly([(10,9),(12,5+phase),(17,8),(20,9)],2)
        ellipse((7,8,28,21));poly([(23,11),(28,12),(31,17),(27,21),(18,21)])
        poly([(11,19),(13,23-phase),(19,21),(20,18)],2)
        line([(10,12),(11,10),(14,9)],2)
        # Lure sways without blinking out on either monochrome phase.
        d.line([(17,9),(16,5),(18,2),(22,1),(26-phase,3),(26-phase,5)],fill=1,width=2)
        ellipse((24-phase,4,29-phase,8),1)
        ellipse((25-phase,5,28-phase,7),2)
        d.point((26-phase,5),3)
        ellipse((21,10,25,14),3);d.point((24,12),1)
        # Negative-space grin and small teeth remain readable in one bit.
        poly([(23,16),(29,16),(28,19),(22,18)],3)
        for x in (24,27):d.point((x,16),1)
    return im
out=['#pragma once','#include <stdint.h>','// Generated by tools/water/generate_sprites.py; 14 species x 2 frames x 192 bytes.','namespace LoRaFishWaterArt {','static const uint8_t masks[14][2][192] = {']
for i,name in enumerate(names,1):
    out.append('  { // '+name)
    for p in range(2):
        data=list(frame(i,p).get_flattened_data());packed=[sum(data[j+k]<<(2*k) for k in range(4)) for j in range(0,len(data),4)]
        out.append('    {'+','.join('0x%02x'%v for v in packed)+'},')
    out.append('  },')
out.extend(['};','}'])
(ROOT/'examples/companion_radio/ui-new/LoRaFishWaterArt.h').write_text('\n'.join(out)+'\n')
print('Generated 5376 bytes of 2-bit semantic masks; no RGB framebuffer assets.')
