"""
Basic rule set for the rule-based agent.

Two data sources, two access styles:
  - Live board state (active/bench/hand Pokémon, the option list) comes from the
    raw observation dict via ``obs_utils`` — accessed with ``.get(...)``. Always
    resolve "me" / "opponent" through the perspective helpers (my_active, …),
    because the players array is absolute and the agent may be player 0 or 1.
  - Static card metadata (``CardData`` / ``Attack``) comes from ``card_db`` as
    typed dataclasses (from ``cg.api``) — accessed with attribute access.

CardData fields:  cardId, name, cardType, retreatCost, hp, weakness, resistance,
                  energyType, basic, stage1, stage2, ex, megaEx, tera, attacks
Attack fields:    attackId, name, text, damage, energies
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
      1. Attacks that win the game this turn (KO while opponent has ≤ 1 prize left).
      2. Attacks that KO the opponent using effective damage.
      3. Attacks that hit weakness and leave the opponent in KO range next turn.
      4. Attacks with the highest effective damage.
      5. Tiebreaker A: prefer non-resisted attacks when effective damage is equal.
      6. Tiebreaker B: prefer lower energy cost.

    Falls through to RandomFallback when the card database is not loaded.
    """

    def _attack_options(self, obs: dict) -> list[tuple[int, dict]]:
        return [
            (i, opt) for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.ATTACK
        ]

    def _attack_damage(self, opt: dict) -> int:
        attack = card_db.get_attack(opt.get("attackId", -1))
        return attack.damage if attack else 0

    def _attack_energy_cost(self, opt: dict) -> int:
        attack = card_db.get_attack(opt.get("attackId", -1))
        return len(attack.energies) if attack else 0

    def _effective(self, opt: dict, attacker_card, defender_card) -> int:
        return damage.compute_effective_damage(
            attacker_card, defender_card, self._attack_damage(opt)
        )

    def _score(
        self,
        opt: dict,
        attacker_card,
        defender_card,
        opponent_hp: int,
        opponent_prizes_left: int,
        best_effective_this_turn: int,
    ) -> tuple:
        effective   = self._effective(opt, attacker_card, defender_card)
        energy_cost = self._attack_energy_cost(opt)

        kos_opponent = effective >= opponent_hp
        wins_game    = kos_opponent and opponent_prizes_left <= 1

        remaining_after_hit = opponent_hp - effective
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

    def matches(self, obs: dict) -> bool:
        return card_db.is_loaded() and bool(self._attack_options(obs))

    def select(self, obs: dict) -> list[int]:
        attack_opts = self._attack_options(obs)

        my_active = obs_utils.my_active(obs)
        opponent  = obs_utils.opponent_active(obs)

        # Guard: if board state is incomplete fall back to first available attack
        if my_active is None or opponent is None:
            return [attack_opts[0][0]] * obs_utils.get_max_count(obs)

        attacker_card        = card_db.get_card(my_active.get("id", -1))
        defender_card        = card_db.get_card(opponent.get("id", -1))
        opponent_hp          = opponent.get("hp", 0)
        opponent_prizes_left = len(obs_utils.opponent_prize_cards(obs))

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
                opponent_prizes_left,
                best_effective_this_turn,
            ),
        )[0]

        return [best_idx] * obs_utils.get_max_count(obs)


# ── 2. Retreat if active Pokémon HP is critically low ────────────────────────

