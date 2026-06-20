import random

from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils

# Default deck taken from the cabt engine's bundled example (cabt.py).
# Replace with your own 60-card deck once you know the full card pool.
_DECK: list[int] = [
    721, 721,
    722, 722, 722, 722,
    723, 723, 723, 723,
    1092,
    1121, 1121,
    1145, 1145,
    1163, 1163,
    1219, 1219, 1219, 1219,
    1227, 1227, 1227, 1227,
    1262, 1262,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3,
]  # 60 cards


class RandomAgent(BaseAgent):

    def get_deck(self) -> list[int]:
        return _DECK

    def on_game_start(self) -> None:
        pass

    def on_game_end(self, result: dict) -> None:
        pass

    def select_action(self, obs: dict) -> list[int]:
        options = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        return random.sample(range(len(options)), max_count)
