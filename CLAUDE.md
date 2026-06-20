# CLAUDE.md

## Project overview

Python framework for competing in the [Kaggle Pokemon TCG AI Battle Challenge](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/overview).
Two AI agents play full Pokemon Trading Card Games against each other using the **cabt engine**
(a Linux-only battle simulator, pre-installed in Kaggle competition notebooks only).

---

## Reference docs — always consult before working on this project

These docs must be read before any agent implementation, game logic change, or brainstorming session:

| Doc | When to use |
|---|---|
| [`docs/cabt_api_reference.md`](docs/cabt_api_reference.md) | Any time you touch agent code, read the observation dict, select actions, build decks, or use the `game`/`api`/`sim` modules. Ground truth for what the engine exposes. |
| [`docs/ptcg_ruleset.md`](docs/ptcg_ruleset.md) | Any time you reason about game strategy, card interactions, turn sequencing, damage, status conditions, win conditions, or evolution chains. Contains the **Simulator Differences** section — deviations from official TCG rules that directly affect what the engine offers as valid actions. |

**Mandatory before:**
- Writing or reviewing any agent in `src/ptcg/agents/`
- Modifying `observation.py`, `game.py`, or `agent_base.py`
- Brainstorming new agent strategies, heuristics, or search approaches
- Designing or evaluating deck compositions
- Debugging unexpected agent behavior (check simulator differences first)

---

## Repository layout

```
src/ptcg/
├── agent_base.py        # Abstract BaseAgent — every agent subclasses this
├── observation.py       # Stateless helpers for reading the obs dict
├── game.py              # Thin kaggle_environments / cabt wrapper
└── agents/
    └── random_agent.py  # Baseline: uniform random action selection

docs/
├── cabt_api_reference.md   # Engine API, all data structures, enums, functions
└── ptcg_ruleset.md         # TCG rules + simulator deviations

scripts/
└── build_submission.py  # Generates flat submission.py from any BaseAgent subclass

notebooks/
└── test_agents.ipynb    # Kaggle notebook — the only place battles can actually run
```

---

## Core architecture

### Agent call protocol

The cabt engine calls `agent(obs, *args) -> list[int]` every step. `BaseAgent.__call__`
handles the two-phase routing:

```
First call  →  obs["select"] is None  →  BaseAgent calls get_deck()   → returns list[int] (60 card IDs)
All others  →  obs["select"] is set   →  BaseAgent calls select_action(obs) → returns list[int] (option indices)
```

Never override `__call__`. Implement the four abstract methods instead.

### BaseAgent interface (`src/ptcg/agent_base.py`)

```python
class BaseAgent(ABC):
    def get_deck(self) -> list[int]: ...         # return exactly 60 card IDs
    def select_action(self, obs: dict) -> list[int]: ...  # return indices into obs["select"]["option"]
    def on_game_start(self) -> None: ...         # called once before the first turn
    def on_game_end(self, result: dict) -> None: ...      # called once after the game ends
```

All four methods are abstract — every agent must implement all of them.

### observation.py helpers

Always use `obs_utils` functions instead of raw dict indexing in agent code.
This keeps agent code readable and makes `build_submission.py` inlining reliable.

```python
from ptcg import observation as obs_utils

obs_utils.get_options(obs)              # obs["select"]["option"]
obs_utils.get_max_count(obs)            # obs["select"]["maxCount"]
obs_utils.has_select(obs)              # bool
obs_utils.get_current_state(obs)       # obs["current"]
obs_utils.get_players(obs)             # obs["current"]["players"]
obs_utils.get_active_pokemon(obs, 0)   # your active Pokémon (player index 0)
obs_utils.get_active_pokemon(obs, 1)   # opponent's active Pokémon
obs_utils.get_bench(obs, 0)            # your bench
obs_utils.get_hand(obs, 0)             # your hand (opponent's hand is None)
obs_utils.get_hand_count(obs, 0)       # hand size (visible for both players)
obs_utils.get_prize_cards(obs, 0)      # your prize cards (face-down = None)
obs_utils.get_deck_count(obs, 0)       # remaining deck size
obs_utils.get_discard(obs, 0)          # discard pile
obs_utils.get_status_conditions(obs, 0) # {"poisoned": bool, "burned": bool, ...}
```

