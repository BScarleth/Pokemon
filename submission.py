"""
Kaggle arena entry point.

Bundled into submission.tar.gz (as main.py) together with the cg/ and ptcg/
packages by scripts/build_submission.py. The competition harness imports this
file and calls agent(obs_dict) each turn.

To change which agent competes, swap the import and instantiation below.
"""

import os
import sys

# Make the bundled cg/ and ptcg/ packages importable when the archive is
# extracted by the arena.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ptcg import card_db
from ptcg.agents.rule_based_agent import RuleBasedAgent

card_db.load()                 # load card/attack metadata once at startup
_agent = RuleBasedAgent()


def agent(obs_dict: dict) -> list[int]:
    return _agent(obs_dict)