class RetreatIfLowHP(Rule):
    """Retreat when active remaining HP ≤ HP_THRESHOLD and retreat is available."""

    HP_THRESHOLD = 30

    def _retreat_indices(self, obs: dict) -> list[int]:
        return [
            i for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.RETREAT
        ]

    def matches(self, obs: dict) -> bool:
        active = obs_utils.my_active(obs)
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
    Prefers the Pokémon with the highest HP.
    Falls through if the card database is not loaded.
    """

    def _play_pokemon_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        result = []
        for i, opt in enumerate(obs_utils.get_options(obs)):
            if opt.get("type") != OptionType.PLAY:
                continue
            card = card_db.get_card(opt.get("cardId", -1))
            if card and card.cardType == CardType.POKEMON and card.basic:
                result.append(i)
        return result

    def matches(self, obs: dict) -> bool:
        bench = obs_utils.my_bench(obs)
        player = obs_utils.my_player_state(obs)
        bench_max = (player or {}).get("benchMax", 5)
        return len(bench) < bench_max and bool(self._play_pokemon_indices(obs))

    def select(self, obs: dict) -> list[int]:
        indices = self._play_pokemon_indices(obs)
        options = obs_utils.get_options(obs)

        def hp_of(i: int) -> int:
            card = card_db.get_card(options[i].get("cardId", -1))
            return card.hp if card else 0

        best = max(indices, key=hp_of)
        return [best] * obs_utils.get_max_count(obs)


# ── 4. Attach energy to the active Pokémon ───────────────────────────────────

class AttachEnergyToActive(Rule):
    """
    Attach energy to the active Pokémon, subject to:
      - Energy can only be attached once per turn (State.energyAttached).
      - Skip if the active is almost dead (hp ≤ threshold) AND the opponent
        cannot be KO'd this turn AND the active is not a Stage 2 Pokémon.
    """

    HP_THRESHOLD = 30

    def _attach_indices(self, obs: dict) -> list[int]:
        return [
            i for i, opt in enumerate(obs_utils.get_options(obs))
            if opt.get("type") == OptionType.ATTACH
        ]

    def _active_is_almost_dead(self, obs: dict) -> bool:
        active = obs_utils.my_active(obs)
        return active is not None and active.get("hp", 999) <= self.HP_THRESHOLD

    def _can_ko_this_turn(self, obs: dict) -> bool:
        if not card_db.is_loaded():
            return False
        opponent = obs_utils.opponent_active(obs)
        if opponent is None:
            return False
        opponent_hp = opponent.get("hp", 0)
        for opt in obs_utils.get_options(obs):
            if opt.get("type") != OptionType.ATTACK:
                continue
            attack = card_db.get_attack(opt.get("attackId", -1))
            if attack and attack.damage >= opponent_hp:
                return True
        return False

    def _active_is_stage2(self, obs: dict) -> bool:
        active = obs_utils.my_active(obs)
        if active is None or not card_db.is_loaded():
            return False
        card = card_db.get_card(active.get("id", -1))
        return bool(card and card.stage2)

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
    Evolve the active Pokémon when the evolution has more HP than the current
    form OR the active has a special condition (evolving cures it).

    Block evolution if the evolution's best attack deals less damage or requires
    more energy than the current form's best attack.
    """

    def _active_has_status(self, obs: dict) -> bool:
        return any(obs_utils.my_status_conditions(obs).values())

    def _best_attack(self, card):
        """Return the highest-damage Attack for a CardData, or None."""
        if card is None:
            return None
        best = None
        for attack_id in card.attacks:
            atk = card_db.get_attack(attack_id)
            if atk and (best is None or atk.damage > best.damage):
                best = atk
        return best

    @staticmethod
    def _damage(attack) -> int:
        return attack.damage if attack else 0

    @staticmethod
    def _energy_cost(attack) -> int:
        return len(attack.energies) if attack else 0

    def _beneficial_evolve_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        active = obs_utils.my_active(obs)
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
            if evo_card is None:
                continue
            evo_best = self._best_attack(evo_card)

            # Block if evolution has a weaker best attack or higher energy cost
            if self._damage(evo_best) < self._damage(current_best):
                continue
            if self._energy_cost(evo_best) > self._energy_cost(current_best):
                continue

            # Allow if HP increases or current form has a status condition
            if evo_card.hp > current_hp or has_status:
                result.append(i)

        return result

    def matches(self, obs: dict) -> bool:
        return bool(self._beneficial_evolve_indices(obs))

    def select(self, obs: dict) -> list[int]:
        candidates = self._beneficial_evolve_indices(obs)
        options = obs_utils.get_options(obs)

        def hp_of(i: int) -> int:
            card = card_db.get_card(options[i].get("cardId", -1))
            return card.hp if card else 0

        best = max(candidates, key=hp_of)
        return [best] * obs_utils.get_max_count(obs)


# ── 6. Search for energy if none attached ────────────────────────────────────

class SearchForEnergy(Rule):
    """
    If the active Pokémon has no energy attached and an energy card is playable
    from hand (card type BASIC_ENERGY or SPECIAL_ENERGY), play it.
    Falls through if the card database is not loaded.
    """

    def _active_has_energy(self, obs: dict) -> bool:
        active = obs_utils.my_active(obs)
        if active is None:
            return False
        return len(active.get("energies", [])) > 0

    def _energy_play_indices(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            return []
        result = []
        for i, opt in enumerate(obs_utils.get_options(obs)):
            if opt.get("type") != OptionType.PLAY:
                continue
            card = card_db.get_card(opt.get("cardId", -1))
            if card and card.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
                result.append(i)
        return result

    def matches(self, obs: dict) -> bool:
        return not self._active_has_energy(obs) and bool(self._energy_play_indices(obs))

    def select(self, obs: dict) -> list[int]:
        indices = self._energy_play_indices(obs)
        return [indices[0]] * obs_utils.get_max_count(obs)
