#!/usr/bin/env python3
"""Colour Air and Land scenes on colour displays; every other pixel unchanged.

Host checks of the production scenery code (functions are sliced out of UITask.cpp and compiled against
a recording display, using the harness of check_scenery_colour.py). Not a hardware or timing test:
nothing here sees a real panel.

* every colour panel (T190, T114, V4 TFT: native; ST7735 and the T-Deck: 64-row logical frame; the
  Cardputer: 240x135) draws a colour sky (Air) and a colour meadow (Land), in the Air / Land builds and
  in DX-Pro when the pet belongs to that set; DX-Pro Water pets still get the colour tank, and the
  T-Deck and Cardputer Water tanks keep their own scenery
* the colour scenes keep the 1-bit layout: every object the 1-bit habitat draws is still drawn, in
  the same place, in the colour build; the scene is painted edge to edge with no bare strip, and
  no grey 1-bit scenery is left in it
* everything else is pixel-identical to the build before this change (test/ui/air_land_colour_before.json,
  recorded from UITask.cpp at the Water colour tank commit): 1-bit OLED, e-ink, colour flag off,
  the T-Deck and Cardputer Water tanks, and the DX / Water / DX-Pro Water colour tank
* no scenery code names a board
"""
import argparse, importlib.util, json, re, struct, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('check_scenery_colour', HERE / 'check_scenery_colour.py')
sc = importlib.util.module_from_spec(spec)
sys.modules['check_scenery_colour'] = sc
spec.loader.exec_module(sc)

BEFORE = HERE / 'air_land_colour_before.json'
WINDOW, GREY = 0x0861, 0x9CF3          # the harness theme: window background, secondary text (1-bit scenery)
SUN, CLOUD, TURF, EARTH, TRUNK = 0xFEA8, 0xF7DF, 0x2B67, 0x59E5, 0x6A66
COLOUR_DISPLAYS = {                     # macro set -> [(display, w, h)] with the colour flag on
    m: [(n, w, h) for n, w, h, c in d if c and not n.endswith('flag_off')]
    for m, d in sc.DISPLAYS.items() if m in sc.COLOUR_SETS + ('tdeck', 'cardputer')
}
# What each edition/species-set draws, per harness scene name (the harness always names the first scene
# 'water'; single-edition builds ignore the species id, DX-Pro follows it).
def scene_of(edition, kind):
    if edition == 'air':
        return 'air'
    if edition == 'land':
        return 'land'
    if edition == 'dxpro':
        return kind
    return 'water'


def affected(key):
    """Air and Land scenes on a colour panel with the colour flag on: the only pixels allowed to change."""
    edition, mset, rest = key.split('.', 2)
    display, kind = rest.split('.')[:2]
    return (mset in sc.COLOUR_SETS + ('tdeck', 'cardputer') and not display.endswith('flag_off')
            and scene_of(edition, kind) in ('air', 'land'))


def frame(path, w, h):
    raw = path.read_bytes()
    assert len(raw) == w * h * 2, path
    px = struct.unpack(f'<{w * h}H', raw)
    return [px[y * w:(y + 1) * w] for y in range(h)]


def sky_palette(src, fn):
    body = sc.block(src, fn)
    m = re.search(r'sky\[\]=\{([^}]*)\}', body)
    return {int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))}


