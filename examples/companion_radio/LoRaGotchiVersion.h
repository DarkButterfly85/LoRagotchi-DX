#pragma once

#ifndef LORAGOTCHI_WATER_EDITION
#define LORAGOTCHI_WATER_EDITION 0
#endif

#ifndef LORAGOTCHI_AIR_EDITION
#define LORAGOTCHI_AIR_EDITION 0
#endif
#ifndef LORAGOTCHI_LAND_EDITION
#define LORAGOTCHI_LAND_EDITION 0
#endif
#if (LORAGOTCHI_AIR_EDITION + LORAGOTCHI_WATER_EDITION + LORAGOTCHI_LAND_EDITION) > 1
#error Select one habitat edition
#endif
// DX-Pro: one firmware carrying the Water, Air and Land registries together; the owner picks the
// set, then the species, in the menu. It replaces the single-edition flags rather than adding to them.
#ifndef LORAGOTCHI_DXPRO
#define LORAGOTCHI_DXPRO 0
#endif
#if LORAGOTCHI_DXPRO && (LORAGOTCHI_AIR_EDITION || LORAGOTCHI_WATER_EDITION || LORAGOTCHI_LAND_EDITION)
#error LORAGOTCHI_DXPRO already includes every habitat set; do not combine it with an edition flag
#endif
#define LORAGOTCHI_SPECIES_EDITION (LORAGOTCHI_WATER_EDITION || LORAGOTCHI_AIR_EDITION || LORAGOTCHI_LAND_EDITION || LORAGOTCHI_DXPRO)
// Editions whose pets live on the ground or in the air: shared habitat motion model.
#define LORAGOTCHI_ANIMAL_EDITION (LORAGOTCHI_AIR_EDITION || LORAGOTCHI_LAND_EDITION || LORAGOTCHI_DXPRO)
// Which sprite sets and discovery markers a build carries (DX-Pro carries all of them).
#define LORAGOTCHI_HAS_AIR (LORAGOTCHI_AIR_EDITION || LORAGOTCHI_DXPRO)
#define LORAGOTCHI_HAS_LAND (LORAGOTCHI_LAND_EDITION || LORAGOTCHI_DXPRO)

// Product source candidate, separate from MeshCore FIRMWARE_VERSION.
// No GitHub release or hardware acceptance is implied.
#ifndef LORAGOTCHI_PRODUCT_VERSION
#define LORAGOTCHI_PRODUCT_VERSION "v1.1.0"
#endif

#if LORAGOTCHI_DXPRO
#define LORAGOTCHI_EDITION_NAME "DX-PRO"
#elif LORAGOTCHI_LAND_EDITION
#define LORAGOTCHI_EDITION_NAME "LAND"
#elif LORAGOTCHI_AIR_EDITION
#define LORAGOTCHI_EDITION_NAME "AIR"
#elif LORAGOTCHI_WATER_EDITION
#define LORAGOTCHI_EDITION_NAME "WATER"
#else
#define LORAGOTCHI_EDITION_NAME "DX"
#endif
