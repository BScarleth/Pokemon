"""
Target valuation for the planning agent.

``pokemon_score()`` ranks how valuable it is to attack / KO a given opponent
Pokémon. The dominant factor is **prize count** (winning the prize race wins
the game), then invested resources (energy, tools), evolution stage, damage
already taken, and whether the Pokémon is a near-term attacking threat.

Pokémon are the raw observation dicts (board state). Card metadata comes from
``card_db`` (typed ``CardData``).
"""

from ptcg import card_db

# Weights — prize count dominates, then resources, then board quality.
W_PRIZE  = 1000
W_ENERGY = 150
W_TOOL   = 100
W_STAGE2 = 250
W_STAGE1 = 130
W_DAMAGE = 1     # per point of HP already lost
W_THREAT = 200   # Pokémon can already use one of its attacks


def prize_count(pokemon: dict) -> int:
    """Number of prizes the opponent takes when this Pokémon is Knocked Out."""
    data = card_db.get_card(pokemon.get("id", -1))
    if data is None:
        return 1
    if data.megaEx:
        return 3
    if data.ex:
        return 2
    return 1


def is_threat(pokemon: dict) -> bool:
    """True if the Pokémon already has enough energy to use one of its attacks."""
    data = card_db.get_card(pokemon.get("id", -1))
    if data is None:
        return False
    attached = len(pokemon.get("energies", []))
    for attack_id in data.attacks:
        atk = card_db.get_attack(attack_id)
        if atk is not None and len(atk.energies) <= attached:
            return True
    return False


def pokemon_score(pokemon: dict) -> int:
    """Heuristic value of targeting this opponent Pokémon."""
    data = card_db.get_card(pokemon.get("id", -1))

    score = prize_count(pokemon) * W_PRIZE
    score += len(pokemon.get("energies", [])) * W_ENERGY
    score += len(pokemon.get("tools", [])) * W_TOOL

    if data is not None:
        if data.stage2:
            score += W_STAGE2
        elif data.stage1:
            score += W_STAGE1

    damage_taken = max(0, pokemon.get("maxHp", 0) - pokemon.get("hp", 0))
    score += damage_taken * W_DAMAGE

    if is_threat(pokemon):
        score += W_THREAT

    return score
