#!/usr/bin/env python3
"""Label/scale exact production PPMs from check_water_rendering.py, not new art.
Usage: uv run --with pillow==12.1.0 python tools/water/preview_anglerfish.py FRAMES/plain OUTPUT
"""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw

p=argparse.ArgumentParser()
p.add_argument('frames',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
sheets=[]
for phase in range(2):
    sheet=Image.new('RGB',(840,420),(235,240,236))
    d=ImageDraw.Draw(sheet)
    d.text((18,12),'ANGLERFISH / Water species 14',(22,42,43))
    d.text((18,30),'Production host framebuffer pixels | two 280 ms phases | not device photographs',(22,42,43))
    for mono in (False,True):
        y=72+int(mono)*170
        d.text((18,y-16),'1-bit monochrome' if mono else 'Inherited RGB565 body / fins + lure / eyes',(22,42,43))
        for stage,label in enumerate(('Fry','Young','Adult','Elder')):
            x=18+stage*205
            filename=f'species-14-stage-{stage}-phase-{phase}'+('-mono' if mono else '')+'.ppm'
            im=Image.open(a.frames/filename).crop((15,6,49,33))
            sheet.paste(im.resize((170,135),Image.Resampling.NEAREST),(x,y))
            d.text((x,y+140),label,(22,42,43))
    sheets.append(sheet)
sheets[0].save(a.output/'water-anglerfish.png')
sheets[0].save(a.output/'water-anglerfish.gif',save_all=True,append_images=sheets[1:],duration=280,loop=0)
print(a.output)
