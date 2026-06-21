from collections import Counter

from ptcg import card_db
from ptcg.agent_base import BaseAgent
from ptcg.decks import DECKS
from ptcg.rules.rule import Rule
from ptcg.rules.basic_rules import (
    SelectBestAttack,
    RetreatIfLowHP,
    PlayPokemonToBench,
    AttachEnergyToActive,
    EvolveIfBeneficial,
    SearchForEnergy,
)
from ptcg.rules.fallback import RandomFallback

_DECK: list[int] = DECKS["default"]

# Priority order: first matching rule wins.
# Edit this list to add, remove, or reorder rules.
DEFAULT_RULES: list[Rule] = [
    SelectBestAttack(),     # ranks attacks by effective damage (weakness/resistance aware)
    EvolveIfBeneficial(),
    SearchForEnergy(),
    AttachEnergyToActive(),
    PlayPokemonToBench(),
    RetreatIfLowHP(),
    RandomFallback(),       # must stay last
]


class RuleBasedAgent(BaseAgent):

    def __init__(self, rules: list[Rule] | None = None):
        self.rules    = rules if rules is not None else DEFAULT_RULES
        self.rule_log: list[str] = []   # name of the rule that fired each turn

    def get_deck(self) -> list[int]:
        return _DECK

    def on_game_start(self) -> None:
        card_db.load()          # no-op if already loaded or on non-Linux
        self.rule_log.clear()

    def on_game_end(self, result: dict) -> None:
        pass

    def select_action(self, obs: dict) -> list[int]:
        for rule in self.rules:
            if rule.matches(obs):
                self.rule_log.append(type(rule).__name__)
                return rule.select(obs)
        # Should never reach here — RandomFallback always matches
        self.rule_log.append("RandomFallback")
        return RandomFallback().select(obs)

    def rule_summary(self) -> dict[str, int]:
        """Return a {rule_name: count} dict for all decisions so far."""
        return dict(Counter(self.rule_log))
