import json
import random

from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils

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


class InspectorAgent(BaseAgent):
    """
    Plays randomly while recording every observation.
    Use it to discover the real structure of options before writing rules.

    After a battle, call print_options(max_turns=N) to see the raw option dicts.
    """

    def __init__(self):
        self.history: list[dict] = []

    def get_deck(self) -> list[int]:
        return _DECK

    def on_game_start(self) -> None:
        self.history.clear()

    def on_game_end(self, result: dict) -> None:
        pass

    def select_action(self, obs: dict) -> list[int]:
        options = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        chosen = random.sample(range(len(options)), max_count)
        self.history.append({
            "options":  options,
            "max_count": max_count,
            "chosen":   chosen,
            "current":  obs.get("current"),
        })
        return chosen

    def print_options(self, max_turns: int = 5) -> None:
        shown = self.history[:max_turns]
        print(f"Showing {len(shown)} of {len(self.history)} turns.\n")
        for i, turn in enumerate(shown):
            opts = turn["options"]
            print(f"--- turn {i + 1}  (pick {turn['max_count']} of {len(opts)}) ---")
            for j, opt in enumerate(opts):
                marker = "✓" if j in turn["chosen"] else " "
                print(f"  [{marker}] {j}: {json.dumps(opt, ensure_ascii=False, indent=4)}")
            print()
