import random

from ptcg.rules.rule import Rule
from ptcg import observation as obs_utils


class RandomFallback(Rule):
    """Always matches. Picks actions at random. Must be the last rule in any list."""

    def matches(self, obs: dict) -> bool:
        return True

    def select(self, obs: dict) -> list[int]:
        options = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        return random.sample(range(len(options)), max_count)
