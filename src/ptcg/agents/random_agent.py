import random

from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils
from ptcg.decks import DECKS

_DECK: list[int] = DECKS["default"]


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
