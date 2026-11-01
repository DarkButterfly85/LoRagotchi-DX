# Repeater tank destinations

Local branch feature/repeater-tank-destinations, based on Water 856d420 in
DrToxic/LoRagotchi-DX. No upstream sync, push, release or flash.

Stock MeshCore repeater adverts must remain ADV_TYPE_REPEATER. The visit picker
now also accepts saved repeaters whose raw name begins with exact "LRX1 " and
contains a supported fish/Water marker. Ordinary fish-marked chat peers are
unchanged. Other repeaters/room nodes are excluded. The name is a discovery hint,
not attestation; the active full public key, capability negotiation, transaction
binding, rich retry metadata, recall and return paths are unchanged.

This small sender patch is required to select the new LoRagotchi-RX stock repeater
tank product through the normal UI. Wire-compatible unmodified senders cannot
select a repeater because their picker filters it out. Keep the source change
separate from RX and Aquarium, and integrate in the actual sending firmware before
hardware acceptance. Do not advertise a forwarding repeater as a fake companion.

Production picker/navigation host tests cover exact marker/type filtering,
existing emoji contacts, aquarium-to-picker entry, filtered row mapping and
identity-bound recalls after rename/reorder/removal. Test helper supplies the
real MeshCore repeater type constant. These are not hardware/RF tests; no new DX
firmware image was built by this focused discovery-only patch.
