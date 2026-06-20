# cabt Engine API Reference

Source: https://matsuoinstitute.github.io/cabt/

---

## Overview

The cabt engine is a Pokemon TCG battle simulator exposed through `kaggle_environments`.
Your agent is called as a plain function every step with an observation dict and must return
a list of integer indices.

> **Simulator is authoritative.** The simulator deviates from official TCG rules in a few
> known ways. The most agent-relevant difference: **some attacks are withheld from
> `select["option"]` even when energy requirements are met** (e.g. when the Bench is full
> or the deck is empty). Never assume an attack is available — always select only from what
> the engine offers. Full details in `docs/ptcg_ruleset.md` → *Simulator Differences*.

**Engine availability:** Linux only (pre-installed in Kaggle competition notebooks).
`pip install cabt` will fail — the package is not on PyPI.

---

## Quick Start

```python
from kaggle_environments import make

env = make("cabt", configuration={"decks": [deck0, deck1]})
env.run([agent0, agent1])
rewards = [step["reward"] for step in env.steps[-1]]
```

Agent signature expected by `env.run`:

```python
def agent(obs: dict, *args) -> list[int]:
    if obs.get("select") is None:
        return DECK           # deck-selection phase: return 60 card IDs
    options   = obs["select"]["option"]
    max_count = obs["select"]["maxCount"]
    return random.sample(range(len(options)), max_count)
```

---

## Observation Dict

Every call to the agent receives an `obs` dict with three top-level keys.

```
obs
├── "logs"     list[Log]         — recent game events (see LogType)
├── "current"  State | None      — full board state; None at deck-selection phase
└── "select"   SelectData | None — choices to make; None at deck-selection phase
```

### Two-Phase Protocol

| Phase | `obs["select"]` | `obs["current"]` | Agent must return |
|---|---|---|---|
| Deck selection (first call) | `None` | `None` | `list[int]` — exactly 60 card IDs |
| Every game turn | set | set | `list[int]` — indices into `select["option"]` |

---

## Data Structures

### State

Top-level board state, found at `obs["current"]`.

| Field | Type | Description |
|---|---|---|
| `turn` | `int` | Round number (0 before first turn) |
| `turnActionCount` | `int` | Actions taken this turn |
| `yourIndex` | `int` | Active player index (0 or 1) |
| `firstPlayer` | `int` | Who goes first (-1 if undetermined) |
| `supporterPlayed` | `bool` | Supporter card played this turn |
| `stadiumPlayed` | `bool` | Stadium card played this turn |
| `energyAttached` | `bool` | Energy attached this turn |
| `retreated` | `bool` | Active Pokémon retreated this turn |
| `result` | `int` | Winner index; -1 if game ongoing |
| `stadium` | `list[Card]` | Active stadium (0 or 1 elements) |
| `looking` | `list[Card \| None] \| None` | Cards currently being examined |
| `players` | `list[PlayerState]` | Two-element array, index matches `yourIndex` |

### PlayerState

Found at `obs["current"]["players"][i]`.

| Field | Type | Description |
|---|---|---|
| `active` | `list[Pokemon \| None]` | Active Pokémon (0–1 elements; `None` = face-down) |
| `bench` | `list[Pokemon]` | Benched Pokémon (up to `benchMax`) |
| `benchMax` | `int` | Maximum bench capacity (usually 5) |
| `hand` | `list[Card] \| None` | Cards in hand — `None` for the opponent |
| `handCount` | `int` | Number of cards in hand (always visible) |
| `deckCount` | `int` | Remaining cards in deck |
| `discard` | `list[Card]` | Discard pile |
| `prize` | `list[Card \| None]` | Prize cards; face-down cards are `None` |
| `poisoned` | `bool` | |
| `burned` | `bool` | |
| `asleep` | `bool` | |
| `paralyzed` | `bool` | |
| `confused` | `bool` | |

### Pokemon

Extends `Card` with in-play state.

| Field | Type | Description |
|---|---|---|
| `id` | `int` | CardData identifier |
| `serial` | `int` | Unique per-match serial number |
| `hp` | `int` | Current HP |
| `maxHp` | `int` | Maximum HP |
| `appearThisTurn` | `bool` | Was played or moved to active this turn |
| `energies` | `list[EnergyType]` | Attached energy types |
| `energyCards` | `list[Card]` | The actual energy card objects |
| `tools` | `list[Card]` | Attached tool cards |
| `preEvolution` | `list[Card]` | Previous evolution cards underneath |

### Card

Basic card identity.

| Field | Type | Description |
|---|---|---|
| `id` | `int` | CardData identifier |
| `serial` | `int` | Unique per-match serial number |
| `playerIndex` | `int` | Owner (0 or 1) |

### SelectData

Found at `obs["select"]`.

