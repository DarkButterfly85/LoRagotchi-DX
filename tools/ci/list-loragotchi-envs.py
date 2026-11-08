#!/usr/bin/env python3
"""Print the LoRaGotchi firmware envs that CI and releases build, as a JSON array.

Selects picker envs (those PlatformIO loads from platformio.ini and variants/*)
whose name contains "loragotchi" or "dx" (case-insensitive), plus the water_
and air_ edition envs. native* unit-test envs are excluded, and envs from
platformio-meshcore.ini are never loaded, so they can never be selected.
"""
import json
import re
import subprocess
import sys

KEEP = re.compile(r"loragotchi|dx|^(water|air)_", re.IGNORECASE)


def main() -> int:
    out = subprocess.run(
        ["pio", "project", "config", "--json-output"],
        check=True, capture_output=True, text=True,
    ).stdout
    envs = [
        section[4:]
        for section, _options in json.loads(out)
        if section.startswith("env:")
    ]
    selected = [e for e in envs if not e.startswith("native") and KEEP.search(e)]
    if not selected:
        print("no LoRaGotchi envs found", file=sys.stderr)
        return 1
    print(json.dumps(selected, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
