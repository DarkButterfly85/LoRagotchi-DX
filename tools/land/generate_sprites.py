#!/usr/bin/env python3
"""FIRST-PASS Land semantic masks (32x24, two frames) -- DRAFT ART, NOT FINAL.

Mirrors tools/air/generate_sprites.py: original geometric masks, no emoji/font/raster
imports. Generation-only Pillow; firmware uses 14976 packed bytes and no framebuffer.
0 transparent, 1 body, 2 markings/horns/mane/detail, 3 contrast eyes/nose.
Every sprite faces right (the sprite code mirrors for left-facing pets).
Run:  python3 tools/land/generate_sprites.py                 (writes LoRaFishLandArt.h)
      python3 tools/land/generate_sprites.py --preview out.png   (contact sheet, phase 0)
"""
from pathlib import Path
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
NAMES = ['Dog', 'Cat', 'Horse', 'Cow', 'Elephant', 'Pig', 'Ram', 'Sheep', 'Goat', 'Giraffe',
         'Kangaroo', 'Llama', 'Deer', 'Mouse', 'Hamster', 'Rabbit', 'Hedgehog', 'Koala', 'Panda',
         'Sloth', 'Otter', 'Skunk', 'Badger', 'Hippo', 'Rhino', 'Camel', 'Bactrian camel', 'Bison',
         'Frog', 'Crocodile', 'Lizard', 'Turtle', 'Snake', 'Unicorn', 'Dragon', 'Dragon face',
         'Phoenix', 'Sauropod', 'T-Rex']
BASE_ID = 512
FLASH_BYTES = len(NAMES) * 2 * 192


