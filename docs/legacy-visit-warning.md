# Legacy-compatible visit warning

New visits remain compatible with existing LFG1 peers. Every selected peer gets the same local confirmation, before any REQ is sent:
> Pet may appear differently on older or other habitats.

Cancel is selected by default. Short presses/directional navigation or watch list gestures switch Cancel/Visit; hold/Select activates. Back/double-click or triple-click cancel, and waking the display or leaving the pet screen discards consent. No request, transaction-state save, or home-species change occurs on cancellation. Approval is bound to the selected full public key; if the contact slot resolves to another peer, approval is discarded rather than sent there. Existing sleeping/pending/away/recall guards remain.

The warning is deliberately not inferred from emoji. Name markers are discovery hints only, not proof of peer habitat, protocol capabilities, or stored species. A legacy peer can display a fallback without changing the home pet species. No wire fields, ACK/COMMIT behavior, species storage, discovery allowlists, adoption or breeding negotiation were changed. `hasFish` remains a compatibility alias for the explicitly named `hasDiscoveryMarker`.

Host regressions exercise production handlers (buttons, keyboard directions, L1 routing and watch list stepping), default cancel, explicit approval, no send/save on cancel, wake/alert guards, peer changes, recall and 128x64 text bounds/overlap. These are not physical input, panel or RF validation.
