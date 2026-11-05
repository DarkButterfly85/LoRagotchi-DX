#!/usr/bin/env python3
"""Make a labelled sheet/GIF from production framebuffer PPMs, never concept art."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('frames',type=Path);p.add_argument('output',type=Path);p.add_argument('--mono',action='store_true');a=p.parse_args()
names=['Tropical fish','Blowfish','Shark','Dolphin','Whale','Seal','Shrimp','Squid','Lobster','Crab','Octopus','Jellyfish','Shell-dweller','Sea star','Anglerfish']
a.output.mkdir(parents=True,exist_ok=True)
sheets=[]
for phase in range(2):
    sheet=Image.new('RGB',(800,70+4*150),(239,241,235));d=ImageDraw.Draw(sheet)
    d.text((14,12),'LoRagotchi Water / production host-rendered sprites',(20,34,38))
    d.text((14,30),'15 species; adult frame; not device photographs. '+('1-bit OLED fallback.' if a.mono else 'Runtime inherited RGB565 colours.'),(20,34,38))
    for id,label in enumerate(names):
        x=10+(id%4)*197;y=62+(id//4)*150
        d.text((x,y),f'{id}: {label}',(20,34,38))
        im=Image.open(a.frames/(f'species-{id}-stage-2-phase-{phase}'+('-mono' if a.mono else '')+'.ppm')).crop((15,6,49,33))
        sheet.paste(im.resize((170,135),Image.Resampling.NEAREST),(x,y+14))
    sheets.append(sheet)
sheets[0].save(a.output/('water-production-oled.png' if a.mono else 'water-production-catalogue.png'))
sheets[0].save(a.output/('water-production-oled-animation.gif' if a.mono else 'water-production-animation.gif'),save_all=True,append_images=sheets[1:],duration=280,loop=0)
print(a.output)