def frame(species, p):
    im = Image.new('L', (32, 24))
    d = ImageDraw.Draw(im)

    def poly(points, c=1): d.polygon(points, fill=c)
    def line(points, c=2, w=1): d.line(points, fill=c, width=w)
    def oval(box, c=1): d.ellipse(box, fill=c)
    def rect(box, c=1): d.rectangle(box, fill=c)
    def dot(x, y, c=3): d.point((x, y), c)

    def legs(xs, top, bottom, w=2, c=1, hoof=None):
        # Alternating diagonal walk: even legs swing one way, odd the other.
        for k, x in enumerate(xs):
            dx = p if k % 2 == 0 else -p
            line([(x, top), (x + dx, bottom)], c, w)
            if hoof: line([(x + dx, bottom), (x + dx + 1, bottom)], hoof)

    def horse_body(horn=False):
        oval((5, 8, 22, 16))
        poly([(18, 10), (21, 3), (26, 3), (24, 12)])
        poly([(23, 3), (31, 8), (29, 11), (24, 7)])
        line([(21, 3), (17, 9)], 2, 2)
        line([(5, 10), (1, 14 + p), (2, 20)], 2, 2)
        legs([7, 10, 18, 21], 15, 23, 2, 1, 2)
        dot(25, 5)
        if horn: poly([(25, 3), (27, 0), (28, 3)], 2)

    if species == 0:    # Dog: floppy ear, snout, wagging tail
        oval((5, 9, 21, 17)); oval((19, 5, 28, 13)); rect((26, 8, 30, 11)); dot(30, 8)
        poly([(20, 5), (18, 11), (22, 10)], 2); dot(25, 7)
        line([(5, 11), (1, 7 + p * 3)], 1, 2); legs([8, 11, 17, 20], 16, 22)
    elif species == 1:  # Cat: pointed ears, whiskers, curled tail
        oval((6, 11, 21, 18)); oval((19, 6, 27, 13))
        poly([(19, 7), (20, 2), (23, 6)]); poly([(23, 6), (26, 2), (27, 7)])
        dot(22, 9); dot(25, 9); line([(27, 10), (31, 9)], 2); line([(27, 12), (31, 13)], 2)
        line([(6, 14), (2, 11), (2, 5), (4, 3 + p * 2)], 1, 2); legs([8, 11, 17, 20], 17, 22)
    elif species == 2:  # Horse
        horse_body()
    elif species == 3:  # Cow: spots, horns, muzzle
        oval((4, 8, 22, 17)); oval((20, 6, 28, 15)); oval((26, 11, 30, 15), 2)
        line([(21, 6), (20, 3)], 2); line([(26, 6), (27, 3)], 2)
        oval((8, 10, 11, 13), 2); oval((14, 12, 17, 15), 2); dot(24, 8)
        line([(4, 10), (2, 16 - p)], 2); legs([7, 10, 17, 20], 16, 22)
    elif species == 4:  # Elephant: big ear, trunk, tusk
        oval((3, 5, 22, 18)); oval((17, 4, 27, 15)); oval((13, 5, 21, 14), 2)
        line([(26, 10), (29, 14), (28, 19), (30, 21 + p)], 1, 2)
        line([(25, 13), (29, 16)], 2); dot(24, 8)
        legs([7, 11, 17, 21], 17, 22, 3); line([(3, 8), (1, 14)], 2)
    elif species == 5:  # Pig: snout, floppy ear, curly tail
        oval((5, 9, 22, 18)); oval((20, 7, 28, 15)); oval((26, 10, 31, 14), 2)
        dot(28, 11); dot(28, 13); dot(24, 9); poly([(21, 7), (22, 3), (25, 7)], 2)
        line([(5, 11), (2, 10), (3, 7), (1, 8)], 2); legs([8, 11, 17, 20], 17, 22)
    elif species == 6:  # Ram: wool body, big curled horn
        oval((4, 9, 22, 18)); oval((21, 8, 29, 16), 2)
        d.ellipse((17, 3, 25, 11), outline=2, width=2); dot(26, 11); dot(28, 14, 1)
        legs([8, 11, 17, 20], 17, 22, 2, 2)
    elif species == 7:  # Sheep: fluffy cloud body, small dark face
        for b in [(3, 8, 12, 17), (9, 6, 18, 15), (14, 8, 23, 17), (6, 11, 16, 19)]: oval(b)
        oval((21, 9, 28, 16), 2); dot(25, 11); poly([(21, 9), (19, 12), (22, 12)], 2)
        legs([8, 11, 16, 19], 17, 22, 2, 2)
    elif species == 8:  # Goat: horns back, beard
        oval((5, 10, 21, 17)); oval((19, 6, 27, 13)); poly([(27, 9), (31, 12), (27, 13)])
        line([(20, 6), (17, 1)], 2, 1); line([(23, 6), (21, 1)], 2, 1)
        line([(27, 14), (27, 17)], 2); dot(24, 8); line([(5, 11), (3, 9)], 1, 2)
        legs([7, 10, 17, 20], 16, 22)
    elif species == 9:  # Giraffe: long neck, patches, ossicones
        oval((4, 12, 18, 18)); poly([(14, 13), (16, 4), (20, 4), (19, 14)]); oval((16, 0, 25, 5))
        for x, y in [(8, 13), (12, 15), (16, 8), (17, 11)]: oval((x, y, x + 2, y + 2), 2)
        line([(18, 0), (18, -1)], 2); line([(21, 0), (21, -1)], 2); dot(22, 2)
        legs([6, 8, 15, 17], 16, 23); line([(4, 12), (2, 17)], 2)
    elif species == 10:  # Kangaroo: upright, tail, pouch, big feet
        oval((7, 8, 17, 20)); oval((14, 3, 22, 10)); poly([(21, 5), (25, 7), (22, 8)])
        poly([(15, 3), (15, -1), (18, 3)]); poly([(18, 3), (20, -1), (21, 3)])
        poly([(8, 17), (1, 22), (8, 22)]); oval((12, 12, 16, 17), 2)
        line([(16, 12), (20, 13 + p)], 1, 1); rect((9, 20, 16 + p, 22)); dot(19, 6)
    elif species == 11:  # Llama: neck, banana ears, woolly
        oval((5, 10, 19, 18)); poly([(15, 11), (17, 3), (21, 3), (20, 12)]); oval((17, 1, 25, 6))
        line([(18, 1), (17, -1)], 2); line([(21, 1), (22, -1)], 2); oval((8, 11, 15, 16), 2)
        dot(22, 3); legs([7, 9, 15, 17], 17, 23); line([(5, 11), (3, 12)], 1, 2)
    elif species == 12:  # Deer: antlers, spots, white tail
        oval((6, 10, 20, 17)); poly([(17, 10), (20, 4), (23, 4), (22, 12)]); oval((19, 4, 27, 11))
        line([(21, 4), (20, 0)], 2); line([(20, 2), (18, 0)], 2)
        line([(24, 4), (25, 0)], 2); line([(25, 2), (27, 0)], 2)
        for x, y in [(9, 12), (13, 13), (11, 15)]: dot(x, y, 2)
        oval((4, 10, 7, 13), 2); dot(24, 6); dot(27, 8); legs([8, 10, 16, 18], 16, 23)
    elif species == 13:  # Mouse: round ears, long tail
        oval((6, 13, 20, 20)); poly([(18, 12), (27, 15), (18, 20)])
        oval((14, 8, 20, 14), 2); oval((18, 8, 24, 14), 2); dot(21, 15); dot(26, 15)
        line([(6, 18), (1, 17), (1, 13 + p * 2)], 2); legs([9, 17], 19, 22)
    elif species == 14:  # Hamster: chubby, cheek pouches, small ears
        oval((5, 6, 26, 21)); oval((20, 12, 27, 19), 2); oval((17, 3, 22, 8), 2)
        dot(22, 11); line([(8, 8), (16, 7)], 2); legs([9, 19], 20, 22, 3)
    elif species == 15:  # Rabbit: tall ears, fluffy tail
        oval((5, 11, 20, 19)); oval((18, 8, 26, 15))
        oval((19, 0 + p, 22, 9)); oval((22, 1 - p, 25, 9)); line([(20, 2), (20, 8)], 2)
        oval((3, 12, 7, 16), 2); dot(23, 11); dot(26, 12); rect((8, 19, 12, 21), 2)
    elif species == 16:  # Hedgehog: spines on the back, pointed face
        poly([(4, 19), (5, 12), (7, 13), (8, 7), (11, 10), (13, 5), (16, 9), (19, 6), (21, 11),
              (23, 10), (24, 19)], 2)
        poly([(20, 12), (31, 16), (28, 19), (20, 19)]); dot(30, 16); dot(25, 14)
        line([(8, 19), (8 + p, 22)], 1, 2); line([(18, 19), (18 - p, 22)], 1, 2)
    elif species == 17:  # Koala: round face, big fluffy ears, clinging to a branch
        line([(0, 22), (31, 22)], 2, 2); oval((7, 9, 21, 21)); oval((14, 2, 26, 13))
        oval((11, 1, 17, 7), 2); oval((23, 1, 29, 7), 2); oval((18, 7, 23, 11), 3)
        dot(16, 6); dot(25, 6); line([(10, 14), (14, 18 + p)], 2)
    elif species == 18:  # Panda: eye patches, black ears/limbs
        oval((6, 11, 26, 21)); oval((11, 2, 25, 14)); oval((10, 1, 14, 5), 2); oval((22, 1, 26, 5), 2)
        oval((13, 6, 17, 10), 2); oval((19, 6, 23, 10), 2); dot(15, 8); dot(21, 8)
        oval((16, 10, 20, 12), 3); line([(8, 14), (24, 14)], 2, 2); legs([9, 12, 20, 23], 19, 22, 3, 2)
    elif species == 19:  # Sloth: hangs from a branch, long arms, face mask
        line([(0, 2), (31, 2)], 2, 2); oval((7, 9, 24, 19)); oval((21, 10, 29, 17))
        oval((22, 11, 28, 16), 2); dot(24, 13); dot(26, 13)
        line([(11, 10), (9 + p, 3)], 1, 2); line([(19, 10), (22 - p, 3)], 1, 2)
        line([(10, 19), (9, 22)], 2); line([(20, 19), (21, 22)], 2)
    elif species == 20:  # Otter: long sleek body, pale belly, thick tail
        oval((4, 12, 23, 19)); oval((21, 9, 29, 16)); oval((8, 16, 20, 19), 2)
        poly([(4, 15), (0, 18 + p), (3, 21), (7, 18)]); dot(26, 11); dot(29, 12)
        line([(28, 14), (31, 14)], 2); line([(28, 15), (31, 17)], 2); legs([9, 12, 18, 21], 18, 21)
    elif species == 21:  # Skunk: bushy raised tail, white stripe
        poly([(7, 13), (2, 10), (3, 3 + p), (8, 2), (11, 8)]); line([(6, 4), (5, 12)], 2)
        oval((7, 11, 22, 18)); oval((20, 9, 28, 15)); line([(8, 12), (21, 10), (27, 9)], 2)
        dot(25, 11); dot(28, 12); legs([9, 12, 17, 20], 17, 22)
    elif species == 22:  # Badger: low, wedge head with a dark stripe
        oval((5, 11, 23, 19)); poly([(21, 10), (31, 14), (28, 18), (21, 17)], 2)
        line([(21, 11), (30, 14)], 1, 2); dot(26, 13); dot(30, 14)
        line([(7, 14), (21, 14)], 2); legs([8, 12, 18, 22], 18, 22, 2)
    elif species == 23:  # Hippo: huge muzzle, tiny ears, stubby legs
        oval((3, 8, 23, 20)); oval((19, 8, 31, 19)); oval((20, 5, 24, 9), 2)
        dot(29, 10); dot(27, 10); dot(24, 8); line([(21, 16), (31, 16)], 2)
        legs([7, 11, 16, 20], 18, 23, 3)
    elif species == 24:  # Rhino: nose horn, ear, plated shoulder
        oval((3, 8, 22, 18)); poly([(19, 10), (26, 9), (31, 15), (27, 18), (19, 17)])
        poly([(28, 11), (30, 3), (31, 11)], 2); poly([(24, 9), (25, 6), (26, 9)], 2)
        poly([(20, 8), (21, 4), (23, 9)], 2); dot(25, 12); line([(13, 9), (13, 17)], 2)
        legs([7, 11, 16, 20], 17, 22, 3)
    elif species == 25:  # Camel: one hump
        oval((4, 10, 21, 17)); oval((9, 3, 17, 11), 2); line([(19, 12), (22, 8), (24, 4)], 1, 3)
        oval((22, 1, 30, 6)); dot(27, 3); line([(8, 10), (18, 10)], 2); legs([6, 9, 16, 19], 16, 23)
    elif species == 26:  # Bactrian camel: two humps, shaggy neck
        oval((4, 11, 21, 18)); oval((5, 4, 11, 12), 2); oval((12, 4, 18, 12), 2)
        line([(19, 12), (22, 8), (24, 4)], 1, 3); oval((22, 1, 30, 6)); dot(27, 3)
        line([(20, 12), (22, 9)], 2, 1); line([(18, 13), (20, 16)], 2); legs([6, 9, 16, 19], 17, 23)
    elif species == 27:  # Bison: shoulder hump, shaggy beard, horns
        oval((3, 6, 20, 17)); oval((11, 3, 22, 13)); oval((19, 9, 29, 18))
        oval((20, 14, 28, 19), 2); line([(21, 9), (19, 6)], 2, 2); line([(27, 9), (29, 6)], 2, 2)
        dot(25, 12); line([(3, 9), (2, 15)], 2); legs([6, 9, 16, 19], 16, 22)
    elif species == 28:  # Frog: bulging eyes, folded hind leg, throat pulse
        o = -2 * p
        oval((6, 10 + o, 22, 20 + o)); oval((16, 5 + o, 20, 10 + o)); oval((21, 5 + o, 25, 10 + o))
        dot(18, 7 + o); dot(23, 7 + o); line([(18, 16 + o), (27, 16 + o)], 2)
        oval((20, 17 + o, 26, 20 + o), 2); poly([(6, 14 + o), (2, 20), (10, 21)])
        line([(18, 19 + o), (21, 22)], 1, 2)
    elif species == 29:  # Crocodile: long snout with teeth, ridged back, swishing tail
        oval((3, 12, 22, 18)); poly([(20, 12), (31, 13), (31, 16), (20, 17)])
        line([(22, 16), (31, 16)], 2); oval((22, 9, 26, 13)); dot(24, 10)
        poly([(4, 13), (0, 17 + p * 2), (1, 20), (5, 18)])
        for x in (7, 11, 15): line([(x, 12), (x + 1, 10)], 2)
        line([(8, 17), (6, 21 - p)], 1, 2); line([(18, 17), (20, 21)], 1, 2)
    elif species == 30:  # Lizard: slim, long tail, splayed legs, stripes
        oval((8, 13, 22, 18)); poly([(21, 13), (29, 14), (21, 18)]); dot(25, 14)
        line([(9, 16), (4, 18), (1, 16 + p * 2)], 1, 2); line([(10, 14), (21, 14)], 2)
        line([(11, 17), (8, 21 + p)], 1); line([(19, 17), (22, 21 - p)], 1)
        line([(11, 17), (14, 21 - p)], 1); line([(19, 17), (17, 21 + p)], 1)
    elif species == 31:  # Turtle: domed shell with plates, head, flippers
        oval((6, 5, 24, 19)); oval((23, 12, 30, 18)); dot(28, 14)
        line([(9, 9), (21, 9)], 2); line([(8, 13), (22, 13)], 2)
        line([(12, 6), (12, 18)], 2); line([(18, 6), (18, 18)], 2)
        line([(10, 18), (10 + p, 22)], 1, 2); line([(20, 18), (20 - p, 22)], 1, 2)
        poly([(6, 17), (3, 19), (6, 19)])
    elif species == 32:  # Snake: S-curve, raised head, tongue, pattern
        pts = [(1, 20), (5, 17 + p), (9, 20), (13, 22 - p), (17, 19), (21, 15 + p), (23, 11)]
        line(pts, 1, 4); oval((22, 5, 30, 12)); dot(27, 7)
        line([(30, 9), (31, 9)], 2); line([(31, 9), (31, 8)], 2); line([(31, 9), (31, 10)], 2)
        for x, y in [(5, 17 + p), (13, 22 - p), (21, 15 + p)]: dot(x, y, 2)
    elif species == 33:  # Unicorn: horse + spiral horn
        horse_body(True)
    elif species == 34:  # Dragon: wings, tail spikes, horned head
        oval((6, 10, 21, 18)); poly([(18, 11), (21, 5), (25, 4), (24, 12)])
        poly([(23, 4), (30, 7), (28, 10), (23, 8)]); poly([(23, 4), (24, 0), (26, 4)], 2)
        poly([(10, 11), (5, 1 + p * 5), (13, 4 + p * 4), (18, 10)], 2)
        line([(7, 14), (1, 19), (0, 22)], 1, 2)
        for x in (8, 12, 16): poly([(x, 10), (x + 1, 7), (x + 2, 10)], 2)
        dot(26, 6); legs([9, 17], 17, 22, 2, 1)
    elif species == 35:  # Dragon face: frontal head, horns, whiskers, fangs
        oval((7, 4, 25, 21)); poly([(8, 7), (4, 1), (12, 5)], 2); poly([(24, 7), (28, 1), (20, 5)], 2)
        oval((9, 8, 14, 12), 2); oval((18, 8, 23, 12), 2); dot(11, 10); dot(20, 10)
        oval((11, 14, 21, 20), 2); dot(14, 16); dot(18, 16)
        line([(10, 20), (10, 22)], 2); line([(22, 20), (22, 22)], 2)
        line([(7, 14), (2, 12 + p * 2)], 2); line([(25, 14), (30, 12 + p * 2)], 2)
    elif species == 36:  # Phoenix: flame wings and tail, crest
        poly([(14, 12), (6, 2 + p * 6), (10, 1 + p * 6), (13, 4 + p * 6), (17, 3 + p * 6), (22, 12)], 2)
        oval((11, 8, 23, 16)); oval((21, 5, 27, 11)); poly([(26, 7), (31, 9), (26, 10)], 2)
        poly([(22, 5), (21, 1), (24, 3), (26, 0), (26, 5)], 2); dot(25, 7)
        poly([(12, 14), (1, 17), (6, 19), (2, 23), (14, 18)], 2)
        line([(18, 16), (17, 20), (20, 20)], 2)
    elif species == 37:  # Sauropod: very long neck, tail, pillar legs
        oval((4, 11, 20, 19)); poly([(17, 12), (21, 2), (24, 2), (22, 13)]); oval((22, 0, 29, 5))
        poly([(5, 13), (0, 19), (6, 17)]); dot(26, 2)
        for x, y in [(8, 13), (13, 14), (16, 12)]: oval((x, y, x + 2, y + 2), 2)
        legs([7, 10, 16, 19], 17, 23, 3)
    elif species == 38:  # T-Rex: huge head, teeth, tiny arms, thick tail
        poly([(6, 8), (18, 7), (21, 16), (14, 21), (8, 18)]); poly([(17, 3), (30, 5), (30, 10), (22, 10), (17, 9)])
        for x in (23, 25, 27, 29): line([(x, 10), (x, 12)], 2)
        line([(19, 12), (22, 14)], 2); poly([(6, 9), (0, 14), (7, 15)]); dot(23, 6)
        rect((9, 19, 12 + p, 22)); rect((14, 19, 17 - p, 22))
    return im