| Field | Type | Description |
|---|---|---|
| `type` | `SelectType` | Category of selection |
| `context` | `SelectContext` | Specific scenario (49 values) |
| `minCount` | `int` | Minimum indices to return |
| `maxCount` | `int` | Maximum indices to return |
| `option` | `list[Option]` | Available choices — index into this list |
| `deck` | `list[Card] \| None` | Cards if selecting from deck |
| `contextCard` | `Card \| None` | Card that triggered this selection |
| `effect` | `Card \| None` | Card producing the current effect |
| `remainDamageCounter` | `int` | Damage counters still to place |
| `remainEnergyCost` | `int` | Energy still needed to pay |

### Option

A single selectable choice inside `select["option"]`. Return its index to choose it.

| Field | Type | Description |
|---|---|---|
| `type` | `OptionType` | What kind of action this is |
| `number` | `int \| None` | Numeric value for COUNT selections |
| `area` | `AreaType \| None` | Zone the card is in |
| `index` | `int \| None` | Position within that zone |
| `playerIndex` | `int \| None` | Card owner |
| `toolIndex` | `int \| None` | Tool attachment slot |
| `energyIndex` | `int \| None` | Energy attachment slot |
| `count` | `int \| None` | Energy unit quantity |
| `inPlayArea` | `AreaType \| None` | In-play zone |
| `inPlayIndex` | `int \| None` | In-play position |
| `attackId` | `int \| None` | Attack identifier |
| `cardId` | `int \| None` | CardData ID |
| `serial` | `int \| None` | Card serial |
| `specialConditionType` | `SpecialConditionType \| None` | Status condition |

### CardData

Static card metadata, returned by `all_card_data()`.

| Field | Type | Description |
|---|---|---|
| `cardId` | `int` | Unique identifier |
| `name` | `str` | Card name |
| `cardType` | `CardType` | Classification |
| `hp` | `int` | Max HP (0 for non-Pokémon) |
| `retreatCost` | `int` | Energy needed to retreat |
| `weakness` | `EnergyType \| None` | Weakness type |
| `resistance` | `EnergyType \| None` | Resistance type |
| `energyType` | `EnergyType` | Pokémon or basic energy type |
| `basic` | `bool` | Is Basic Pokémon |
| `stage1` | `bool` | Is Stage 1 |
| `stage2` | `bool` | Is Stage 2 |
| `ex` | `bool` | Is Pokémon-EX |
| `megaEx` | `bool` | Is Mega-EX |
| `tera` | `bool` | Is Tera Pokémon |
| `aceSpec` | `bool` | Is ACE SPEC card |
| `evolvesFrom` | `str \| None` | Name of the pre-evolution |
| `skills` | `list[Skill]` | Abilities / Poké-Powers |
| `attacks` | `list[int]` | Attack IDs (look up via `all_attack()`) |

### Attack

| Field | Type | Description |
|---|---|---|
| `attackId` | `int` | Unique identifier |
| `name` | `str` | Attack name |
| `text` | `str` | Effect description |
| `damage` | `int` | Base damage value |
| `energies` | `list[EnergyType]` | Required energy types |

### Log

A single game event entry in `obs["logs"]`.

| Field | Type | Notes |
|---|---|---|
| `type` | `LogType` | Event type |
| `playerIndex` | `int \| None` | Acting player |
| `cardId` | `int \| None` | Card involved |
| `serial` | `int \| None` | Card serial |
| `fromArea` | `AreaType \| None` | Source zone |
| `toArea` | `AreaType \| None` | Destination zone |
| `attackId` | `int \| None` | Attack used |
| `value` | `int \| None` | Numeric payload (e.g. damage) |
| `head` | `bool \| None` | Coin flip result |
| `result` | `int \| None` | Game result |
| `reason` | `... \| None` | Reason for event |

---

## Enumerations

### AreaType — card zones

| Name | Value |
|---|---|
| DECK | 1 |
| HAND | 2 |
| DISCARD | 3 |
| ACTIVE | 4 |
| BENCH | 5 |
| PRIZE | 6 |
| STADIUM | 7 |
| ENERGY | 8 |
| TOOL | 9 |
| PRE_EVOLUTION | 10 |
| PLAYER | 11 |
| LOOKING | 12 |

### EnergyType

| Name | Value |
|---|---|
| COLORLESS | 0 |
| GRASS | 1 |
| FIRE | 2 |
| WATER | 3 |
| LIGHTNING | 4 |
| PSYCHIC | 5 |
| FIGHTING | 6 |
| DARKNESS | 7 |
| METAL | 8 |
| DRAGON | 9 |
| RAINBOW | 10 |
| TEAM_ROCKET | 11 |

### CardType

| Name | Value |
|---|---|
| POKEMON | 0 |
| ITEM | 1 |
| TOOL | 2 |
| SUPPORTER | 3 |
| STADIUM | 4 |
| BASIC_ENERGY | 5 |
| SPECIAL_ENERGY | 6 |

### OptionType — action kinds

