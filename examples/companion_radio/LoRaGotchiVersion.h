#pragma once

#ifndef LORAGOTCHI_WATER_EDITION
#define LORAGOTCHI_WATER_EDITION 0
#endif

// Product source candidate, separate from MeshCore FIRMWARE_VERSION.
// No GitHub release or hardware acceptance is implied.
#ifndef LORAGOTCHI_PRODUCT_VERSION
#define LORAGOTCHI_PRODUCT_VERSION "v1.1.0"
#endif

#if LORAGOTCHI_WATER_EDITION
#define LORAGOTCHI_EDITION_NAME "WATER"
#else
#define LORAGOTCHI_EDITION_NAME "DX"
#endif