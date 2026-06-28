# Pokemon TCG AI Battle

A modular Python framework for building AI agents that compete in the
[Kaggle PTCG AI Battle Challenge Simulation](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/overview),
powered by the [cabt engine](https://matsuoinstitute.github.io/cabt/).

> **Platform note:** the cabt engine's native library (`libcg.so`) is Linux-only.
> Games can only run inside a **Kaggle notebook** (or Linux). See [Testing](#testing).

---

## Project Structure

```
PokemonBattle/
├── submission.py                      # Arena entry point (bundled as main.py)
├── CLAUDE.md                          # AI assistant context / dev guidelines
├── notebooks/
│   └── test_agents.ipynb              # Kaggle notebook: run tournaments, replays
├── scripts/
│   └── build_submission.py           # Bundles submission.tar.gz (main.py + cg + ptcg)
├── docs/
│   ├── cabt_api_reference.md          # Engine API: observation, data classes, enums
│   └── ptcg_ruleset.md               # TCG rules + simulator deviations
├── setup.py
├── requirements.txt
└── src/
    ├── cg/                            # Official engine helper package (Linux-only libcg.so)
    │   ├── api.py                     # Typed dataclasses + enums + all_card_data/all_attack
    │   ├── game.py  sim.py  utils.py  # Low-level battle control / ctypes bindings
    │   └── libcg.so                   # Native engine library
    └── ptcg/                          # Our framework
        ├── agent_base.py             # Abstract base class all agents inherit from
        ├── observation.py            # Read the observation dict (incl. perspective helpers)
        ├── card_db.py                # Typed card/attack lookup via cg.api
        ├── decks.py                  # Named 60-card decks
        ├── log_formatter.py          # Human-readable game replay
        ├── game.py                   # kaggle_environments / cabt wrappers
        ├── agents/
        │   ├── random_agent.py       # Baseline: uniform random
        │   ├── rule_based_agent.py   # Priority rule-list agent
        │   ├── planner_agent.py      # Turn-level AttackPlan agent
        │   └── inspector_agent.py    # Dev tool: records raw options
        ├── rules/
        │   ├── rule.py               # Abstract Rule base class
        │   ├── schema.py             # Re-exports cg.api enums + option helpers
        │   ├── damage.py             # Effective damage (weakness ×2, resistance −30)
        │   ├── basic_rules.py        # Six rule implementations
        │   └── fallback.py           # RandomFallback — always matches
        └── planning/
            ├── pokemon_score.py      # Target valuation (prize count first)
            └── attack_plan.py        # Turn-level AttackPlan + builder
```

---

## Reference Docs

| Doc | Purpose |
|---|---|
| [`docs/cabt_api_reference.md`](docs/cabt_api_reference.md) | Engine API: observation dict shape, all data classes/enums, game/api/sim functions, deck & submission formats. |
| [`docs/ptcg_ruleset.md`](docs/ptcg_ruleset.md) | TCG rules (turns, combat, status, win conditions) + a **Simulator Differences** section. |

---

## Setup

```bash
pip install -r requirements.txt
pip install -e .
```

The `cg` package (with `libcg.so`) ships in `src/cg/`. It only loads on
**Linux**; on macOS/Windows any code path that touches the engine raises a
`dlopen` error and `card_db.load()` returns `False`. Develop locally, run on
Kaggle.

---

## How the Game Works

The cabt engine calls your agent in two phases each game:

1. **Deck selection** (`obs["select"]` is `None`) — return your 60-card deck as
   `list[int]`. `BaseAgent.__call__` handles this automatically via `get_deck()`.
2. **Every turn** (`obs["select"]` is set) — return action indices from
   `obs["select"]["option"]`.

```
observation dict
├── "logs"     — events since the last selection
├── "current"  — board state (None during deck selection)
│   ├── "yourIndex" — which player you are (0 or 1)
│   └── "players"   — ABSOLUTE list [player0, player1]
│       ├── active, bench, hand, handCount, prize, deckCount, discard, benchMax
│       └── poisoned / burned / asleep / paralyzed / confused
└── "select"   — available choices (None during deck selection)
    ├── "option"   — list of option dicts (type = OptionType int, + fields)
    ├── "minCount" / "maxCount" — how many indices to return
    └── "context"  — SelectContext (what is being chosen)
```

> **Perspective matters.** `players` is absolute; `yourIndex` says which one you
> are. "Your" active is `players[yourIndex]`, *not* `players[0]`. Always go
> through the perspective helpers in `observation.py` (`my_active`,
> `opponent_active`, …) — never hard-code index 0 as "me".

---

## Module Reference

### `agent_base.py` — `BaseAgent`

| Method | When called | Must return |
|---|---|---|
| `get_deck()` | Deck-selection phase | `list[int]` — 60 card IDs |
| `select_action(obs)` | Every turn | `list[int]` — action indices |
| `on_game_start()` | Before first turn | Nothing |
| `on_game_end(result)` | After last turn | Nothing |

All agents accept an optional `deck=` argument so a deck can be chosen at runtime
(`RandomAgent(deck=DECKS["mega_lucario_ex"])`).

### `observation.py` — board state helpers

```python
from ptcg import observation as obs_utils

obs_utils.get_options(obs)            # available option dicts
obs_utils.get_max_count(obs)          # how many to pick
# Perspective-aware (preferred):
obs_utils.my_active(obs)              # your active Pokémon
obs_utils.opponent_active(obs)        # opponent's active
obs_utils.my_bench(obs)               # your bench
obs_utils.my_prize_cards(obs)         # your prize cards
obs_utils.opponent_prize_cards(obs)   # opponent's prize cards
obs_utils.my_status_conditions(obs)   # {"poisoned": bool, ...}
```

### `card_db.py` — typed card/attack lookup

Loads `CardData` / `Attack` dataclasses from `cg.api.all_card_data()` /
`all_attack()`. Call `card_db.load()` once (agents do this in `on_game_start`),
then `card_db.get_card(id)` / `card_db.get_attack(id)` (return `None` if unknown
or the engine isn't loaded).

### `decks.py` — named decks

`DECKS` maps a name to a 60-card `list[int]`. Currently `"default"` (engine
sample) and `"mega_lucario_ex"` (from the official sample notebook).

### `log_formatter.py` — replay

`format_history(history, agent_names=[...])` turns a game's `visualize` data into
readable commentary (card names, KOs, status, winner), suppressing noise.

### `rules/` — reusable decision rules

`Rule` (abstract `matches`/`select`), `schema` (re-exports the `cg.api` enums +
option-type helpers), `damage` (effective-damage formula), `basic_rules` (the
six rules), `fallback` (`RandomFallback`).

### `planning/` — turn-level planning

`pokemon_score(pokemon)` values a target (prize count → energy → tools → stage →
damage taken → threat). `build_attack_plan(...)` returns an `AttackPlan`
(`best_attacker`, `best_target`, `attack_id`, `should_switch_or_use_boss`,
`expected_effective_damage`, `expected_prizes`, `required_energy`, `can_take_ko`).

---

## Agents

### `RandomAgent` — baseline
Picks `maxCount` actions uniformly at random. No game knowledge; the yardstick
for measuring smarter agents.

### `RuleBasedAgent` — priority rule list
Evaluates rules in priority order; the first whose `matches()` is true fires.
`RandomFallback` is always last so the agent never fails to act. Records the rule
that fired each turn in `rule_log`.

| Priority | Rule | Fires when | Selects |
|---|---|---|---|
| 1 | `SelectBestAttack` | Attacks available, card DB loaded | Best attack by effective damage (ranking below) |
| 2 | `EvolveIfBeneficial` | Evolution raises HP or cures a status, best attack not weaker | Highest-HP evolution |
| 3 | `SearchForEnergy` | Active has no energy and an energy card is playable | The energy card |
| 4 | `AttachEnergyToActive` | Attach available, energy not yet attached, active not almost-dead w/o a KO (unless Stage 2) | First attach |
| 5 | `PlayPokemonToBench` | Bench space + a basic Pokémon in hand | Highest-HP basic |
| 6 | `RetreatIfLowHP` | Active HP ≤ 30 and retreat available | First retreat |
| 7 | `RandomFallback` | Always | A random valid action |

**`SelectBestAttack` ranking** (six-element tuple, higher wins): wins the game
(KO while opponent ≤ 1 prize) → KO → hits weakness & leaves target in KO range
next turn → highest effective damage → prefer non-resisted → lower energy cost.
Weakness/resistance come from card data (`weakness ×2`, `resistance −30`), never
a hard-coded type chart.

### `PlannerAgent` — turn-level AttackPlan
**File:** `src/ptcg/agents/planner_agent.py`

Instead of deciding each action independently, it builds one `AttackPlan` at the
start of every turn and judges every action by how well it serves the plan:

1. attach energy to the **planned attacker** until it can attack,
2. switch / retreat to bring the planned attacker active,
3. play **Boss Orders** only when it enables the planned KO / threat removal,
4. execute the planned attack,
5. choose searched cards (`TO_HAND`) that fill gaps in the plan.

Targets are valued by `pokemon_score` (prize count first), and game-winning KOs
dominate. Decision labels are recorded in `rule_log` for the notebook breakdown.
`GUST_CARD_IDS` / `SWITCH_CARD_IDS` list the Boss-Orders / Switch card IDs and
are easy to extend for other decks.

### `InspectorAgent` — dev tool
Plays randomly while recording every observation. After a battle,
`inspector.print_options(max_turns=5)` prints the raw option dicts so you can
inspect the engine's actual data on Kaggle.

---

## Adding a New Agent

1. Create `src/ptcg/agents/my_agent.py`.
2. Subclass `BaseAgent`, implement the four methods, accept an optional `deck=`.
3. Add `"MyAgent"` to `AGENTS` in the notebook to test it.

```python
from ptcg.agent_base import BaseAgent
from ptcg import observation as obs_utils
from ptcg.decks import DECKS

class MyAgent(BaseAgent):
    def __init__(self, deck=None):
        self._deck = deck if deck is not None else DECKS["default"]

    def get_deck(self):       return self._deck
    def on_game_start(self):  pass
    def on_game_end(self, r): pass

    def select_action(self, obs):
        options   = obs_utils.get_options(obs)
        max_count = obs_utils.get_max_count(obs)
        return ...  # your strategy
```

The file name must be the snake_case of the class name:
`MyAgent` → `my_agent.py` (the notebook resolves agents this way).

---

## Decks

Decks live in `src/ptcg/decks.py` as named entries in `DECKS`. To add one, append
a `name: list[int]` (exactly 60 card IDs). Card IDs and names can be browsed in
the notebook's **Available decks** section (uses `card_db`). Pick which deck each
agent uses at runtime via `DECK_CHOICE` in the notebook, or pass `deck=` directly.

---

## Testing

cabt is Linux-only, so testing happens **inside a Kaggle notebook**. Open
`notebooks/test_agents.ipynb`, set `GITHUB_URL` (and optionally `BRANCH` to clone
a single branch), then run all cells. Sections:

1. **Clone repo** — optional single-branch clone.
2. **Card database** — loads `card_db`; warns if it failed (then `PlannerAgent`/
   `RuleBasedAgent` behave like `RandomAgent`).
3. **Available decks** — every deck in `DECKS` with Pokémon and counts.
4. **Configure tournament** — `AGENTS`, `NICKNAMES`, `DECK_CHOICE`, `N_GAMES`.
   Same-class matchups are auto-labeled `(P0)` / `(P1)` so you can tell sides apart.
5. **Run tournament** — every agent vs every agent, `N_GAMES` each.
6. **Results summary** — win/draw/loss table.
7. **Rule firing breakdown** — which rule/decision fired (per agent). If
   `RandomFallback` is ~100%, `card_db` didn't load.
8. **Replay a tournament game** — readable replay of any matchup's last game.
9. **Custom game** — one-off match with nicknames and decks set at runtime.

---

## Submitting to Kaggle

The submission is a **tar.gz** bundling the entry point with the `cg` and `ptcg`
packages (the format the official sample uses).

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
Edit the import in `submission.py` to the agent you want to compete:
```python
from ptcg.agents.planner_agent import PlannerAgent
_agent = PlannerAgent()
```

### 5. Build the archive
```bash
python scripts/build_submission.py
```
Produces `submission.tar.gz` containing:
```
main.py   (= submission.py)
cg/       (engine helpers + libcg.so)
ptcg/     (our framework)
```

### 6. Submit
```bash
kaggle competitions submit pokemon-tcg-ai-battle -f submission.tar.gz -m "your description"
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
