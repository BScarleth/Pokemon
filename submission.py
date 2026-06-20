"""
Auto-generated from RandomAgent by scripts/build_submission.py.
Do not edit manually — run the script to regenerate.
"""
import random

DECK: list[int] = [
    721, 721, 722, 722, 722, 722, 723, 723, 723, 723,
    1092, 1121, 1121, 1145, 1145, 1163, 1163, 1219, 1219, 1219,
    1219, 1227, 1227, 1227, 1227, 1262, 1262, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
]  # 60 cards


def agent(obs: dict, *args) -> list[int]:
    if obs.get("select") is None:
        return DECK
    options = obs["select"]["option"]
    max_count = obs["select"]["maxCount"]
    return random.sample(range(len(options)), max_count)
