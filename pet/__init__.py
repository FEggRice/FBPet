"""FB Pet (Python) — extensible desktop pet.

Layering (low → high, no cycles):
  animator / key_counter   — pure logic, no GUI, unit-tested
  config                   — dict-backed JSON config, extensible by design
  events                   — publish/subscribe decoupling
  assets / audio           — placeholder generation & playback
  keyboard_hook / tray     — OS integration (own threads, marshal via queue)
  ui                       — tkinter views (pet window / bubble / settings)
  app                      — composition root: wires it all together
"""