| Name | Description |
|---|---|
| NUMBER | Numeric count selection |
| YES | Confirm |
| NO | Decline |
| CARD | Select a card |
| TOOL_CARD | Select a tool card |
| ENERGY_CARD | Select an energy card |
| ENERGY | Select an energy unit |
| PLAY | Play a card |
| ATTACH | Attach a card |
| EVOLVE | Evolve a Pokémon |
| ABILITY | Use an ability |
| DISCARD | Discard a card |
| RETREAT | Retreat active Pokémon |
| ATTACK | Use an attack |
| END | End the turn |
| SKILL | Use a Pokémon skill |
| SPECIAL_CONDITION | Apply a status condition |

### SelectType — selection categories

`MAIN, CARD, ATTACHED_CARD, CARD_OR_ATTACHED_CARD, ENERGY, SKILL, ATTACK, EVOLVE, COUNT, YES_NO, SPECIAL_CONDITION`

### SpecialConditionType

| Name | Value |
|---|---|
| POISON | 0 |
| BURN | 1 |
| SLEEP | 2 |
| PARALYZE | 3 |
| CONFUSE | 4 |

### LogType — event types

**Game phases:** `SHUFFLE, HAS_BASIC_POKEMON, TURN_START, TURN_END`

**Card actions:** `DRAW, MOVE_CARD, SWITCH, PLAY, ATTACH, EVOLVE, DEVOLVE, MOVE_ATTACHED, ATTACK`

**Status / damage:** `POISONED, BURNED, ASLEEP, PARALYZED, CONFUSED, HP_CHANGE, COIN, RESULT`

---

## Functions

### game module

#### `battle_start(deck0, deck1) -> tuple[dict | None, StartData]`

Starts a new battle.

- `deck0`, `deck1`: `list[int]` — exactly 60 card IDs each.
- Returns `(initial_observation, start_data)`. Observation is `None` if init fails.
- Raises `ValueError` if either deck is not exactly 60 cards.

#### `battle_select(select_list) -> dict`

Submits the agent's choice and advances the game.

- `select_list`: `list[int]` — indices into `obs["select"]["option"]`.
- Returns the next observation dict.
- Raises `ValueError` for non-integer list or corrupted state; `IndexError` for out-of-bounds.

#### `battle_finish() -> None`

Terminates the current battle and frees native resources. Always call after a game ends.

#### `visualize_data() -> str`

Returns a human-readable string of the current board state. Useful for debugging.

---

### api module

#### `all_card_data() -> list[CardData]`

Returns metadata for every card in the game pool (name, HP, types, attacks, evolution chain).
Call once and cache — the card pool does not change during a match.

#### `all_attack() -> list[Attack]`

Returns all attack definitions. Cross-reference with `CardData.attacks` (list of `attackId`).

#### `to_observation_class(obs: dict) -> Observation`

Converts a raw observation dict into typed dataclass instances.

---

### sim module — tree search / MCTS support

These functions support building a lookahead search over game states.

#### `search_begin(agent_observation, your_deck, your_prize, opponent_deck, opponent_hand, opponent_active, manual_coin=False) -> SearchState`

Initialises a search from the current observation. The opponent's hidden information (deck,
prize cards, hand) must be estimated — counts must match reality or the engine will reject them.

- `agent_observation`: `Observation` — current observation (as dataclass).
- `your_deck`: `list[int]` — your remaining deck card IDs.
- `your_prize`: `list[int]` — your prize card IDs (face-up ones known).
- `opponent_deck`: `list[int]` — estimated opponent deck.
- `opponent_hand`: `list[int]` — estimated opponent hand.
- `opponent_active`: `list[int]` — opponent's active Pokémon card IDs.
- `manual_coin`: `bool` — if `True`, coin flips must be supplied manually.
- Returns a `SearchState` with `.searchId` and `.observation`.

#### `search_step(search_id: int, select: list[int]) -> SearchState`

Advances the search tree by one action. Equivalent to `battle_select` but within the search.

#### `search_end() -> None`

Terminates all searches and frees memory.

#### `search_release(search_id: int) -> None`

Frees a single search state by ID without affecting others.

---

## Deck Format

- Exactly **60 card IDs** (integers), duplicates allowed.
- Maximum **4 copies** of any single card (Basic Energy is exempt).
- Must contain at least one Basic Pokémon or the game will not start.
- Card IDs are obtained from `all_card_data()` or from the engine's bundled default deck.

```python
DECK: list[int] = [
    721, 721,           # 2x some Basic Pokémon
    722, 722, 722, 722, # 4x Stage 1
    # ... 54 more IDs totalling 60
]
```

---

## Submission Format

The competition expects a single flat `submission.py` with no local imports:

```python
DECK: list[int] = [...]  # 60 card IDs

def agent(obs: dict, *args) -> list[int]:
    if obs.get("select") is None:
        return DECK
    # your strategy
    options   = obs["select"]["option"]
    max_count = obs["select"]["maxCount"]
    return [...]  # indices into options
```

Use `scripts/build_submission.py` to generate this file automatically from any `BaseAgent` subclass.