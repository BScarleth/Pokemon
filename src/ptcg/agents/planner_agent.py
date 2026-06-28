"""
PlannerAgent — a plan-driven rule-based agent.

Unlike RuleBasedAgent (which decides each action independently), PlannerAgent
builds one turn-level ``AttackPlan`` at the start of every turn and then judges
every action by how well it serves that plan:

  - attach energy to the *planned attacker* until it can attack,
  - switch / retreat to bring the planned attacker active,
  - play Boss Orders only when it enables the planned KO / threat removal,
  - then execute the planned attack,
  - choose searched cards (TO_HAND) that fill gaps in the plan.

Targets are valued with ``pokemon_score`` (prize count first), not raw HP.

Decision labels are recorded in ``self.rule_log`` so the notebook's
"rule firing breakdown" works for this agent too.

NOTE: integration logic (multi-step setup across a turn) can only be validated
on Kaggle/Linux, where the engine runs. The pure-logic pieces (pokemon_score,
build_attack_plan) are unit-tested.
"""

from collections import Counter

from ptcg import card_db
from ptcg import observation as obs_utils
from ptcg.agent_base import BaseAgent
from ptcg.decks import DECKS
from ptcg.planning.attack_plan import AttackPlan, build_attack_plan
from ptcg.planning.pokemon_score import pokemon_score
from ptcg.rules.fallback import RandomFallback
from ptcg.rules.schema import (
    AreaType, CardType, OptionType, SelectType, SelectContext,
    energy_already_attached,
)

_DECK: list[int] = DECKS["default"]

# Cards that drag an opponent's benched Pokémon into the Active Spot.
# Extend this set with any other "gust" cards in your deck.
GUST_CARD_IDS = {1182}    # Boss Orders
# Cards that switch your own Active Pokémon.
SWITCH_CARD_IDS = {1123}  # Switch

# Score tiers (higher = chosen first within a single selection).
S_EXECUTE_ATTACK = 100_000
S_ABILITY        = 12_000
S_BOSS_FOR_PLAN  = 9_000
S_SWITCH_FOR_PLAN = 8_000
S_ATTACH_PLAN    = 7_000
S_EVOLVE         = 6_000
S_PLAY_BASIC     = 5_000
S_PLAY_SUPPORT   = 4_000
S_OTHER_ATTACK   = 1_000
S_ATTACH_OTHER   = 200
S_PLAY_LOW       = 50
S_RETREAT_LOW    = 40
S_END_TURN       = -1


