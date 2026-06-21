"""
Effective damage calculation for Pokémon TCG attacks.

Weakness and resistance come from the typed ``CardData`` dataclasses returned
by ``cg.api.all_card_data()`` (via ``card_db``): ``.weakness``, ``.resistance``
and ``.energyType`` (all ``EnergyType | None``). No hard-coded type chart is
used — the engine's own data drives every check.

Damage formula:
  1. Start with base_damage from the Attack record.
  2. If defender.weakness == attacker.energyType:    damage *= 2
  3. If defender.resistance == attacker.energyType:  damage = max(0, damage - 30)
  4. Clamp to a minimum of 0.
"""

WEAKNESS_MULTIPLIER  = 2
RESISTANCE_REDUCTION = 30


def compute_effective_damage(attacker_card, defender_card, base_damage: int) -> int:
    """Return effective damage after applying weakness and resistance.

    attacker_card / defender_card are CardData instances (or None). If either
    is missing, the base damage is returned unchanged.
    """
    if attacker_card is None or defender_card is None:
        return max(0, base_damage)

    attacker_type = attacker_card.energyType
    damage = base_damage

    if defender_card.weakness is not None and defender_card.weakness == attacker_type:
        damage *= WEAKNESS_MULTIPLIER

    if defender_card.resistance is not None and defender_card.resistance == attacker_type:
        damage = max(0, damage - RESISTANCE_REDUCTION)

    return max(0, damage)


def hits_weakness(attacker_card, defender_card) -> bool:
    """True if the attacker's type matches the defender's weakness."""
    if attacker_card is None or defender_card is None:
        return False
    return (defender_card.weakness is not None
            and defender_card.weakness == attacker_card.energyType)


def hits_resistance(attacker_card, defender_card) -> bool:
    """True if the attacker's type matches the defender's resistance."""
    if attacker_card is None or defender_card is None:
        return False
    return (defender_card.resistance is not None
            and defender_card.resistance == attacker_card.energyType)
