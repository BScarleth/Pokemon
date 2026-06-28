"""
Turn-level attack planning.

Instead of choosing each action independently, the planning agent evaluates
*all* legal attacker × target combinations once at the start of a turn and
commits to a single ``AttackPlan``. Every later action that turn (attach energy,
switch, Boss Orders, attack) is judged by how well it serves that plan.

Indices:
  - Attacker / target indices are into the "cards" list ``[active, *bench]``,
    so index 0 is always the Active Pokémon and 1.. are the Bench.

Card metadata and attack data come from ``card_db``; weakness / resistance are
applied via ``rules.damage`` (no hard-coded type chart).
"""

from dataclasses import dataclass

from ptcg import card_db
from ptcg import observation as obs_utils
from ptcg.rules import damage
from ptcg.planning.pokemon_score import pokemon_score, prize_count

# Score awarded to a KO that wins the game outright (takes the last prize).
WIN_SCORE = 1_000_000
# Penalties for plans that need extra setup before the attack can happen.
SWITCH_PENALTY = 220   # attacker is on the bench (needs a switch/retreat first)
BOSS_PENALTY   = 300   # target is on the bench (needs Boss Orders / gust first)


@dataclass
class AttackPlan:
    best_attacker: int = -1              # index into [active, *bench]; 0 = active
    best_target: int = -1                # index into [active, *bench]; 0 = active
    best_attacker_serial: int = -1       # stable id of the attacker (survives switches)
    best_target_serial: int = -1         # stable id of the target
    attack_id: int = -1                  # chosen attack's id
    should_switch_or_use_boss: bool = False
    expected_effective_damage: int = 0
    expected_prizes: int = 0
    required_energy: int = 0
    can_take_ko: bool = False
    score: int = -1                      # internal ranking score of this plan

    @property
    def valid(self) -> bool:
        return self.best_attacker >= 0 and self.best_target >= 0 and self.attack_id >= 0


def _cards(active, bench) -> list:
    """Return [active, *bench] with the active at index 0 (may be None)."""
    return [active] + list(bench)


def _attacks_for(pokemon: dict) -> list:
    """Return the Attack objects available to a Pokémon (may be empty)."""
    data = card_db.get_card(pokemon.get("id", -1))
    if data is None:
        return []
    return [a for a in (card_db.get_attack(aid) for aid in data.attacks) if a is not None]


def build_attack_plan(
    obs: dict,
    can_switch: bool,
    can_boss: bool,
    energy_attachable: bool,
) -> AttackPlan:
    """
    Evaluate every attacker × attack × target combination and return the best
    ``AttackPlan``. Returns an invalid (empty) plan when no attack is possible.

    Args:
        obs: raw observation dict (board state).
        can_switch: a bench attacker could be brought active this turn.
        can_boss: an opponent's bench Pokémon could be dragged active (Boss/gust).
        energy_attachable: we can still attach one more energy this turn.
    """
    if not card_db.is_loaded():
        return AttackPlan()

    my_cards  = _cards(obs_utils.my_active(obs), obs_utils.my_bench(obs))
    opp_cards = _cards(obs_utils.opponent_active(obs), obs_utils.opponent_bench(obs))
    opp_prizes_left = len(obs_utils.opponent_prize_cards(obs))

    best = AttackPlan()

    for ai, attacker in enumerate(my_cards):
        if attacker is None:
            continue
        # Bench attackers are only reachable if we can switch this turn.
        if ai != 0 and not can_switch:
            continue

        attacker_card = card_db.get_card(attacker.get("id", -1))
        if attacker_card is None:
            continue
        attached = len(attacker.get("energies", []))
        # One extra energy may be attached this turn if we still have our drop.
        reachable_energy = attached + (1 if energy_attachable else 0)

        for atk in _attacks_for(attacker):
            required = len(atk.energies)
            if required > reachable_energy:
                continue

            for ti, target in enumerate(opp_cards):
                if target is None:
                    continue
                # Bench targets require a Boss-Orders style effect.
                if ti != 0 and not can_boss:
                    continue

                target_card = card_db.get_card(target.get("id", -1))
                effective = damage.compute_effective_damage(attacker_card, target_card, atk.damage)
                target_hp = target.get("hp", 0)
                kos = effective >= target_hp

                score = pokemon_score(target)
                if kos:
                    score += prize_count(target) * 1000
                else:
                    # Partial damage is worth a fraction of the target's value.
                    score = int(score * (effective / target_hp)) if target_hp else 0

                # Winning the game (taking the last prize) dominates everything.
                if kos and opp_prizes_left <= prize_count(target):
                    score += WIN_SCORE

                # Prefer plans that need no extra setup.
                if ai != 0:
                    score -= SWITCH_PENALTY
                if ti != 0:
                    score -= BOSS_PENALTY

                if score > best.score:
                    best = AttackPlan(
                        best_attacker=ai,
                        best_target=ti,
                        best_attacker_serial=attacker.get("serial", -1),
                        best_target_serial=target.get("serial", -1),
                        attack_id=atk.attackId,
                        should_switch_or_use_boss=(ai != 0 or ti != 0),
                        expected_effective_damage=effective,
                        expected_prizes=(prize_count(target) if kos else 0),
                        required_energy=required,
                        can_take_ko=kos,
                        score=score,
                    )

    return best
