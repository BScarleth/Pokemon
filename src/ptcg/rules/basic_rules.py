"""
Basic rule set for the rule-based agent.

Field references are taken from the official cabt API docs:
https://matsuoinstitute.github.io/cabt/api.html

Pokemon fields:  id, serial, hp (remaining), maxHp, energies, energyCards,
                 tools, preEvolution, appearThisTurn
Option fields:   type (OptionType int), attackId, cardId, serial, area,
                 index, playerIndex, ...
State fields:    energyAttached, retreated, supporterPlayed, turn, yourIndex,
                 result, players, stadium
"""

from ptcg import card_db
from ptcg import observation as obs_utils
from ptcg.rules import damage
from ptcg.rules.rule import Rule
from ptcg.rules.schema import OptionType, CardType, energy_already_attached


# ── 1. Select the best available attack ──────────────────────────────────────

class SelectBestAttack(Rule):
    """
    Ranks all available attack options using effective damage (base damage
    adjusted for the opponent's weakness and resistance from card data) and
    selects the best one.

    Priority order within attack selection:
      1. Attacks that win the game this turn (KO + exactly 1 prize remaining).
      2. Attacks that KO the opponent using effective damage.
      3. Attacks that hit weakness and leave the opponent in KO range next turn
         (remaining HP after this hit ≤ best effective damage we can deal).
      4. Attacks with the highest effective damage.
      5. Tiebreaker A: prefer non-resisted attacks when effective damage is equal.
      6. Tiebreaker B: prefer lower energy cost.

    Weakness and resistance are read exclusively from all_card_data() card
    records — no hard-coded type chart is used. The damage formula is:
      effective = base_damage
      if defender.weakness == attacker.energyType: effective *= 2
      if defender.resistance == attacker.energyType: effective = max(0, effective - 30)

    Falls through to RandomFallback when the card database is not loaded.
    """

    # ── helpers ───────────────────────────────────────────────────────────────

    def _attack_options(self, obs: dict) -> list[tuple[int, dict]]:
        return [
            (i, opt) for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.ATTACK
        ]

    def _effective(
        self,
        opt: dict,
        attacker_card: dict,
        defender_card: dict,
    ) -> int:
        base = card_db.get_attack(opt.get("attackId", -1)).get("damage", 0)
        return damage.compute_effective_damage(attacker_card, defender_card, base)

    def _score(
        self,
        opt: dict,
        attacker_card: dict,
        defender_card: dict,
        opponent_hp: int,
        prizes_remaining: int,
        best_effective_this_turn: int,
    ) -> tuple:
        effective    = self._effective(opt, attacker_card, defender_card)
        energy_cost  = len(card_db.get_attack(opt.get("attackId", -1)).get("energies", []))

        kos_opponent = effective >= opponent_hp
        wins_game    = kos_opponent and prizes_remaining == 1

        remaining_after_hit  = opponent_hp - effective
        in_ko_range_next = (
            not kos_opponent
            and damage.hits_weakness(attacker_card, defender_card)
            and remaining_after_hit <= best_effective_this_turn
        )

        is_resisted = damage.hits_resistance(attacker_card, defender_card)

        # Higher tuple = better choice; Python compares element by element.
        return (
            wins_game,          # bool — True beats False
            kos_opponent,       # bool
            in_ko_range_next,   # bool
            effective,          # int  — more damage is better
            not is_resisted,    # bool — prefer non-resisted as tiebreaker
            -energy_cost,       # int  — negative so lower cost sorts higher
        )

    # ── Rule interface ────────────────────────────────────────────────────────

    def matches(self, obs: dict) -> bool:
        return card_db.is_loaded() and bool(self._attack_options(obs))

    def select(self, obs: dict) -> list[int]:
        attack_opts = self._attack_options(obs)

        my_active = obs_utils.get_active_pokemon(obs, 0)
        opponent  = obs_utils.get_active_pokemon(obs, 1)

        # Guard: if board state is incomplete fall back to first available attack
        if my_active is None or opponent is None:
            return [attack_opts[0][0]] * obs_utils.get_max_count(obs)

        attacker_card    = card_db.get_card(my_active.get("id", -1))
        defender_card    = card_db.get_card(opponent.get("id", -1))
        opponent_hp      = opponent.get("hp", 0)
        prizes_remaining = len(obs_utils.get_prize_cards(obs, 0))

        # Pre-compute the best effective damage available this turn (used for
        # the "in KO range next turn" check in every candidate's score).
        best_effective_this_turn = max(
            self._effective(opt, attacker_card, defender_card)
            for _, opt in attack_opts
        )

        best_idx = max(
            attack_opts,
            key=lambda t: self._score(
                t[1],
                attacker_card,
                defender_card,
                opponent_hp,
                prizes_remaining,
                best_effective_this_turn,
            ),
        )[0]

        return [best_idx] * obs_utils.get_max_count(obs)


