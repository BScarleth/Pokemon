"""
Enum constants and option-identification helpers for the cabt engine.

All values are taken directly from the official API documentation:
https://matsuoinstitute.github.io/cabt/api.html

IntEnum is used so members compare equal to plain integers (the observation
arrives as parsed JSON where all enum fields are plain ints), while still
giving proper repr, iteration, and reverse lookup via e.g. OptionType(13).
"""

from enum import IntEnum


# ── Enums ─────────────────────────────────────────────────────────────────────

class OptionType(IntEnum):
    NUMBER            = 0
    YES               = 1
    NO                = 2
    CARD              = 3
    TOOL_CARD         = 4
    ENERGY_CARD       = 5
    ENERGY            = 6
    PLAY              = 7   # play a card from hand
    ATTACH            = 8   # attach energy or tool
    EVOLVE            = 9   # evolve a Pokémon
    ABILITY           = 10
    DISCARD           = 11
    RETREAT           = 12
    ATTACK            = 13
    END               = 14  # end turn
    SKILL             = 15
    SPECIAL_CONDITION = 16


class SelectType(IntEnum):
    MAIN              = 0   # main phase — mixed option types
    CARD              = 1
    ATTACHED_CARD     = 2
    CARD_OR_ATTACHED  = 3
    ENERGY            = 4
    SKILL             = 5
    ATTACK            = 6
    EVOLVE            = 7
    COUNT             = 8
    YES_NO            = 9
    SPECIAL_CONDITION = 10


class CardType(IntEnum):
    POKEMON           = 0
    ITEM              = 1
    TOOL              = 2
    SUPPORTER         = 3
    STADIUM           = 4
    BASIC_ENERGY      = 5
    SPECIAL_ENERGY    = 6


class EnergyType(IntEnum):
    COLORLESS         = 0
    GRASS             = 1
    FIRE              = 2
    WATER             = 3
    LIGHTNING         = 4
    PSYCHIC           = 5
    FIGHTING          = 6
    DARKNESS          = 7
    METAL             = 8
    DRAGON            = 9
    RAINBOW           = 10
    TEAM_ROCKET       = 11


class AreaType(IntEnum):
    DECK              = 1
    HAND              = 2
    DISCARD           = 3
    ACTIVE            = 4
    BENCH             = 5
    PRIZE             = 6
    STADIUM           = 7
    ENERGY            = 8
    TOOL              = 9
    PRE_EVOLUTION     = 10
    PLAYER            = 11
    LOOKING           = 12


# ── Option type checks ────────────────────────────────────────────────────────
# Each function checks a single option dict (one element of select["option"]).

def is_attack(option: dict) -> bool:
    return option.get("type") == OptionType.ATTACK


def is_retreat(option: dict) -> bool:
    return option.get("type") == OptionType.RETREAT


def is_play(option: dict) -> bool:
    return option.get("type") == OptionType.PLAY


def is_attach(option: dict) -> bool:
    return option.get("type") == OptionType.ATTACH


def is_evolve(option: dict) -> bool:
    return option.get("type") == OptionType.EVOLVE


def is_end_turn(option: dict) -> bool:
    return option.get("type") == OptionType.END


def is_ability(option: dict) -> bool:
    return option.get("type") == OptionType.ABILITY


# ── Select-level helpers ──────────────────────────────────────────────────────
# These check the select object itself (obs["select"]), not individual options.

def get_select_type(obs: dict) -> SelectType:
    return SelectType((obs.get("select") or {}).get("type", SelectType.MAIN))


def energy_already_attached(obs: dict) -> bool:
    return bool((obs.get("current") or {}).get("energyAttached", False))
