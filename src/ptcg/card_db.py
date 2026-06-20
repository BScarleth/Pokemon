"""
Card and attack database loaded from the cabt C library.

Requires the Linux native library (libcg.so) — only available on Kaggle.
On macOS/Windows, all lookups return empty dicts and the rules that depend
on this module fall back to their RandomFallback.

Usage:
    from ptcg import card_db
    card_db.load()                         # call once, e.g. in on_game_start
    card = card_db.get_card(card_id)       # CardData dict
    attack = card_db.get_attack(attack_id) # Attack dict
"""

import ctypes
import json

_cards: dict[int, dict] = {}    # cardId → CardData dict
_attacks: dict[int, dict] = {}  # attackId → Attack dict
_loaded = False


def load() -> bool:
    """Load card and attack data from the C library. Returns True on success."""
    global _cards, _attacks, _loaded
    if _loaded:
        return True
    try:
        from kaggle_environments.envs.cabt.cg.sim import lib
        lib.AllCard.restype  = ctypes.c_char_p
        lib.AllAttack.restype = ctypes.c_char_p
        raw_cards   = lib.AllCard()
        raw_attacks = lib.AllAttack()
        if raw_cards:
            for c in json.loads(raw_cards.decode()):
                _cards[c["cardId"]] = c
        if raw_attacks:
            for a in json.loads(raw_attacks.decode()):
                _attacks[a["attackId"]] = a
        _loaded = True
        return True
    except Exception:
        return False


def get_card(card_id: int) -> dict:
    return _cards.get(card_id, {})


def get_attack(attack_id: int) -> dict:
    return _attacks.get(attack_id, {})


def is_loaded() -> bool:
    return _loaded