class PlannerAgent(BaseAgent):

    def __init__(self, deck: list[int] | None = None):
        self._deck = deck if deck is not None else _DECK
        self._plan = AttackPlan()
        self._turn = -1
        self.rule_log: list[str] = []

    # ── BaseAgent interface ───────────────────────────────────────────────────

    def get_deck(self) -> list[int]:
        return self._deck

    def on_game_start(self) -> None:
        card_db.load()
        self._plan = AttackPlan()
        self._turn = -1
        self.rule_log.clear()

    def on_game_end(self, result: dict) -> None:
        pass

    def rule_summary(self) -> dict[str, int]:
        return dict(Counter(self.rule_log))

    def select_action(self, obs: dict) -> list[int]:
        if not card_db.is_loaded():
            self.rule_log.append("RandomFallback")
            return RandomFallback().select(obs)

        select = obs.get("select") or {}
        is_main = select.get("type") == SelectType.MAIN

        # (Re)build the plan once per turn, at the MAIN selection.
        if is_main:
            turn = (obs.get("current") or {}).get("turn", -1)
            if turn != self._turn:
                self._turn = turn
                self._plan = self._build_plan(obs)

        options   = obs_utils.get_options(obs)
        min_count = select.get("minCount", 1)
        max_count = select.get("maxCount", 1)

        scored = [
            (self._score_option(obs, opt, is_main), i)
            for i, opt in enumerate(options)
        ]
        # scored item: ((score, label), index)
        scored.sort(key=lambda s: s[0][0], reverse=True)

        k = max(min_count, max_count)
        chosen = [idx for (_, idx) in scored[:k]]
        self.rule_log.append(scored[0][0][1] if scored else "none")
        return chosen

    # ── Plan construction ─────────────────────────────────────────────────────

    def _build_plan(self, obs: dict) -> AttackPlan:
        options = obs_utils.get_options(obs)

        can_switch = any(o.get("type") == OptionType.RETREAT for o in options) or \
            any(self._hand_card_id(obs, o) in SWITCH_CARD_IDS
                for o in options if o.get("type") == OptionType.PLAY)
        can_boss = any(self._hand_card_id(obs, o) in GUST_CARD_IDS
                       for o in options if o.get("type") == OptionType.PLAY)
        energy_attachable = (not energy_already_attached(obs)) and \
            any(o.get("type") == OptionType.ATTACH for o in options)

        return build_attack_plan(obs, can_switch, can_boss, energy_attachable)

    # ── Option scoring ────────────────────────────────────────────────────────

    def _score_option(self, obs: dict, opt: dict, is_main: bool) -> tuple[int, str]:
        t = opt.get("type")

        # Universal simple option types.
        if t == OptionType.YES:
            return (1, "yes")
        if t == OptionType.NO:
            return (0, "no")
        if t == OptionType.NUMBER:
            return (opt.get("number", 0), "number")   # take the largest count

        if is_main:
            return self._score_main(obs, opt)
        return self._score_selection(obs, opt)

    def _score_main(self, obs: dict, opt: dict) -> tuple[int, str]:
        t    = opt.get("type")
        plan = self._plan

        if t == OptionType.ATTACK:
            aid = opt.get("attackId")
            if plan.valid and aid == plan.attack_id and self._plan_ready(obs):
                return (S_EXECUTE_ATTACK, "execute_attack")
            bonus = 500 if (plan.valid and aid == plan.attack_id) else 0
            return (S_OTHER_ATTACK + bonus, "attack")

        if t == OptionType.PLAY:
            cid  = self._hand_card_id(obs, opt)
            card = card_db.get_card(cid)
            if cid in GUST_CARD_IDS:
                if plan.valid and plan.best_target != 0:
                    return (S_BOSS_FOR_PLAN, "boss_for_plan")
                return (S_PLAY_LOW, "play_low")
            if cid in SWITCH_CARD_IDS:
                if plan.valid and plan.best_attacker != 0:
                    return (S_SWITCH_FOR_PLAN, "switch_for_plan")
                return (S_PLAY_LOW, "play_low")
            if card and card.cardType == CardType.POKEMON and card.basic:
                if self._bench_has_space(obs):
                    return (S_PLAY_BASIC, "play_pokemon")
                return (S_PLAY_LOW, "play_low")
            if card and card.cardType in (CardType.SUPPORTER, CardType.ITEM,
                                          CardType.STADIUM, CardType.TOOL):
                return (S_PLAY_SUPPORT, "play_support")
            return (S_PLAY_LOW, "play_other")

        if t == OptionType.ATTACH:
            if self._attaches_to_plan_attacker(obs, opt) and self._attacker_needs_energy(obs):
                return (S_ATTACH_PLAN, "attach_for_plan")
            return (S_ATTACH_OTHER, "attach_other")

        if t == OptionType.EVOLVE:
            return (S_EVOLVE, "evolve")

        if t == OptionType.RETREAT:
            if plan.valid and plan.best_attacker != 0:
                return (S_SWITCH_FOR_PLAN, "switch_for_plan")
            return (S_RETREAT_LOW, "retreat_low")

        if t == OptionType.ABILITY:
            return (S_ABILITY, "ability")

        if t == OptionType.END:
            return (S_END_TURN, "end_turn")

        return (0, "other")

    def _score_selection(self, obs: dict, opt: dict) -> tuple[int, str]:
        """Score card/energy selections (non-MAIN sub-prompts)."""
        select  = obs.get("select") or {}
        context = select.get("context")
        plan    = self._plan

        if opt.get("type") != OptionType.CARD:
            # energy/tool/skill selections: keep deterministic, prefer first
            return (-opt.get("index", 0), "select_default")

        area    = opt.get("area")
        index   = opt.get("index", 0)
        pidx    = opt.get("playerIndex")
        opp_idx = obs_utils.get_opponent_index(obs)
        card    = self._card_at(obs, area, index, pidx)

        # Choosing an opponent Pokémon (e.g. Boss Orders target).
        if pidx == opp_idx:
            score = pokemon_score(card) if card else 0
            if plan.valid and card and card.get("serial") == plan.best_target_serial:
                score += 100_000
            return (score, "target_select")

        # Choosing one of our Pokémon to bring active.
        if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
            score = (len(card.get("energies", [])) * 10) if card else 0
            if plan.valid and card and card.get("serial") == plan.best_attacker_serial:
                score += 1000
            return (score, "switch_select")

        # Setup / putting Pokémon into play: prefer higher-HP basics.
        if context in (SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON,
                       SelectContext.TO_FIELD, SelectContext.TO_BENCH):
            meta = card_db.get_card(card.get("id", -1)) if card else None
            return ((meta.hp if meta else 0), "setup_select")

        # Searching cards to hand: pick what supports the plan.
        if context == SelectContext.TO_HAND:
            return (self._to_hand_score(obs, card), "to_hand")

        return (-index, "card_default")

    # ── Plan-readiness helpers ────────────────────────────────────────────────

    def _plan_ready(self, obs: dict) -> bool:
        plan = self._plan
        if not plan.valid:
            return False
        active = obs_utils.my_active(obs)
        opp    = obs_utils.opponent_active(obs)
        if active is None or opp is None:
            return False
        if active.get("serial") != plan.best_attacker_serial:
            return False
        if opp.get("serial") != plan.best_target_serial:
            return False
        return len(active.get("energies", [])) >= plan.required_energy

    def _attacker_needs_energy(self, obs: dict) -> bool:
        plan = self._plan
        attacker = self._find_my_pokemon(obs, plan.best_attacker_serial)
        if attacker is None:
            return False
        return len(attacker.get("energies", [])) < plan.required_energy

    def _attaches_to_plan_attacker(self, obs: dict, opt: dict) -> bool:
        plan = self._plan
        if not plan.valid:
            return False
        target = self._card_at(obs, opt.get("inPlayArea"), opt.get("inPlayIndex", 0),
                               obs_utils.get_your_index(obs))
        return target is not None and target.get("serial") == plan.best_attacker_serial

    # ── TO_HAND scoring ───────────────────────────────────────────────────────

    def _to_hand_score(self, obs: dict, card: dict | None) -> int:
        if card is None:
            return 0
        cid  = card.get("id", -1)
        meta = card_db.get_card(cid)
        score = 200

        # Avoid grabbing redundant copies already in hand.
        in_hand = sum(1 for c in obs_utils.my_hand_cards(obs) if c.get("id") == cid)
        score -= 100 * in_hand

        if meta is None:
            return score

        plan = self._plan
        # Energy when the planned attacker still needs it.
        if meta.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
            if plan.valid and self._attacker_needs_energy(obs):
                score += 120
        # More copies of the planned attacker line.
        attacker = self._find_my_pokemon(obs, plan.best_attacker_serial) if plan.valid else None
        if attacker is not None and cid == attacker.get("id"):
            score += 100
        # Key supporters are generally worth holding.
        if meta.cardType == CardType.SUPPORTER:
            score += 60
        return score

    # ── Low-level lookups ─────────────────────────────────────────────────────

    def _hand_card_id(self, obs: dict, opt: dict) -> int:
        hand = obs_utils.my_hand_cards(obs)
        idx = opt.get("index", -1)
        if 0 <= idx < len(hand):
            return hand[idx].get("id", -1)
        return -1

    def _bench_has_space(self, obs: dict) -> bool:
        player = obs_utils.my_player_state(obs) or {}
        return len(obs_utils.my_bench(obs)) < player.get("benchMax", 5)

    def _find_my_pokemon(self, obs: dict, serial: int):
        if serial < 0:
            return None
        active = obs_utils.my_active(obs)
        if active and active.get("serial") == serial:
            return active
        for pk in obs_utils.my_bench(obs):
            if pk and pk.get("serial") == serial:
                return pk
        return None

    def _card_at(self, obs: dict, area, index: int, player_index: int):
        if area == AreaType.ACTIVE:
            return obs_utils.get_active_pokemon(obs, player_index)
        if area == AreaType.BENCH:
            bench = obs_utils.get_bench(obs, player_index)
            return bench[index] if 0 <= index < len(bench) else None
        if area == AreaType.HAND:
            hand = obs_utils.get_hand(obs, player_index)
            return hand[index] if 0 <= index < len(hand) else None
        if area == AreaType.DISCARD:
            discard = obs_utils.get_discard(obs, player_index)
            return discard[index] if 0 <= index < len(discard) else None
        # Cards offered from the deck during a search live on select.deck.
        deck = (obs.get("select") or {}).get("deck")
        if deck and 0 <= index < len(deck):
            return deck[index]
        return None