If you add a new helper to `observation.py`, also add its inline equivalent to
`OBS_UTILS_INLINE` in `scripts/build_submission.py` or the build step will fail.

---

## Adding a new agent

### 1. Create the agent file

File must live at `src/ptcg/agents/<snake_case_of_class>.py`.
The naming rule is strict — `build_submission.py` and the test notebook both
derive the module path from the class name.

```
MyAgent      → src/ptcg/agents/my_agent.py
GreedyAgent  → src/ptcg/agents/greedy_agent.py
```

### 2. Implement BaseAgent

```python
from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils

_DECK: list[int] = [...]  # exactly 60 card IDs

class MyAgent(BaseAgent):

    def get_deck(self) -> list[int]:
        return _DECK

    def on_game_start(self) -> None:
        pass  # reset any per-game state here

    def on_game_end(self, result: dict) -> None:
        pass  # result contains {"steps": ..., "rewards": [r0, r1]}

    def select_action(self, obs: dict) -> list[int]:
        options   = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        # return a list of indices into options, length == max_count
        return [...]
```

Key constraints for `select_action`:
- Return exactly `max_count` indices (not fewer, not more).
- All indices must be valid positions in `options` (0 to `len(options) - 1`).
- Do not assume an action is available based on board state — only what appears in
  `options` can be selected (the simulator withholds some actions; see ruleset doc).

### 3. Define a deck

A deck is exactly **60 card IDs** (integers). Rules:
- Maximum 4 copies of any one card (Basic Energy is exempt).
- Must contain at least 1 Basic Pokémon.
- Card IDs come from `all_card_data()` or the engine's bundled default deck.
- Store the deck as a module-level `_DECK` constant in the agent file.

The default deck used by `RandomAgent` is a safe starting point for new agents.

### 4. Test on Kaggle

Local execution of battles is not possible — `libcg.so` is Linux-only and not on PyPI.

1. Push your branch to GitHub.
2. Open `notebooks/test_agents.ipynb` in a Kaggle competition notebook.
3. Set `GITHUB_URL` to your repo and add your class name to `AGENTS`.
4. Run all cells — the notebook runs round-robin battles and prints results.

### 5. Build and submit

```bash
# In scripts/build_submission.py, set:
AGENT_CLASS  = "MyAgent"
AGENT_MODULE = "ptcg.agents.my_agent"

# Then:
python scripts/build_submission.py   # writes submission.py
kaggle competitions submit pokemon-tcg-ai-battle -f submission.py -m "description"
```

The build script extracts `select_action`'s source, inlines all `obs_utils.*` calls,
and wraps everything in a standalone `def agent(obs, *args)` function.

---

## Key constraints

| Constraint | Detail |
|---|---|
| **No local imports in submission** | `submission.py` must be self-contained. Use `build_submission.py` to generate it — never edit it by hand. |
| **cabt is Linux-only** | All actual battle execution happens on Kaggle. Local dev is writing and linting only. |
| **Simulator overrides rules** | Where the engine differs from official TCG rules, engine behavior wins. Details in `docs/ptcg_ruleset.md` → *Simulator Differences*. |
| **Only pick from options** | `obs["select"]["option"]` is the only source of valid actions. Never infer availability from board state. |
| **Exactly 60 cards** | `battle_start` raises `ValueError` if either deck is not exactly 60 cards. |
| **obs_utils inline requirement** | Any `obs_utils.*` call used inside `select_action` must have an entry in `OBS_UTILS_INLINE` in `build_submission.py`. |

---

## game.py wrapper (quick reference)

```python
from ptcg.game import create_environment, run_battle, get_rewards

env = create_environment(deck0, deck1)   # wraps make("cabt", configuration={"decks": ...})
steps = run_battle(env, agent0, agent1)  # runs env.run([agent0, agent1])
rewards = get_rewards(env)               # [reward_player0, reward_player1]
```

Use these wrappers in tests and the notebook rather than calling `kaggle_environments` directly.