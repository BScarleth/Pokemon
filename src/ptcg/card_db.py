"""
Typed card and attack lookup, backed by the official ``cg.api`` helpers.

``cg.api.all_card_data()`` and ``cg.api.all_attack()`` return fully typed
``CardData`` / ``Attack`` dataclasses (see ``cg/api.py``). This module loads
them once and exposes id-keyed lookups.

Requires the native library (``libcg.so``) — available on Kaggle/Linux only.
``cg.api`` is imported lazily inside ``load()`` so this module stays importable
on any platform; on non-Linux, ``load()`` returns False and lookups return
None, and rules that need card data fall through to RandomFallback.

Usage:
    from ptcg import card_db
    card_db.load()                          # call once, e.g. in on_game_start
    card   = card_db.get_card(card_id)      # CardData | None
    attack = card_db.get_attack(attack_id)  # Attack | None
"""

_cards: dict = {}     # cardId   → CardData
_attacks: dict = {}   # attackId → Attack
_loaded = False


def load() -> bool:
    """Load all card and attack data. Returns True on success (idempotent)."""
    global _loaded
    if _loaded:
        return True
    try:
        # Lazy import: triggers loading libcg.so, which only succeeds on Linux.
        from cg.api import all_card_data, all_attack
        _cards.update({c.cardId: c for c in all_card_data()})
        _attacks.update({a.attackId: a for a in all_attack()})
        _loaded = True
        return True
    except Exception:
        return False


def get_card(card_id: int):
    """Return the CardData for a card id, or None if unknown / not loaded."""
    return _cards.get(card_id)


def get_attack(attack_id: int):
    """Return the Attack for an attack id, or None if unknown / not loaded."""
    return _attacks.get(attack_id)


def is_loaded() -> bool:
    return _loaded