def static_checks(src):
    # Wiring: only inside the colour-scene guard, only for a colour display at run time.
    for habitat, colour in (('drawLoRaFishAirHabitat', 'drawLoRaFishAirColour'),
                            ('drawLoRaFishLandHabitat', 'drawLoRaFishLandColour')):
        body = sc.block(src, f'static void {habitat}(')
        want = ('#if defined(LORAFISH_COLOUR_SCENES)\n'
                f'  if (loRaFishColorDisplay) {{ {colour}(display); return; }}\n#endif')
        assert want in body, habitat
        assert body.index(want) < body.index('display.setColor(UIColor::secondary_txt)'), habitat
    assert '#if defined(LORAFISH_COLOUR_SCENES) && LORAGOTCHI_HAS_AIR\n// Air:' in src
    assert '#if defined(LORAFISH_COLOUR_SCENES) && LORAGOTCHI_HAS_LAND\n// Land:' in src
    assert '#if defined(LORAFISH_COLOUR_SCENES) && (LORAGOTCHI_HAS_AIR || LORAGOTCHI_HAS_LAND)\n// Colour Air and Land' in src
    assert src.count('drawLoRaFishAirColour(display)') == 1 and src.count('drawLoRaFishLandColour(display)') == 1
    # The colour scene owns the trees on every colour panel; the grey ones are skipped only through the flag.
    body = sc.block(src, 'static bool loRaFishColourTank(')
    assert 'return loRaFishColorDisplay;' in body
    # On the T-Deck and Cardputer only the Air / Land trees are replaced; their Water tank keeps its scenery.
    assert '#elif defined(LORAFISH_COLOUR_SCENES)\n  return loRaFishColorDisplay && loRaFishAnimalHome();' in body
    assert ('#if (defined(LORAGOTCHI_RGB565_PANEL) || defined(LORAFISH_CARDPUTER_25D) || '
            'defined(LORAFISH_TDECK_PIXEL_ART)) && \\\n    !defined(LORAFISH_TALL_TANK)\n'
            '#define LORAFISH_COLOUR_SCENES 1\n#endif') in src
    # No scenery code names a board.
    boards = re.compile(r'HELTEC|LILYGO|TDECK|T190|T114|T096|T-?DECK|CARDPUTER|M5|TWATCH|WATCH|\bV[34]\b|RAK|ESP32|NRF|'
                        r'THINKNODE|WIO|XIAO|STATION|TBEAM|ST77|SSD1306|SH110|E213|E290', re.I)
    for fn in ('static void fillLoRaFishColourSky(', 'static void drawLoRaFishColourSun(',
               'static void drawLoRaFishColourTrees(', 'static void drawLoRaFishAirColour(',
               'static void drawLoRaFishLandColour('):
        body = re.sub(r'//[^\n]*', '', sc.block(src, fn))
        body = body[body.index('{'):]
        assert not boards.search(body), (fn, boards.search(body).group(0))