# ── 2. Retreat if active Pokémon HP is critically low ────────────────────────

class RetreatIfLowHP(Rule):
    """
    Retreat when the active Pokémon's remaining HP is at or below HP_THRESHOLD
    and a retreat option is available.
    """

    HP_THRESHOLD = 30  # remaining HP — adjust after seeing real values in play

    def _retreat_indices(self, obs: dict) -> list[int]:
        return [
            i for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.RETREAT
        ]

    def matches(self, obs: dict) -> bool:
        active = obs_utils.get_active_pokemon(obs, 0)
        if active is None:
            return False
        return active.get("hp", 999) <= self.HP_THRESHOLD and bool(self._retreat_indices(obs))

    def select(self, obs: dict) -> list[int]:
        indices = self._retreat_indices(obs)
        return [indices[0]] * obs_utils.get_max_count(obs)


# ── 3. Play a basic Pokémon to the bench ─────────────────────────────────────

class PlayPokemonToBench(Rule):
    """
    Play a basic Pokémon from hand to the bench when bench space is available.
    Prefers the Pokémon with the highest maxHp.
    Falls through if the card database is not loaded.
    """

    def _play_pokemon_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        options = obs_utils.get_options(obs)
        result = []
        for i, opt in enumerate(options):
            if opt.get("type") != OptionType.PLAY:
                continue
            card = card_db.get_card(opt.get("cardId", -1))
            if card.get("cardType") == CardType.POKEMON and card.get("basic", False):
                result.append(i)
        return result

    def matches(self, obs: dict) -> bool:
        bench = obs_utils.get_bench(obs, 0)
        player = obs_utils.get_player_state(obs, 0)
        bench_max = (player or {}).get("benchMax", 5)
        return len(bench) < bench_max and bool(self._play_pokemon_indices(obs))

    def select(self, obs: dict) -> list[int]:
        indices = self._play_pokemon_indices(obs)
        options = obs_utils.get_options(obs)
        # Prefer the basic Pokémon with the most HP
        best = max(
            indices,
            key=lambda i: card_db.get_card(options[i].get("cardId", -1)).get("hp", 0)
        )
        return [best] * obs_utils.get_max_count(obs)


# ── 4. Attach energy to the active Pokémon ───────────────────────────────────

class AttachEnergyToActive(Rule):
    """
    Attach energy to the active Pokémon, subject to these conditions:
      - Energy can only be attached once per turn (checked via State.energyAttached).
      - Skip if the active Pokémon is almost dead (hp <= threshold) AND the
        opponent cannot be KO'd this turn AND the active is not a Stage 2 Pokémon.
    """

    HP_THRESHOLD = 30

    def _attach_indices(self, obs: dict) -> list[int]:
        return [
            i for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.ATTACH
        ]

    def _active_is_almost_dead(self, obs: dict) -> bool:
        active = obs_utils.get_active_pokemon(obs, 0)
        return active is not None and active.get("hp", 999) <= self.HP_THRESHOLD

    def _can_ko_this_turn(self, obs: dict) -> bool:
        if not card_db.is_loaded():
            return False
        opponent = obs_utils.get_active_pokemon(obs, 1)
        if opponent is None:
            return False
        opponent_hp = opponent.get("hp", 0)
        return any(
            card_db.get_attack(opt.get("attackId", -1)).get("damage", 0) >= opponent_hp
            for opt in obs_utils.get_options(obs)
            if opt.get("type") == OptionType.ATTACK
        )

    def _active_is_stage2(self, obs: dict) -> bool:
        active = obs_utils.get_active_pokemon(obs, 0)
        if active is None or not card_db.is_loaded():
            return False
        return card_db.get_card(active.get("id", -1)).get("stage2", False)

    def matches(self, obs: dict) -> bool:
        if energy_already_attached(obs):
            return False
        if not self._attach_indices(obs):
            return False
        if self._active_is_almost_dead(obs):
            if not self._can_ko_this_turn(obs) and not self._active_is_stage2(obs):
                return False
        return True

    def select(self, obs: dict) -> list[int]:
        indices = self._attach_indices(obs)
        return [indices[0]] * obs_utils.get_max_count(obs)


