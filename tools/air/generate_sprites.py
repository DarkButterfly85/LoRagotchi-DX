#!/usr/bin/env python3
"""Original 32x24 Air semantic masks, not emoji/font/raster imports.
Generation-only Pillow; firmware uses 6912 packed bytes and no framebuffer.
0 transparent, 1 body, 2 wings/markings/beak, 3 contrast eyes/detail.
"""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
NAMES=['Eagle','Bird','Owl','Duck','Swan','Penguin','Parrot','Flamingo','Peacock',
       'Turkey','Rooster','Dove','Bat','Honeybee','Butterfly','Fly','Worm','Bug']
def frame(species,phase):
    im=Image.new('L',(32,24));d=ImageDraw.Draw(im)
    def poly(points,c=1):d.polygon(points,fill=c)
    def line(points,c=2,w=1):d.line(points,fill=c,width=w)
    def oval(box,c=1):d.ellipse(box,fill=c)
    def eye(x,y):d.point((x,y),3)
    def feet(x,y):
        for xx in (x,x+5):line([(xx,y),(xx+phase,y+3),(xx+phase+3,y+3)],2)
    def bird_body():
        oval((9,10,24,19));oval((21,5,28,13));poly([(27,8),(31,10),(27,11)],2)
        poly([(10,13),(3,10+phase),(6,18-phase),(13,17)],2);eye(26,8)
    if species==0: # eagle, broad feathered wings, contrasting hooked head
        oval((11,9,24,16));oval((21,7,27,12),2);eye(25,8)
        poly([(27,9),(31,10),(29,13),(28,11)],2)
        poly([(13,12),(2,2+phase*7),(6,3+phase*8),(8,2+phase*8),(10,5+phase*8),(13,5+phase*7),(21,13)])
        for x in (6,9,12):line([(x,5+phase*7),(x+4,12)],2)
        poly([(12,13),(3,17+phase),(5,21-phase),(16,15)],2)
        line([(19,15),(17,19),(20,19)],2)
    elif species==1: # small bird, long up/down wing and forked tail
        bird_body();poly([(13,13),(10,3+phase*12),(16,6+phase*9),(20,14)],2)
        poly([(9,14),(1,12),(3,16),(1,20),(11,17)])
    elif species==2: # owl face discs, ear tufts and perched talons
        oval((8,4,25,20));poly([(8,8),(8,1),(14,5)]);poly([(19,5),(25,1),(25,8)])
        oval((10,6,17,13),2);oval((17,6,24,13),2);eye(14,9);eye(20,9)
        poly([(16,12),(19,12),(17,15)],3)
        line([(9,13),(7-phase*2,18),(12,19)],2);line([(24,13),(26+phase*2,18),(22,19)],2)
        for x in (14,19):line([(x,19),(x,22),(x+2,22)],2)
    elif species==3: # duck, wide bill, round head, paddle feet
        bird_body();d.rectangle((27,9,31,11),fill=2);oval((22,6,28,12));eye(26,8)
        line([(13,13),(18,12+phase),(22,15)],2);feet(13,18)
    elif species==4: # swan S-neck, swept wings
        oval((5,13,24,20));line([(22,16),(24,12),(22,9),(22,5),(26,3),(29,5)],1,3)
        poly([(28,5),(31,7),(28,8)],2);eye(27,4)
        poly([(9,16),(8,6+phase*4),(13,9+phase*3),(15,7+phase*4),(19,15)],2)
        line([(8,21),(22,21)],2)
    elif species==5: # penguin, upright belly and waddling flippers
        oval((10,2,24,21));oval((13,9,21,19),2);oval((12,4,22,10),2)
        eye(15,6);eye(20,6);poly([(20,8),(27,10),(21,11)],2)
        line([(11,10),(6,14+phase*3),(8,18)],1,2)
        line([(23,10),(27,14-phase*3),(26,18)],1,2)
        poly([(12,20),(9+phase,23),(16,23)],2);poly([(20,20),(19,23),(26-phase,23)],2)
    elif species==6: # parrot crest, curved beak and long pointed tail
        bird_body();poly([(22,5),(21,1),(24,3),(26,1),(27,5)],2)
        oval((27,7,31,12),2);poly([(29,10),(31,11),(28,15)],2);eye(26,7)
        poly([(12,16),(3,23),(10,21),(17,16)],2)
        line([(14,11),(12-phase,17),(19,16)],2)
    elif species==7: # flamingo neck, bent leg and one straight leg
        oval((7,8,22,14));line([(21,10),(23,6),(22,3),(26,2),(28,4)],1,2)
        poly([(27,4),(31,6),(29,8),(27,6)],2);eye(26,3)
        line([(13,13),(13,23),(16,23)],2)
        line([(18,13),(22,16+phase),(17,18+phase)],2)
        line([(9,11),(16,10+phase),(20,12)],2)
    elif species==8: # peacock eye-spotted fan, upright head
        oval((1,1,22,21),2)
        for x,y in [(5,6),(11,4),(17,6),(5,13),(11,11),(17,13)]:
            oval((x-1,y-1,x+2,y+2),1);eye(x,y)
        oval((15,13,26,20));line([(24,16),(25,6),(28,4)],1,3)
        poly([(28,5),(31,7),(28,8)],2);eye(28,5)
        line([(26,3),(25,1),(27,2),(29,1)],2);feet(19,19)
        line([(2,18),(6,18-phase)],1)
    elif species==9: # turkey fan, bare neck, wattle
        poly([(13,16),(1,13),(1,6+phase),(5,2),(8,5),(11,1),(14,5),(18,2),(21,7),(20,14)],2)
        for x in (4,8,12,16):line([(x,6),(14,16)],3)
        oval((10,11,26,20));line([(24,14),(24,7),(28,6)],2,3)
        poly([(28,7),(31,9),(28,10)],2);eye(27,6)
        line([(27,10),(28,13)],3);feet(16,19)
    elif species==10: # rooster comb, curved sweeping tail, spur
        bird_body();poly([(22,6),(21,2),(24,4),(25,1),(27,4),(29,3),(28,7)],2)
        line([(9,14),(6,5),(1,4),(3,10+phase),(4,17)],2,2)
        line([(12,13),(8,6),(4,7),(8,17)],1,2)
        line([(27,12),(27,15)],2);feet(14,18)
        line([(15,20),(12,20-phase)],2)
    elif species==11: # dove, spread fan tail, olive twig
        bird_body();poly([(12,13),(9,2+phase*8),(13,4+phase*8),(16,3+phase*8),(21,14)],2)
        poly([(11,15),(1,14),(2,18),(5,21),(13,17)])
        line([(28,11),(31,14),(30,17)],2);line([(30,14),(28,14)],2)
    elif species==12: # bat membrane scallops, pointed ears
        poly([(16,11),(7,2+phase*6),(1,3+phase*7),(3,15),(6,12),(8,18-phase),(11,14),(15,19),
              (18,14),(23,18-phase),(25,12),(29,15),(31,3+phase*7),(25,2+phase*6)])
        for x,y in [(4,6),(9,8),(26,6),(22,8)]:line([(16,12),(x,y+phase*5)],2)
        oval((13,7,20,19));poly([(13,9),(13,3),(16,7)]);poly([(17,7),(20,3),(20,9)])
        eye(15,10);eye(18,10)
    elif species==13: # honeybee, segmented stripes and clear wings
        oval((7,9,24,19));oval((21,10,28,17));poly([(7,12),(3,15),(7,17)],2)
        for x in (11,16,21):line([(x,10),(x,18)],3,2)
        oval((9,2+phase*3,18,10+phase*3),2);oval((17,2+phase*3,24,10+phase*3),2)
        eye(26,12);line([(24,10),(25,7),(28,6)],2)
        for x in (13,18,23):line([(x,18),(x-2+phase,21)],2)
    elif species==14: # butterfly bilaterally symmetric lobed patterned wings
        oval((2+phase*3,2,15,14),2);oval((17,2,29-phase*3,14),2)
        oval((5+phase*2,12,15,22),1);oval((17,12,26-phase*2,22),1)
        for x in (9+phase,22-phase):oval((x-2,6,x+2,10),3)
        line([(16,5),(16,21)],1,2);line([(15,6),(12,2)],1);line([(17,6),(20,2)],1)
        eye(15,6);eye(17,6)
    elif species==15: # fly, huge eyes, thin veined wings and six legs
        oval((11,8,23,20));oval((20,8,28,16),2);oval((23,9,27,12),3)
        oval((3,2+phase*3,17,10+phase*3),2);oval((13,1+phase*3,25,9+phase*3),2)
        line([(5,6+phase*3),(15,8)],3);line([(17,4+phase*3),(18,8)],3)
        for x in (13,17,21):line([(x,17),(x-3+phase,22)],2)
        line([(26,15),(30,18)],2)
    elif species==16: # worm, continuous long segmented crawl, no wings/feet
        line([(2,17),(6,15+phase*2),(10,17),(14,14+phase*2),(18,16),(22,12+phase),(26,12)],1,4)
        oval((24,8+phase,30,14+phase));eye(28,10+phase)
        for x in (6,10,14,18,22):line([(x,14+((x//4)%2)),(x,18-((x//4)%2))],2)
    elif species==17: # caterpillar-like generic bug, antennae and many feet
        for x in (5,10,15,20):
            oval((x-3,10+phase*(x%2),x+4,18+phase*(x%2)))
            line([(x,17),(x-1+phase,21),(x+2,21)],2)
            d.point((x,13),2)
        oval((22,6,29,16));eye(27,9)
        line([(24,7),(22,3+phase)],2);line([(27,7),(29,3-phase)],2)
    return im
def main():
    out=['#pragma once','#include <stdint.h>',
         '// Generated by tools/air/generate_sprites.py; 18 x 2 x 192 = 6912 bytes.',
         'namespace LoRaFishAirArt {','static const uint8_t masks[18][2][192] = {']
    for i,name in enumerate(NAMES):
        out.append('  { // %d %s'%(256+i,name))
        for phase in range(2):
            data=list(frame(i,phase).get_flattened_data())
            packed=[sum(data[j+k]<<(2*k) for k in range(4)) for j in range(0,len(data),4)]
            out.append('    {'+','.join('0x%02x'%v for v in packed)+'},')
        out.append('  },')
    out+=['};','static_assert(sizeof(masks)==6912,"Air asset budget");','}']
    (ROOT/'examples/companion_radio/ui-new/LoRaFishAirArt.h').write_text('\n'.join(out)+'\n')
    print('PASS generated 6912 bytes, 18 original two-frame semantic masks')

if __name__=='__main__':main()