def frame_checks(src, dump):
    air_sky = sky_palette(src, 'static void drawLoRaFishAirColour(')
    land_sky = sky_palette(src, 'static void drawLoRaFishLandColour(')
    n = 0
    seen = {}
    for edition in sc.EDITIONS:
        for mset, displays in COLOUR_DISPLAYS.items():
            base = Path(dump) / f'{edition}-{mset}'
            for display, w, h in displays:
                kinds = ('water', 'air', 'land') if edition == 'dxpro' else ('water',)
                for kind in kinds:
                    scene = scene_of(edition, kind)
                    if scene not in ('air', 'land'):
                        continue
                    sky = air_sky if scene == 'air' else land_sky
                    ref = {}
                    for t in sc.TICKS:
                        col = frame(base / f'{display}.{kind}.{t}.awake.bin', w, h)
                        slp = frame(base / f'{display}.{kind}.{t}.sleep.bin', w, h)
                        mono = frame(base / f'{display}.{kind}.{t}.mono.bin', w, h)
                        tag = (edition, mset, display, scene, t)
                        floor_rule = h - 15
                        # The awake frame also carries the floor rule (drawn by the caller after the scene).
                        assert col[:floor_rule] == slp[:floor_rule] and col[floor_rule + 1:] == slp[floor_rule + 1:], \
                            ('sleeping scene differs from the awake scene', tag)
                        # Fully painted: nothing between the header rule and the floor rule is left bare or grey.
                        for y in range(17, floor_rule):
                            row = col[y]
                            assert WINDOW not in row, ('bare strip', tag, y)
                            assert GREY not in row, ('1-bit grey scenery left in the colour scene', tag, y)
                        assert all(c == GREY for c in col[floor_rule][2:w - 2]), ('floor rule', tag)
                        # The three rows above the floor rule are ground (mist / turf and earth), never sky.
                        for y in range(h - 18, floor_rule):
                            assert not (set(col[y]) & sky), ('sky colour in the ground strip', tag, y)
                        # Header rows are the caller's: the scene never paints them.
                        assert all(c == WINDOW for y in range(0, 17) for c in col[y]), ('header rows touched', tag)
                        # Layout: everything the 1-bit habitat draws above the floor rule is still an object here.
                        for y in range(17, floor_rule):
                            for x in range(w):
                                if mono[y][x] != 0:
                                    assert col[y][x] not in sky, ('1-bit object missing in colour scene', tag, x, y)
                        flat = [c for r in col[17:floor_rule] for c in r]
                        colours = set(flat)
                        assert len(colours) >= 10, ('too flat', tag, len(colours))
                        assert (SUN in colours) and (TURF in colours) == (scene == 'land') \
                            and (EARTH in colours) == (scene == 'land') and (CLOUD in colours) == (scene == 'air'), tag
                        assert (TRUNK in colours) == (mset == 'rgb565_native' and h > 64), ('trees: native panels only', tag)
                        # Sky gradient: the top band and the horizon band differ; they are the scene's own palette.
                        assert col[17][0] in sky and col[17][0] != col[floor_rule - 12][0], ('no sky gradient', tag)
                        ref[t] = col
                        seen.setdefault((mset, display, scene, t), {})[edition] = col
                    drifts = ref[sc.TICKS[0]] != ref[sc.TICKS[-1]]
                    assert drifts == (scene == 'air'), ('clouds drift in Air, Land stands still', edition, mset, display)
                    n += 1
    # DX-Pro draws the scene of the set the pet is in: identical to the single-edition build of that set.
    cmp_n = 0
    for (mset, display, scene, t), by_ed in seen.items():
        if 'dxpro' in by_ed and scene in by_ed:
            assert by_ed['dxpro'] == by_ed[scene], ('DX-Pro scene differs from the', scene, 'build', mset, display, t)
            cmp_n += 1
    assert cmp_n > 0
    # Air and Land are visibly different scenes on every panel.
    for (mset, display, scene, t), by_ed in seen.items():
        if scene == 'air':
            assert by_ed['air'] != seen[(mset, display, 'land', t)]['land'], (mset, display)
    return n, cmp_n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--record-baseline-from', type=Path,
                    help='Maintenance only: record pre-change pixel signatures from an old UITask.cpp')
    args = ap.parse_args()
    if args.record_baseline_from:
        res = sc.run_all(args.record_baseline_from.read_text())
        BEFORE.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
        print('recorded', len(res), 'signatures')
        return
    src = sc.UI.read_text()
    static_checks(src)
    print('PASS wiring: colour Air / Land only behind the colour-scene guard and the run-time colour flag; '
          'no scenery function names a board')
    before = json.loads(BEFORE.read_text())
    with tempfile.TemporaryDirectory(prefix='dx-airland-dump-') as dump:
        now = sc.run_all(src, dump=dump)
        sig = {k: v for k, v in now.items() if k.rsplit('.', 2)[-2] in ('awake', 'sleep')}
        assert set(sig) == set(before), set(sig) ^ set(before)
        same = diff = 0
        for k in sorted(sig):
            if affected(k):
                assert sig[k] != before[k], f'colour Air / Land still draws the old habitat: {k}'
                diff += 1
            else:
                assert sig[k] == before[k], f'pixels changed where they must not: {k}'
                same += 1
        print(f'PASS {same} scene signatures identical to the build before this change '
              '(1-bit OLED, e-ink, colour flag off, the T-Deck and Cardputer Water tanks, and every Water / DX colour tank)')
        print(f'PASS {diff} colour Air / Land scenes differ from the old habitat (T190, T114, V4 TFT, ST7735, T-Deck, Cardputer shapes)')
        n, cmp_n = frame_checks(src, dump)
    print(f'PASS {n} colour Air / Land frames: painted edge to edge, no grey 1-bit scenery, every 1-bit object '
          f'still drawn in place, Air clouds drift and Land stands still; {cmp_n} DX-Pro scenes equal the '
          'single-edition scene of the same set; sleeping equals awake; Air and Land differ')


if __name__ == '__main__':
    main()