def pack(im):
    data = list(im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata())
    return [sum(data[j + k] << (2 * k) for k in range(4)) for j in range(0, len(data), 4)]


def preview(path, phase=0):
    cols = 8
    rows = (len(NAMES) + cols - 1) // cols
    scale = 4
    sheet = Image.new('RGB', (cols * 34 * scale, rows * 28 * scale), (20, 24, 30))
    pal = {0: (20, 24, 30), 1: (200, 190, 150), 2: (110, 150, 200), 3: (250, 250, 250)}
    for i in range(len(NAMES)):
        im = frame(i, phase)
        px = Image.new('RGB', (32, 24))
        px.putdata([pal[v] for v in (im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata())])
        px = px.resize((32 * scale, 24 * scale), Image.Resampling.NEAREST)
        sheet.paste(px, ((i % cols) * 34 * scale + scale, (i // cols) * 28 * scale + scale))
    sheet.save(path)


def main():
    if '--preview' in sys.argv:
        preview(sys.argv[sys.argv.index('--preview') + 1]); return
    out = ['#pragma once', '#include <stdint.h>',
           '// Generated by tools/land/generate_sprites.py; %d x 2 x 192 = %d bytes.' % (len(NAMES), FLASH_BYTES),
           '// DRAFT first-pass procedural art: not reviewed on hardware, not final.',
           'namespace LoRaFishLandArt {',
           'static const uint8_t masks[%d][2][192] = {' % len(NAMES)]
    for i, name in enumerate(NAMES):
        out.append('  { // %d %s' % (BASE_ID + i, name))
        for phase in range(2):
            out.append('    {' + ','.join('0x%02x' % v for v in pack(frame(i, phase))) + '},')
        out.append('  },')
    out += ['};', 'static_assert(sizeof(masks)==%d,"Land asset budget");' % FLASH_BYTES, '}']
    (ROOT / 'examples/companion_radio/ui-new/LoRaFishLandArt.h').write_text('\n'.join(out) + '\n')
    print('PASS generated %d bytes, %d two-frame draft semantic masks' % (FLASH_BYTES, len(NAMES)))


if __name__ == '__main__':
    main()
