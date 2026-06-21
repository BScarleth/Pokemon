"""
Option-identification helpers for the cabt engine.

Enums are NOT redefined here — they are re-exported from the official
``cg.api`` module (the source of truth shipped with the engine). Import them
from this module or directly from ``cg.api``; both refer to the same objects.

The helper functions operate on the raw option dicts found in
``obs["select"]["option"]`` (the live observation is still a plain dict).
"""

from cg.api import (
    AreaType,
    CardType,
    EnergyType,
    LogType,
    OptionType,
    SelectContext,
    SelectType,
    SpecialConditionType,
)

__all__ = [
    "AreaType", "CardType", "EnergyType", "LogType", "OptionType",
    "SelectContext", "SelectType", "SpecialConditionType",
    "is_attack", "is_retreat", "is_play", "is_attach", "is_evolve",
    "is_end_turn", "is_ability", "get_select_type", "energy_already_attached",
]


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