# ── 5. Evolve if beneficial ───────────────────────────────────────────────────

class EvolveIfBeneficial(Rule):
    """
    Evolve the active Pokémon when the evolution:
      - Has more HP than the current form, OR
      - The active Pokémon has a special condition (evolution cures it).

    Block evolution if:
      - The evolution's best attack damage is lower than the current form's, OR
      - The evolution requires more energy for its best attack.
    """

    def _active_has_status(self, obs: dict) -> bool:
        conditions = obs_utils.get_status_conditions(obs, 0)
        return any(conditions.values())

    def _best_attack(self, card: dict) -> dict:
        """Return the Attack dict with the highest damage for a card."""
        best = {}
        for attack_id in card.get("attacks", []):
            atk = card_db.get_attack(attack_id)
            if atk.get("damage", 0) > best.get("damage", 0):
                best = atk
        return best

    def _beneficial_evolve_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        active = obs_utils.get_active_pokemon(obs, 0)
        if active is None:
            return []

        current_card = card_db.get_card(active.get("id", -1))
        current_hp   = active.get("hp", 0)
        current_best = self._best_attack(current_card)
        has_status   = self._active_has_status(obs)

        result = []
        for i, opt in enumerate(obs_utils.get_options(obs)):
            if opt.get("type") != OptionType.EVOLVE:
                continue
            evo_card = card_db.get_card(opt.get("cardId", -1))
            evo_hp   = evo_card.get("hp", 0)
            evo_best = self._best_attack(evo_card)

            # Block if evolution has a weaker best attack or higher energy cost
            if evo_best.get("damage", 0) < current_best.get("damage", 0):
                continue
            if len(evo_best.get("energies", [])) > len(current_best.get("energies", [])):
                continue

            # Allow if HP increases or current form has a status condition
            if evo_hp > current_hp or has_status:
                result.append(i)

        return result

    def matches(self, obs: dict) -> bool:
        return bool(self._beneficial_evolve_indices(obs))

    def select(self, obs: dict) -> list[int]:
        candidates = self._beneficial_evolve_indices(obs)
        options = obs_utils.get_options(obs)
        # Prefer the evolution with the greatest HP
        best = max(
            candidates,
            key=lambda i: card_db.get_card(options[i].get("cardId", -1)).get("hp", 0)
        )
        return [best] * obs_utils.get_max_count(obs)


# ── 6. Search for energy if none in hand ─────────────────────────────────────

class SearchForEnergy(Rule):
    """
    If the active Pokémon has no energy attached and there is a supporter or
    item card in hand that can search for energy (card type BASIC_ENERGY or
    SPECIAL_ENERGY is available as a PLAY option), use it.
    Falls through if card database is not loaded.
    """

    def _active_has_energy(self, obs: dict) -> bool:
        active = obs_utils.get_active_pokemon(obs, 0)
        if active is None:
            return False
        return len(active.get("energies", [])) > 0

    def _energy_search_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        result = []
        for i, opt in enumerate(obs_utils.get_options(obs)):
            if opt.get("type") != OptionType.PLAY:
                continue
            card = card_db.get_card(opt.get("cardId", -1))
            card_type = card.get("cardType")
            if card_type in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
                result.append(i)
        return result

    def matches(self, obs: dict) -> bool:
        return not self._active_has_energy(obs) and bool(self._energy_search_indices(obs))

    def select(self, obs: dict) -> list[int]:
        indices = self._energy_search_indices(obs)
        return [indices[0]] * obs_utils.get_max_count(obs)
