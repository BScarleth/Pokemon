"""
Effective damage calculation for Pokémon TCG attacks.

Source of truth for weakness and resistance is always the card data returned
by all_card_data() (CardData.weakness, CardData.resistance, CardData.energyType).
No hard-coded type chart is used — the engine's own data drives every check.

Modern PTCG damage formula:
  1. Start with base_damage from the Attack record.
  2. If defender.weakness == attacker.energyType:
         damage *= WEAKNESS_MULTIPLIER   (×2 in current sets)
  3. If defender.resistance == attacker.energyType:
         damage = max(0, damage - RESISTANCE_REDUCTION)   (-30 in current sets)
  4. Clamp: damage = max(0, damage)

Both weakness and resistance values in CardData are EnergyType integers and
may be None when the Pokémon has no weakness or resistance of that kind.
"""

WEAKNESS_MULTIPLIER   = 2
RESISTANCE_REDUCTION  = 30


def compute_effective_damage(
    attacker_card: dict,
    defender_card: dict,
    base_damage: int,
) -> int:
    """Return effective damage after applying weakness and resistance."""
    attacker_type = attacker_card.get("energyType")
    weakness      = defender_card.get("weakness")
    resistance    = defender_card.get("resistance")

    damage = base_damage

    if weakness is not None and weakness == attacker_type:
        damage *= WEAKNESS_MULTIPLIER

    if resistance is not None and resistance == attacker_type:
        damage = max(0, damage - RESISTANCE_REDUCTION)

    return max(0, damage)


def hits_weakness(attacker_card: dict, defender_card: dict) -> bool:
    """True if the attacker's type matches the defender's weakness."""
    attacker_type = attacker_card.get("energyType")
    weakness      = defender_card.get("weakness")
    return weakness is not None and weakness == attacker_type


def hits_resistance(attacker_card: dict, defender_card: dict) -> bool:
    """True if the attacker's type matches the defender's resistance."""
    attacker_type = attacker_card.get("energyType")
    resistance    = defender_card.get("resistance")
    return resistance is not None and resistance == attacker_type
