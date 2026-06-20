# Pokemon TCG AI Battle

A modular Python framework for building AI agents that compete in the
[Kaggle PTCG AI Battle Challenge Simulation](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/overview),
powered by the [cabt engine](https://matsuoinstitute.github.io/cabt/).

> **Platform note:** the cabt engine's native library (`libcg.so`) is Linux-only.
> All testing must be done inside a Kaggle notebook. See the [Testing](#testing) section.

---

## Project Structure

```
PokemonBattle/
├── submission.py                      # Arena entry point — imports from ptcg/
├── notebooks/
│   └── test_agents.ipynb              # Kaggle notebook for testing agents
├── scripts/
│   └── build_submission.py            # Generates self-contained submission.py
├── setup.py
├── requirements.txt
└── src/ptcg/
    ├── agent_base.py                  # Abstract base class all agents inherit from
    ├── observation.py                 # Stateless helpers for reading the observation dict
    ├── game.py                        # Wrappers around the kaggle_environments / cabt API
    ├── card_db.py                     # Loads card and attack metadata from the C library
    ├── agents/
    │   ├── random_agent.py            # Baseline: picks actions uniformly at random
    │   ├── rule_based_agent.py        # Priority rule-list agent
    │   └── inspector_agent.py         # Dev tool: records options for schema inspection
    └── rules/
        ├── rule.py                    # Abstract Rule base class
        ├── schema.py                  # OptionType / CardType enums and type-check helpers
        ├── damage.py                  # Effective damage formula (weakness × 2, resistance − 30)
        ├── basic_rules.py             # Rule implementations
        └── fallback.py                # RandomFallback — always matches, picks randomly
```

---

## Setup

```bash
pip install -r requirements.txt
pip install -e .
```

---

## How the Game Works

The cabt engine calls your agent in two phases each game:

1. **Deck selection** (`obs["select"]` is `None`) — return your 60-card deck as `list[int]`.
   `BaseAgent.__call__` handles this automatically via `get_deck()`.
2. **Every turn** (`obs["select"]` is set) — return action indices from `obs["select"]["option"]`.

```
observation dict
├── "logs"     — list of past game events
├── "current"  — full board state (None during deck-selection phase)
│   └── "players"  — list of two PlayerState dicts
│       ├── "active"     — active Pokémon (list of 0-1, may be None)
│       ├── "bench"      — benched Pokémon (up to 5)
│       ├── "hand"       — cards in hand (visible only to owner)
│       ├── "handCount"  — number of cards in hand
│       ├── "prize"      — prize cards (face-down shown as None)
│       ├── "deckCount"  — remaining cards in deck
│       ├── "discard"    — discard pile
│       ├── "poisoned", "burned", "asleep", "paralyzed", "confused"  — bools
└── "select"   — available choices (None during deck-selection phase)
    ├── "option"    — list of available actions
    └── "maxCount"  — how many indices the agent must return
```

---

## Module Reference

### `agent_base.py` — `BaseAgent`

Abstract base class every agent must subclass.

| Method | When called | Must return |
|---|---|---|
| `get_deck()` | Deck-selection phase | `list[int]` — 60 card IDs |
| `select_action(obs)` | Every turn | `list[int]` — action indices |
| `on_game_start()` | Before first turn | Nothing |
| `on_game_end(result)` | After last turn | Nothing |

### `observation.py` — Board State Helpers

```python
from ptcg import observation as obs_utils

obs_utils.get_options(obs)              # available choices
obs_utils.get_max_count(obs)            # how many to pick
obs_utils.get_active_pokemon(obs, 0)    # your active Pokémon
obs_utils.get_bench(obs, 0)             # your bench
obs_utils.get_hand(obs, 0)              # your hand
obs_utils.get_prize_cards(obs, 0)       # your prize cards
obs_utils.get_deck_count(obs, 0)        # remaining deck size
obs_utils.get_status_conditions(obs, 0) # {"poisoned": bool, ...}
```

---

## Agents

### `RandomAgent` — baseline

**File:** `src/ptcg/agents/random_agent.py`

Every turn, picks `maxCount` actions uniformly at random from the available
options. No game knowledge is used. Useful as a baseline to measure how much
better a smarter agent performs.

---

### `RuleBasedAgent` — priority rule list

**File:** `src/ptcg/agents/rule_based_agent.py`

Evaluates a fixed list of rules in priority order every turn. The first rule
whose `matches()` condition is satisfied fires and its `select()` result is
returned. `RandomFallback` is always last, so the agent never fails to act.

Rules require the card and attack database (`card_db`) to perform card-aware
decisions. The database is loaded from the C library on `on_game_start()`.
On macOS (where the library is unavailable), rules that depend on it silently
skip and fall through to `RandomFallback`.

#### Rule priority order

| Priority | Rule | Fires when | Selects |
|---|---|---|---|
| 1 | `SelectBestAttack` | Attack options are available and card DB is loaded | Best attack by effective damage — see ranking below |
| 2 | `EvolveIfBeneficial` | An evolution raises HP or cures a status, and its best attack is not weaker | The evolution with the highest HP |
| 3 | `SearchForEnergy` | Active has no energy attached and an energy card is playable from hand | The energy card |
| 4 | `AttachEnergyToActive` | Attach option exists, energy not yet attached this turn, active not almost-dead without a KO opportunity (unless Stage 2) | The first attach option |
| 5 | `PlayPokemonToBench` | Bench has space and a basic Pokémon is in hand | The basic Pokémon with the highest HP |
| 6 | `RetreatIfLowHP` | Active HP ≤ 30 and retreat option exists | The first retreat option |
| 7 | `RandomFallback` | Always — catches anything above misses | A random valid action |

#### Attack ranking inside `SelectBestAttack`

Every legal attack is scored on a six-element tuple; higher tuple = better choice.

| Rank | Criterion | How |
|---|---|---|
| 1 | **Wins the game** | KO + exactly 1 prize card remaining |
| 2 | **Knocks Out** | Effective damage ≥ opponent remaining HP |
| 3 | **Hits weakness, in range next turn** | Hits weakness AND remaining HP after hit ≤ best effective damage we can deal |
| 4 | **Highest effective damage** | `effective = base × 2` if weakness, `effective − 30` if resistance |
| 5 | **Prefer non-resisted** | Tiebreaker when effective damage is equal |
| 6 | **Lower energy cost** | Fewest energies in the attack's cost list |

Weakness and resistance are read from `all_card_data()` card records for the specific attacker and defender. No hard-coded type chart is used.

#### Energy attachment guard (`AttachEnergyToActive`)

Blocked when all three conditions hold:
- Active HP ≤ 30
- No attack KOs the opponent this turn
- Active is not a Stage 2 Pokémon

#### Evolution guard (`EvolveIfBeneficial`)

Blocked if the evolution's best attack has lower damage or higher energy cost than the current form's best attack.

---

### `InspectorAgent` — development tool

**File:** `src/ptcg/agents/inspector_agent.py`

Plays randomly while recording the raw observation at every turn. Use it to
discover the actual structure of `obs["select"]["option"]` on Kaggle before
implementing or tuning rules.

After a battle, call `inspector.print_options(max_turns=5)` to print the
options seen in the first N turns, including the chosen indices and the full
option dict for each available action.

---

## Adding a New Agent

1. Create `src/ptcg/agents/my_agent.py`.
2. Subclass `BaseAgent` and implement all four methods.
3. Add `"MyAgent"` to `AGENTS` in the notebook to test it.

```python
from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils

_DECK: list[int] = [...]  # 60 card IDs

class MyAgent(BaseAgent):

    def get_deck(self) -> list[int]:
        return _DECK

    def on_game_start(self) -> None:
        pass

    def on_game_end(self, result: dict) -> None:
        pass

    def select_action(self, obs: dict) -> list[int]:
        options   = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        return ...  # your strategy here
```

The file name must be the snake_case of the class name:
`MyAgent` → `my_agent.py`, `RandomAgent` → `random_agent.py`.

---

## Building a Deck

A deck is a list of exactly **60 integers** (card IDs). The default deck is
already set in `_DECK` inside each agent file using the engine's bundled
example. To build your own, check the card IDs printed in the notebook's
"Available deck" cell and the competition's starter notebooks on Kaggle.

Once you have your 60 IDs, update `_DECK` in your agent file.

---

## Testing

All testing must be done inside a Kaggle notebook — cabt is pre-installed there.

Open `notebooks/test_agents.ipynb`, set your GitHub URL, edit `AGENTS`, and run all cells.
The notebook will:
- Clone this repo and install the package
- Print the available card IDs from the default deck
- Run every agent in `AGENTS` against every other agent
- Print a results summary

---

## Submitting to Kaggle

### 1. Install the Kaggle CLI

```bash
pip install kaggle
```

### 2. Set up credentials

Go to https://www.kaggle.com/settings → **API** → **Create New Token**, then:

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

### 3. Accept competition rules

Visit the competition page and click **Join Competition**.

### 4. Choose your agent

Open `scripts/build_submission.py` and set `AGENT_CLASS` and `AGENT_MODULE`
to the agent you want to submit:

```python
AGENT_CLASS = "RandomAgent"
AGENT_MODULE = "ptcg.agents.random_agent"
```

### 5. Generate submission.py

```bash
python scripts/build_submission.py
```

This reads your agent class and generates a self-contained `submission.py`
with no local imports — exactly what the competition arena expects.

### 6. Submit

```bash
kaggle competitions submit pokemon-tcg-ai-battle \
  -f submission.py \
  -m "your description"
```

### 7. Check results

```bash
kaggle competitions submissions pokemon-tcg-ai-battle
kaggle competitions leaderboard pokemon-tcg-ai-battle
```

---

## Resources

- Competition: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/overview
- cabt engine API: https://matsuoinstitute.github.io/cabt/
- Kaggle CLI docs: https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md
