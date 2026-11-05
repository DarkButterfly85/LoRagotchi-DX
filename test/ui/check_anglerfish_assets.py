# Banked Water masks must preserve pre-Anglerfish role pixels. No Pillow on CI.
from pathlib import Path
import hashlib
import re
ROOT = Path(__file__).resolve().parents[2]
text = (ROOT/"examples/companion_radio/ui-new/LoRaFishWaterArt.h").read_text()
packed = bytes(int(x,16) for x in re.findall(r"0x([a-f0-9]{2})",text))
assert len(packed) == 5376
# Owner main 4a7b08c: original 13 non-fish masks, 2 frames x 192B.
assert hashlib.sha256(packed[:4992]).hexdigest() == "2327d2118cb1c70ac496419f3fa541fa4ef6aab82a4169ff12bc555746fe5e08"
assert packed[4992:5184] != packed[5184:]
print("PASS original 4992 packed Water bytes unchanged; Anglerfish adds 384B, two distinct frames")
